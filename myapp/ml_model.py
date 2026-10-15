
import os
import joblib
import numpy as np

from pathlib import Path
from django.conf import settings
from django.db.models import Avg

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .models import GrantProposal, Evaluation, ProposalAnalysis


MODEL_DIR = Path(settings.BASE_DIR) / "ml_models"
MODEL_PATH = MODEL_DIR / "grant_score_model.joblib"

FEATURE_NAMES = [
    "requested_budget",
    "abstract_length",
    "objectives_length",
    "methodology_length",
    "expected_impact_length",
    "budget_justification_length",
    "nlp_similarity",
]


def get_proposal_features(proposal):
    """Create consistent numeric features for training and prediction."""

    latest_analysis = (
        ProposalAnalysis.objects
        .filter(proposal=proposal)
        .order_by("-analyzed_at")
        .first()
    )

    # The current NLP analysis stores similarity_score on a 0–100 scale.
    nlp_similarity = (
        latest_analysis.similarity_score
        if latest_analysis and latest_analysis.similarity_score is not None
        else 0.0
    )

    return {
        "requested_budget": float(proposal.requested_budget or 0),
        "abstract_length": len(proposal.abstract or ""),
        "objectives_length": len(proposal.objectives or ""),
        "methodology_length": len(proposal.methodology or ""),
        "expected_impact_length": len(proposal.expected_impact or ""),
        "budget_justification_length": len(
            proposal.budget_justification or ""
        ),
        "nlp_similarity": float(nlp_similarity),
    }


def build_training_dataset():
    """
    Create one training row per proposal.

    Target = mean total_score from that proposal's completed
    reviewer evaluations. Pending evaluations are excluded.
    """

    X = []
    y = []
    proposal_ids = []

    proposals = GrantProposal.objects.all().select_related("category")

    for proposal in proposals:
        completed_evaluations = Evaluation.objects.filter(
            proposal=proposal,
            decision__in=["Recommend", "Not Recommend", "Revision Required"],
        )

        target = completed_evaluations.aggregate(
            average_score=Avg("total_score")
        )["average_score"]

        if target is None:
            continue

        X.append(get_proposal_features(proposal))
        y.append(float(target))
        proposal_ids.append(proposal.id)

    return X, y, proposal_ids


def train_grant_score_model():
    """Train, evaluate, and save a Random Forest regression model."""

    feature_rows, targets, proposal_ids = build_training_dataset()

    if len(feature_rows) < 20:
        raise ValueError(
            f"Only {len(feature_rows)} proposals have completed evaluations. "
            "Collect at least 20 for an initial experiment; 50 or more "
            "diverse, reviewed proposals are preferable for a more "
            "meaningful evaluation."
        )

    X = np.array([
        [row[name] for name in FEATURE_NAMES]
        for row in feature_rows
    ], dtype=float)

    y = np.array(targets, dtype=float)

    if len(set(y.tolist())) < 2:
        raise ValueError(
            "All training targets are identical. More varied reviewer "
            "evaluations are needed to train a useful regression model."
        )

    # Hold out data that the model does not see during training.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        min_samples_leaf=2,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

    # R² can be undefined or misleading with a very small test set.
    r2 = (
        float(r2_score(y_test, predictions))
        if len(y_test) >= 2
        else None
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "feature_names": FEATURE_NAMES,
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "training_rows": len(X_train),
            "test_rows": len(X_test),
            "proposal_ids": proposal_ids,
        },
        MODEL_PATH,
    )

    return {
        "training_rows": len(X_train),
        "test_rows": len(X_test),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "model_path": str(MODEL_PATH),
    }


def predict_proposal_score(proposal):
    """Load the saved model and predict a proposal's estimated score."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "The ML model has not been trained yet. "
            "Train it after collecting completed evaluations."
        )

    saved = joblib.load(MODEL_PATH)
    model = saved["model"]

    features = get_proposal_features(proposal)
    X = np.array(
        [[features[name] for name in saved["feature_names"]]],
        dtype=float,
    )

    predicted_score = float(model.predict(X)[0])

    # Reviewer scores use a 0–10 scale in the current views.
    predicted_score = max(0.0, min(10.0, predicted_score))

    return {
        "predicted_score": round(predicted_score, 2),
        "features": features,
        "mae": saved["mae"],
        "rmse": saved["rmse"],
        "r2": saved["r2"],
        "training_rows": saved["training_rows"],
        "test_rows": saved["test_rows"],
    }
