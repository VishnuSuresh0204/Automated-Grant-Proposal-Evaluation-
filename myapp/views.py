
import os
from functools import lru_cache
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer, util

from .models import *




# ==========================================================
# COMMON HELPERS
# ==========================================================

def is_admin(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.user_type.strip().lower() == "admin"
        )
    )


def has_role(user, role):
    return (
        user.is_authenticated
        and user.user_type.strip().lower() == role.lower()
    )


def get_entity_template(user, template_name):
    """Return the entity-specific template path based on the user's role."""
    if is_admin(user):
        return f"admin/{template_name}"
    elif has_role(user, "reviewer"):
        return f"reviewer/{template_name}"
    else:
        return f"applicant/{template_name}"


def role_required(role):
    """Protect a view based on the logged-in user's role."""

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in first.")
                return redirect("login")

            allowed = is_admin(request.user) if role.lower() == "admin" \
                else has_role(request.user, role)

            if not allowed:
                return HttpResponseForbidden(
                    "You do not have permission to access this page."
                )

            return view_func(request, *args, **kwargs)

        wrapper.__name__ = view_func.__name__
        wrapper.__doc__ = view_func.__doc__
        return wrapper

    return decorator


def get_dashboard_url(user):
    if is_admin(user):
        return "admin_home"

    role = user.user_type.strip().lower()

    if role == "applicant":
        return "applicant_home"

    if role == "reviewer":
        return "reviewer_home"

    return "home"


def valid_uploaded_document(uploaded_file):
    """Allow common document types for proposal uploads."""

    if not uploaded_file:
        return True

    allowed_extensions = {".pdf", ".docx", ".txt"}
    extension = os.path.splitext(uploaded_file.name)[1].lower()

    if extension not in allowed_extensions:
        raise ValidationError(
            "Upload a PDF, DOCX, or TXT file."
        )

    # Basic upload-size limit: 10 MB.
    if uploaded_file.size > 10 * 1024 * 1024:
        raise ValidationError("The file must be smaller than 10 MB.")

    return True


def extract_proposal_text(uploaded_file):
    """Extract text from a saved PDF, DOCX, or TXT file."""

    if not uploaded_file:
        return ""

    extension = os.path.splitext(uploaded_file.name)[1].lower()

    try:
        uploaded_file.open("rb")

        if extension == ".pdf":
            reader = PdfReader(uploaded_file)
            return "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        if extension == ".docx":
            document = Document(uploaded_file)
            paragraphs = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            return "\n".join(paragraphs)

        if extension == ".txt":
            return uploaded_file.read().decode(
                "utf-8", errors="ignore"
            )

    except Exception:
        return ""

    finally:
        try:
            uploaded_file.close()
        except Exception:
            pass

    return ""


def get_proposal_text(proposal):
    """Combine structured proposal fields and extracted file text."""

    parts = [
        f"Title: {proposal.title}",
        f"Abstract: {proposal.abstract}",
        f"Objectives: {proposal.objectives}",
        f"Methodology: {proposal.methodology}",
        f"Expected Impact: {proposal.expected_impact}",
        f"Budget Justification: {proposal.budget_justification}",
    ]

    if proposal.extracted_text:
        parts.append(proposal.extracted_text)

    return "\n\n".join(parts)


@lru_cache(maxsize=1)
def get_nlp_model():
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )


# ==========================================================
# HOME PAGE
# ==========================================================

