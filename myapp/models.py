
from django.db import models
from django.contrib.auth.models import AbstractUser


class Login(AbstractUser):
    

    user_type = models.CharField(
        max_length=50,
    )

    view_pass = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return self.username



# ==========================================
# APPLICANT REGISTRATION
# ==========================================

class ApplicantRegistration(models.Model):
    user = models.OneToOneField(
        Login,
        on_delete=models.CASCADE,
        related_name='applicant_profile'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    organization = models.CharField(
        max_length=200,
        blank=True
    )

    profile_image = models.FileField(
        upload_to='applicant_profiles/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==========================================
# REVIEWER REGISTRATION
# ==========================================

class ReviewerRegistration(models.Model):
    user = models.OneToOneField(
        Login,
        on_delete=models.CASCADE,
        related_name='reviewer_profile'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    organization = models.CharField(
        max_length=200,
        blank=True
    )

    qualification = models.CharField(
        max_length=200,
        blank=True
    )

    specialization = models.CharField(
        max_length=200,
        blank=True
    )

    experience_years = models.PositiveIntegerField(default=0)

    profile_image = models.FileField(
        upload_to='reviewer_profiles/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GrantCategory(models.Model):
    category_name = models.CharField(max_length=150, unique=True)
    description = models.TextField()
    eligibility_criteria = models.TextField(blank=True)

    maximum_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.category_name


# ==========================================
# 2. GRANT PROPOSAL
# ==========================================

class GrantProposal(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('Revision Required', 'Revision Required'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    applicant = models.ForeignKey(
        Login,
        on_delete=models.CASCADE,
        related_name='grant_proposals'
    )

    category = models.ForeignKey(
        GrantCategory,
        on_delete=models.PROTECT,
        related_name='proposals'
    )

    title = models.CharField(max_length=250)
    abstract = models.TextField()
    objectives = models.TextField()
    methodology = models.TextField()
    expected_impact = models.TextField()

    requested_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    budget_justification = models.TextField()

    proposal_file = models.FileField(
        upload_to='grant_proposals/',
        null=True,
        blank=True
    )

    extracted_text = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class EvaluationCriterion(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField()

    weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==========================================
# 4. PROPOSAL NLP ANALYSIS
# ==========================================

class ProposalAnalysis(models.Model):
    proposal = models.ForeignKey(
        GrantProposal,
        on_delete=models.CASCADE,
        related_name='analyses'
    )

    model_name = models.CharField(
        max_length=200,
        default='sentence-transformers/all-MiniLM-L6-v2'
    )

    analysis_summary = models.TextField(blank=True)

    similarity_score = models.FloatField(
        null=True,
        blank=True
    )

    missing_sections = models.TextField(blank=True)
    matched_criteria = models.TextField(blank=True)

    analysis_details = models.JSONField(
        default=dict,
        blank=True
    )

    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Analysis - {self.proposal.title}'


# ==========================================
# 5. CRITERION ANALYSIS
# ==========================================

class CriterionAnalysis(models.Model):
    analysis = models.ForeignKey(
        ProposalAnalysis,
        on_delete=models.CASCADE,
        related_name='criterion_results'
    )

    criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        related_name='proposal_results'
    )

    similarity_score = models.FloatField(
        null=True,
        blank=True
    )

    evidence = models.TextField(blank=True)

    def __str__(self):
        return (
            f'{self.analysis.proposal.title} - '
            f'{self.criterion.name}'
        )

# ==========================================
# 6. REVIEWER ASSIGNMENT
# ==========================================

class ReviewerAssignment(models.Model):
    proposal = models.ForeignKey(
        GrantProposal,
        on_delete=models.CASCADE,
        related_name='reviewer_assignments'
    )

    reviewer = models.ForeignKey(
        Login,
        on_delete=models.CASCADE,
        related_name='reviewer_assignments'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['proposal', 'reviewer'],
                name='unique_proposal_reviewer'
            )
        ]

    def __str__(self):
        return (
            f'{self.reviewer.username} - '
            f'{self.proposal.title}'
        )


# ==========================================
# 7. HUMAN REVIEWER EVALUATION
# ==========================================

class Evaluation(models.Model):

    DECISION_CHOICES = [
        ('Pending', 'Pending'),
        ('Recommend', 'Recommend'),
        ('Not Recommend', 'Not Recommend'),
        ('Revision Required', 'Revision Required'),
    ]

    proposal = models.ForeignKey(
        GrantProposal,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )

    reviewer = models.ForeignKey(
        Login,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )

    innovation_score = models.FloatField(default=0)
    feasibility_score = models.FloatField(default=0)
    impact_score = models.FloatField(default=0)
    methodology_score = models.FloatField(default=0)
    budget_score = models.FloatField(default=0)

    total_score = models.FloatField(default=0)

    comments = models.TextField(blank=True)

    decision = models.CharField(
        max_length=30,
        choices=DECISION_CHOICES,
        default='Pending'
    )

    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['proposal', 'reviewer'],
                name='unique_proposal_evaluation'
            )
        ]

    def __str__(self):
        return (
            f'Evaluation - {self.proposal.title} - '
            f'{self.reviewer.username}'
        )
