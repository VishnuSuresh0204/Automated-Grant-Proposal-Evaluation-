
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