def home(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    return render(request, "home.html")


# ==========================================================
# APPLICANT REGISTRATION
# ==========================================================

def applicant_registration(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        organization = request.POST.get("organization", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        profile_image = request.FILES.get("profile_image")

        if not all([
            username, name, email, phone, address, password
        ]):
            messages.error(request, "Please fill in all required fields.")
            return redirect("applicant_registration")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("applicant_registration")

        if Login.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("applicant_registration")

        if ApplicantRegistration.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("applicant_registration")

        try:
            with transaction.atomic():
                user = Login.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    user_type="Applicant",
                )

                ApplicantRegistration.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    organization=organization,
                    profile_image=profile_image,
                )

            messages.success(
                request, "Registration successful. Please log in."
            )
            return redirect("login")

        except (IntegrityError, ValidationError) as error:
            messages.error(request, f"Registration failed: {error}")

    return render(request, "applicant_registration.html")


# ==========================================================
# REVIEWER REGISTRATION
# ==========================================================

def reviewer_registration(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        organization = request.POST.get("organization", "").strip()
        qualification = request.POST.get("qualification", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        experience = request.POST.get("experience_years", "0").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        profile_image = request.FILES.get("profile_image")

        if not all([
            username, name, email, phone, address, password
        ]):
            messages.error(request, "Please fill in all required fields.")
            return redirect("reviewer_registration")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reviewer_registration")

        if Login.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("reviewer_registration")

        if ReviewerRegistration.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("reviewer_registration")

        try:
            experience_years = int(experience)
            if experience_years < 0:
                raise ValueError
        except ValueError:
            messages.error(
                request, "Experience must be a non-negative whole number."
            )
            return redirect("reviewer_registration")

        try:
            with transaction.atomic():
                user = Login.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    user_type="Reviewer",
                )

                ReviewerRegistration.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    organization=organization,
                    qualification=qualification,
                    specialization=specialization,
                    experience_years=experience_years,
                    profile_image=profile_image,
                )

            messages.success(
                request, "Registration successful. Please log in."
            )
            return redirect("/login")

        except (IntegrityError, ValidationError) as error:
            messages.error(request, f"Registration failed: {error}")

    return render(request, "reviewer_registration.html")


# ==========================================================
# LOGIN AND LOGOUT
# ==========================================================

def login(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            auth_login(request, user)
            messages.success(request, "Login successful.")
            return redirect(get_dashboard_url(user))

        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


# ==========================================================
# DASHBOARDS
# ==========================================================

@role_required("applicant")
def applicant_home(request):
    proposals = GrantProposal.objects.filter(
        applicant=request.user
    ).select_related("category").order_by("-submitted_at")

    context = {
        "total_proposals": proposals.count(),
        "pending_proposals": proposals.filter(status="Pending").count(),
        "under_review": proposals.filter(status="Under Review").count(),
        "approved_proposals": proposals.filter(status="Approved").count(),
        "rejected_proposals": proposals.filter(status="Rejected").count(),
        "recent_proposals": proposals[:5],
    }

    return render(request, "applicant/index.html", context)


@role_required("reviewer")
def reviewr_home(request):
    assignments = ReviewerAssignment.objects.filter(
        reviewer=request.user
    ).select_related(
        "proposal", "proposal__category", "proposal__applicant"
    ).order_by("-assigned_at")

    context = {
        "total_assignments": assignments.count(),
        "pending_assignments": assignments.filter(
            is_completed=False
        ).count(),
        "completed_assignments": assignments.filter(
            is_completed=True
        ).count(),
        "recent_assignments": assignments[:5],
    }

    return render(request, "reviewer/index.html", context)


@role_required("admin")
def admin_home(request):
    context = {
        "total_users": Login.objects.count(),
        "total_applicants": Login.objects.filter(
            user_type__iexact="Applicant"
        ).count(),
        "total_reviewers": Login.objects.filter(
            user_type__iexact="Reviewer"
        ).count(),
        "total_categories": GrantCategory.objects.count(),
        "active_categories": GrantCategory.objects.filter(
            is_active=True
        ).count(),
        "total_proposals": GrantProposal.objects.count(),
        "pending_proposals": GrantProposal.objects.filter(
            status="Pending"
        ).count(),
        "under_review_proposals": GrantProposal.objects.filter(
            status="Under Review"
        ).count(),
        "total_evaluations": Evaluation.objects.count(),
        "recent_proposals": GrantProposal.objects.select_related(
            "applicant", "category"
        ).order_by("-submitted_at")[:5],
    }

    return render(request, "admin/admin_home.html", context)


# ==========================================================
# PROFILE
# ==========================================================

@login_required
def user_profile(request):
    user = request.user

    if is_admin(user):
        messages.info(request, "Administrators manage the portal from the Admin Console.")
        return redirect("admin_home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if email:
            user.email = email
            user.save(update_fields=["email"])

        if has_role(user, "applicant"):
            profile = ApplicantRegistration.objects.filter(
                user=user
            ).first()

            if profile:
                profile.name = request.POST.get(
                    "name", profile.name
                ).strip()
                profile.email = email or profile.email
                profile.phone = request.POST.get(
                    "phone", profile.phone
                ).strip()
                profile.address = request.POST.get(
                    "address", profile.address
                ).strip()
                profile.organization = request.POST.get(
                    "organization", profile.organization
                ).strip()

                if request.FILES.get("profile_image"):
                    profile.profile_image = request.FILES["profile_image"]

                profile.save()

        elif has_role(user, "reviewer"):
            profile = ReviewerRegistration.objects.filter(
                user=user
            ).first()

            if profile:
                profile.name = request.POST.get(
                    "name", profile.name
                ).strip()
                profile.email = email or profile.email
                profile.phone = request.POST.get(
                    "phone", profile.phone
                ).strip()
                profile.address = request.POST.get(
                    "address", profile.address
                ).strip()
                profile.organization = request.POST.get(
                    "organization", profile.organization
                ).strip()
                profile.qualification = request.POST.get(
                    "qualification", profile.qualification
                ).strip()
                profile.specialization = request.POST.get(
                    "specialization", profile.specialization
                ).strip()

                if request.FILES.get("profile_image"):
                    profile.profile_image = request.FILES["profile_image"]

                profile.save()

        messages.success(request, "Profile updated.")
        return redirect("user_profile")

    profile = None

    if has_role(user, "applicant"):
        profile = ApplicantRegistration.objects.filter(
            user=user
        ).first()
    elif has_role(user, "reviewer"):
        profile = ReviewerRegistration.objects.filter(
            user=user
        ).first()

    template_name = get_entity_template(user, "profile.html")
    return render(
        request,
        template_name,
        {"profile": profile, "profile_user": user},
    )


@role_required("admin")
def view_users(request):
    users = Login.objects.exclude(
        is_superuser=True
    ).order_by("username")

    return render(request, "admin/view_users.html", {
        "users": users,
    })


# ==========================================================
# GRANT CATEGORY MANAGEMENT
# ==========================================================

@login_required
def grant_categories(request):
    categories = GrantCategory.objects.filter(
        is_active=True
    ).order_by("category_name")

    template_name = get_entity_template(request.user, "categories.html")
    return render(request, template_name, {
        "categories": categories,
    })


@role_required("admin")
def add_grant_category(request):
    if request.method == "POST":
        category_name = request.POST.get(
            "category_name", ""
        ).strip()
        description = request.POST.get("description", "").strip()
        eligibility_criteria = request.POST.get(
            "eligibility_criteria", ""
        ).strip()
        maximum_budget = request.POST.get("maximum_budget", "0").strip()
        deadline = request.POST.get("deadline") or None

        try:
            budget = Decimal(maximum_budget)
            if budget < 0:
                raise InvalidOperation

            GrantCategory.objects.create(
                category_name=category_name,
                description=description,
                eligibility_criteria=eligibility_criteria,
                maximum_budget=budget,
                deadline=deadline,
            )

            messages.success(request, "Grant category added.")
            return redirect("manage_categories")

        except IntegrityError:
            messages.error(request, "This category name already exists.")
        except (InvalidOperation, ValueError):
            messages.error(request, "Enter a valid non-negative budget.")
        except ValidationError as error:
            messages.error(request, str(error))

    return render(request, "admin/add_category.html")


@role_required("admin")
def manage_categories(request):
    categories = GrantCategory.objects.all().order_by("category_name")

    return render(request, "admin/manage_categories.html", {
        "categories": categories,
    })


@role_required("admin")
def edit_grant_category(request, category_id):
    category = get_object_or_404(GrantCategory, pk=category_id)

    if request.method == "POST":
        category_name = request.POST.get(
            "category_name", ""
        ).strip()
        description = request.POST.get("description", "").strip()
        eligibility = request.POST.get(
            "eligibility_criteria", ""
        ).strip()
        maximum_budget = request.POST.get("maximum_budget", "0").strip()
        deadline = request.POST.get("deadline") or None
        is_active = request.POST.get("is_active") == "on"

        try:
            budget = Decimal(maximum_budget)
            if budget < 0 or not category_name:
                raise InvalidOperation

            category.category_name = category_name
            category.description = description
            category.eligibility_criteria = eligibility
            category.maximum_budget = budget
            category.deadline = deadline
            category.is_active = is_active
            category.save()

            messages.success(request, "Category updated.")
            return redirect("manage_categories")

        except IntegrityError:
            messages.error(request, "That category name is already in use.")
        except (InvalidOperation, ValueError):
            messages.error(request, "Enter a valid category name and budget.")
        except ValidationError as error:
            messages.error(request, str(error))

    return render(request, "admin/edit_category.html", {
        "category": category,
    })


@role_required("admin")
@require_POST
def delete_grant_category(request, category_id):
    category = get_object_or_404(GrantCategory, pk=category_id)

    if category.proposals.exists():
        messages.error(
            request,
            "This category has proposals. Deactivate it instead of deleting it."
        )
    else:
        category.delete()
        messages.success(request, "Category deleted.")

    return redirect("manage_categories")


# ==========================================================
# APPLICANT: SUBMIT AND VIEW PROPOSALS
# ==========================================================

@role_required("applicant")
def submit_proposal(request):
    categories = GrantCategory.objects.filter(
        is_active=True
    ).order_by("category_name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        abstract = request.POST.get("abstract", "").strip()
        objectives = request.POST.get("objectives", "").strip()
        methodology = request.POST.get("methodology", "").strip()
        expected_impact = request.POST.get(
            "expected_impact", ""
        ).strip()
        budget_justification = request.POST.get(
            "budget_justification", ""
        ).strip()
        requested_budget = request.POST.get(
            "requested_budget", "0"
        ).strip()
        category_id = request.POST.get("category")
        proposal_file = request.FILES.get("proposal_file")

        if not all([
            title, abstract, objectives, methodology,
            expected_impact, budget_justification, category_id,
        ]):
            messages.error(request, "Please complete all required fields.")
            return redirect("submit_proposal")

        try:
            category = GrantCategory.objects.get(
                pk=category_id,
                is_active=True,
            )
        except (GrantCategory.DoesNotExist, ValueError):
            messages.error(request, "Select a valid active category.")
            return redirect("submit_proposal")

        try:
            budget = Decimal(requested_budget)
            if budget <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            messages.error(
                request, "Enter a valid budget greater than zero."
            )
            return redirect("submit_proposal")

        if (
            category.deadline
            and category.deadline < timezone.localdate()
        ):
            messages.error(request, "The deadline for this category has passed.")
            return redirect("submit_proposal")

        if (
            category.maximum_budget > 0
            and budget > category.maximum_budget
        ):
            messages.error(
                request,
                f"Budget exceeds the category limit of "
                f"{category.maximum_budget}.",
            )
            return redirect("submit_proposal")

        try:
            valid_uploaded_document(proposal_file)

            proposal = GrantProposal.objects.create(
                applicant=request.user,
                category=category,
                title=title,
                abstract=abstract,
                objectives=objectives,
                methodology=methodology,
                expected_impact=expected_impact,
                requested_budget=budget,
                budget_justification=budget_justification,
                proposal_file=proposal_file,
                status="Pending",
            )

            if proposal.proposal_file:
                extracted_text = extract_proposal_text(
                    proposal.proposal_file
                )
                proposal.extracted_text = extracted_text
                proposal.save(update_fields=["extracted_text"])

            messages.success(request, "Proposal submitted successfully.")
            return redirect("my_proposals")

        except ValidationError as error:
            messages.error(request, " ".join(error.messages))

    return render(request, "applicant/submit_proposal.html", {
        "categories": categories,
    })


@role_required("applicant")
def my_proposals(request):
    proposals = GrantProposal.objects.filter(
        applicant=request.user
    ).select_related("category").order_by("-submitted_at")

    return render(request, "applicant/my_proposals.html", {
        "proposals": proposals,
    })


@login_required
def proposal_details(request, proposal_id):
    proposal = get_object_or_404(
        GrantProposal.objects.select_related(
            "applicant", "category"
        ),
        pk=proposal_id,
    )

    if (
        not is_admin(request.user)
        and proposal.applicant_id != request.user.id
        and not ReviewerAssignment.objects.filter(
            proposal=proposal,
            reviewer=request.user,
        ).exists()
    ):
        return HttpResponseForbidden(
            "You do not have permission to view this proposal."
        )

    analyses = proposal.analyses.order_by("-analyzed_at")
    evaluations = proposal.evaluations.select_related(
        "reviewer"
    ).order_by("-evaluated_at")

    template_name = get_entity_template(request.user, "proposal_details.html")
    return render(request, template_name, {
        "proposal": proposal,
        "analyses": analyses,
        "evaluations": evaluations,
    })


# ==========================================================
# ADMIN: NLP PROPOSAL ANALYSIS
# ==========================================================

@role_required("admin")
@require_POST
def analyze_proposal(request, proposal_id):
    proposal = get_object_or_404(
        GrantProposal.objects.select_related("category"),
        pk=proposal_id,
    )

    criteria = list(
        EvaluationCriterion.objects.filter(
            is_active=True
        ).order_by("name")
    )

    if not criteria:
        messages.error(
            request,
            "Add and activate evaluation criteria before analysis.",
        )
        return redirect("proposal_details", proposal_id=proposal.id)

    proposal_text = get_proposal_text(proposal).strip()

    if not proposal_text:
        messages.error(request, "No proposal text is available to analyze.")
        return redirect("proposal_details", proposal_id=proposal.id)

    try:
        model = get_nlp_model()

        criterion_texts = [
            f"{criterion.name}. {criterion.description}"
            for criterion in criteria
        ]

        embeddings = model.encode(
            [proposal_text] + criterion_texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

        proposal_embedding = embeddings[0]
        criterion_embeddings = embeddings[1:]

        similarities = util.cos_sim(
            proposal_embedding,
            criterion_embeddings,
        )[0]

        results = []
        for index, criterion in enumerate(criteria):
            score = max(
                0.0,
                min(1.0, float(similarities[index].item()))
            )
            results.append({
                "criterion": criterion,
                "score": score,
            })

        average_similarity = sum(
            item["score"] for item in results
        ) / len(results)

        missing_sections = []
        required_sections = {
            "Abstract": proposal.abstract,
            "Objectives": proposal.objectives,
            "Methodology": proposal.methodology,
            "Expected Impact": proposal.expected_impact,
            "Budget Justification": proposal.budget_justification,
        }

        for section, content in required_sections.items():
            if not content or not content.strip():
                missing_sections.append(section)

        matched_criteria = [
            item["criterion"].name
            for item in results
            if item["score"] >= 0.40
        ]

        summary = (
            f"Analyzed {len(criteria)} active criteria using "
            f"all-MiniLM-L6-v2. Mean semantic similarity: "
            f"{average_similarity * 100:.2f}%. "
            f"Potentially matched criteria: {len(matched_criteria)} "
            f"of {len(criteria)}. "
            "This is a text-similarity result, not an automated "
            "funding decision."
        )

        with transaction.atomic():
            analysis = ProposalAnalysis.objects.create(
                proposal=proposal,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                analysis_summary=summary,
                similarity_score=average_similarity * 100,
                missing_sections=", ".join(missing_sections),
                matched_criteria=", ".join(matched_criteria),
                analysis_details={
                    "criteria_count": len(criteria),
                    "matched_count": len(matched_criteria),
                    "similarity_scale": "0-100 percentage",
                    "missing_sections": missing_sections,
                },
            )

            CriterionAnalysis.objects.bulk_create([
                CriterionAnalysis(
                    analysis=analysis,
                    criterion=item["criterion"],
                    similarity_score=item["score"] * 100,
                    evidence=(
                        "Semantic similarity between the proposal text "
                        "and the criterion name/description. Review the "
                        "original proposal to verify evidence."
                    ),
                )
                for item in results
            ])

        messages.success(request, "NLP analysis completed successfully.")
        return redirect(
            "proposal_analysis_details",
            proposal_id=proposal.id,
            analysis_id=analysis.id,
        )

    except Exception as error:
        messages.error(
            request,
            f"NLP analysis failed: {error}",
        )
        return redirect("proposal_details", proposal_id=proposal.id)


@login_required
def proposal_analysis_details(request, proposal_id, analysis_id=None):
    proposal = get_object_or_404(GrantProposal, pk=proposal_id)

    if (
        not is_admin(request.user)
        and proposal.applicant_id != request.user.id
        and not ReviewerAssignment.objects.filter(
            proposal=proposal,
            reviewer=request.user,
        ).exists()
    ):
        return HttpResponseForbidden(
            "You do not have permission to view this analysis."
        )

    analyses = proposal.analyses.order_by("-analyzed_at")

    if analysis_id is not None:
        analysis = get_object_or_404(
            ProposalAnalysis,
            pk=analysis_id,
            proposal=proposal,
        )
    else:
        analysis = analyses.first()

    if analysis is None:
        messages.info(request, "This proposal has not been analyzed yet.")
        return redirect("proposal_details", proposal_id=proposal.id)

    criterion_results = analysis.criterion_results.select_related(
        "criterion"
    ).order_by("-similarity_score")

    template_name = get_entity_template(request.user, "proposal_analysis_details.html")
    return render(request, template_name, {
        "proposal": proposal,
        "analysis": analysis,
        "analyses": analyses,
        "criterion_results": criterion_results,
    })


# ==========================================================
# ADMIN: PROPOSAL MANAGEMENT
# ==========================================================

@role_required("admin")
def admin_proposals(request):
    proposals = GrantProposal.objects.select_related(
        "applicant", "category"
    ).order_by("-submitted_at")

    status = request.GET.get("status", "").strip()
    if status in dict(GrantProposal.STATUS_CHOICES):
        proposals = proposals.filter(status=status)

    return render(request, "admin/admin_proposals.html", {
        "proposals": proposals,
        "status_choices": GrantProposal.STATUS_CHOICES,
        "selected_status": status,
    })


@role_required("admin")
@require_POST
def update_proposal_status(request, proposal_id):
    proposal = get_object_or_404(GrantProposal, pk=proposal_id)
    new_status = request.POST.get("status", "").strip()

    valid_statuses = dict(GrantProposal.STATUS_CHOICES)

    if new_status not in valid_statuses:
        messages.error(request, "Invalid proposal status.")
    else:
        proposal.status = new_status
        proposal.save(update_fields=["status", "updated_at"])
        messages.success(request, "Proposal status updated.")

    return redirect("admin_proposals")


# ==========================================================
# ADMIN: EVALUATION CRITERIA
# ==========================================================

@role_required("admin")
def manage_criteria(request):
    criteria = EvaluationCriterion.objects.all().order_by("name")

    return render(request, "admin/manage_criteria.html", {
        "criteria": criteria,
    })


@role_required("admin")
def add_criterion(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        weight_text = request.POST.get("weight", "1").strip()
        is_active = request.POST.get("is_active") == "on"

        try:
            weight = float(weight_text)
            if not name or not description or weight <= 0:
                raise ValueError

            EvaluationCriterion.objects.create(
                name=name,
                description=description,
                weight=weight,
                is_active=is_active,
            )

            messages.success(request, "Evaluation criterion added.")
            return redirect("manage_criteria")

        except IntegrityError:
            messages.error(request, "This criterion name already exists.")
        except (ValueError, TypeError):
            messages.error(
                request,
                "Enter a name, description, and positive numeric weight.",
            )

    return render(request, "admin/add_criterion.html")


@role_required("admin")
def edit_criterion(request, criterion_id):
    criterion = get_object_or_404(
        EvaluationCriterion,
        pk=criterion_id,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        weight_text = request.POST.get("weight", "1").strip()
        is_active = request.POST.get("is_active") == "on"

        try:
            weight = float(weight_text)
            if not name or not description or weight <= 0:
                raise ValueError

            criterion.name = name
            criterion.description = description
            criterion.weight = weight
            criterion.is_active = is_active
            criterion.save()

            messages.success(request, "Criterion updated.")
            return redirect("manage_criteria")

        except IntegrityError:
            messages.error(request, "This criterion name already exists.")
        except (ValueError, TypeError):
            messages.error(
                request,
                "Enter a name, description, and positive numeric weight.",
            )

    return render(request, "admin/edit_criterion.html", {
        "criterion": criterion,
    })


@role_required("admin")
@require_POST
def delete_criterion(request, criterion_id):
    criterion = get_object_or_404(
        EvaluationCriterion,
        pk=criterion_id,
    )

    # Preserve previous evaluation records by deactivating the criterion.
    criterion.is_active = False
    criterion.save(update_fields=["is_active"])

    messages.success(
        request,
        "Criterion deactivated. Existing analysis records are preserved.",
    )
    return redirect("manage_criteria")


# ==========================================================
# ADMIN: ASSIGN REVIEWERS
# ==========================================================

@role_required("admin")
def assign_reviewer(request, proposal_id):
    proposal = get_object_or_404(GrantProposal, pk=proposal_id)

    reviewers = Login.objects.filter(
        user_type__iexact="Reviewer",
        is_active=True,
    ).order_by("username")

    assignments = ReviewerAssignment.objects.filter(
        proposal=proposal
    ).select_related("reviewer")

    if request.method == "POST":
        reviewer_id = request.POST.get("reviewer")

        try:
            reviewer = reviewers.get(pk=reviewer_id)

            assignment, created = ReviewerAssignment.objects.get_or_create(
                proposal=proposal,
                reviewer=reviewer,
            )

            if created:
                proposal.status = "Under Review"
                proposal.save(update_fields=["status", "updated_at"])
                messages.success(request, "Reviewer assigned successfully.")
            else:
                messages.info(
                    request, "This reviewer is already assigned."
                )

            return redirect(
                "assign_reviewer",
                proposal_id=proposal.id,
            )

        except (Login.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Select a valid reviewer.")

    return render(request, "admin/assign_reviewer.html", {
        "proposal": proposal,
        "reviewers": reviewers,
        "assignments": assignments,
    })


# ==========================================================
# REVIEWER: ASSIGNED PROPOSALS
# ==========================================================

@role_required("reviewer")
def assigned_proposals(request):
    assignments = ReviewerAssignment.objects.filter(
        reviewer=request.user
    ).select_related(
        "proposal",
        "proposal__category",
        "proposal__applicant",
    ).order_by("-assigned_at")

    return render(request, "reviewer/assigned_proposals.html", {
        "assignments": assignments,
    })


# ==========================================================
# REVIEWER: EVALUATE PROPOSAL
# ==========================================================

@role_required("reviewer")
def evaluate_proposal(request, proposal_id):
    proposal = get_object_or_404(GrantProposal, pk=proposal_id)

    assignment = get_object_or_404(
        ReviewerAssignment,
        proposal=proposal,
        reviewer=request.user,
    )

    evaluation, _ = Evaluation.objects.get_or_create(
        proposal=proposal,
        reviewer=request.user,
    )

    if request.method == "POST":
        try:
            innovation = float(request.POST.get("innovation_score", "0"))
            feasibility = float(request.POST.get("feasibility_score", "0"))
            impact = float(request.POST.get("impact_score", "0"))
            methodology = float(request.POST.get("methodology_score", "0"))
            budget = float(request.POST.get("budget_score", "0"))

            scores = [
                innovation, feasibility, impact, methodology, budget
            ]

            if any(score < 0 or score > 10 for score in scores):
                raise ValueError("Scores must be between 0 and 10.")

            decision = request.POST.get("decision", "").strip()
            valid_decisions = dict(Evaluation.DECISION_CHOICES)

            if decision not in valid_decisions or decision == "Pending":
                raise ValueError("Select a valid final decision.")

            evaluation.innovation_score = innovation
            evaluation.feasibility_score = feasibility
            evaluation.impact_score = impact
            evaluation.methodology_score = methodology
            evaluation.budget_score = budget
            evaluation.total_score = sum(scores) / len(scores)
            evaluation.comments = request.POST.get("comments", "").strip()
            evaluation.decision = decision
            evaluation.save()

            assignment.is_completed = True
            assignment.save(update_fields=["is_completed"])

            messages.success(request, "Your evaluation has been saved.")
            return redirect("assigned_proposals")

        except (ValueError, TypeError) as error:
            messages.error(request, str(error))

    return render(request, "reviewer/evaluate_proposal.html", {
        "proposal": proposal,
        "assignment": assignment,
        "evaluation": evaluation,
    })


# ==========================================================
# ADMIN: VIEW EVALUATIONS
# ==========================================================

@role_required("admin")
def view_evaluations(request):
    evaluations = Evaluation.objects.select_related(
        "proposal",
        "proposal__category",
        "reviewer",
    ).order_by("-evaluated_at")

    return render(request, "admin/view_evaluations.html", {
        "evaluations": evaluations,
    })


@role_required("admin")
def proposal_evaluations(request, proposal_id):
    proposal = get_object_or_404(
        GrantProposal.objects.select_related("category", "applicant"),
        pk=proposal_id,
    )

    evaluations = Evaluation.objects.filter(
        proposal=proposal
    ).select_related("reviewer").order_by("-evaluated_at")

    assignments = ReviewerAssignment.objects.filter(
        proposal=proposal
    ).select_related("reviewer")

    if evaluations.exists():
        average_score = sum(
            evaluation.total_score for evaluation in evaluations
        ) / evaluations.count()
    else:
        average_score = None

    return render(request, "admin/proposal_evaluations.html", {
        "proposal": proposal,
        "evaluations": evaluations,
        "assignments": assignments,
        "average_score": average_score,
    })
