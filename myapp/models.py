
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


class Registration(models.Model):
    user = models.ForeignKey(
        Login,
        on_delete=models.CASCADE,
        related_name='registration'
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
        upload_to='profiles/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


