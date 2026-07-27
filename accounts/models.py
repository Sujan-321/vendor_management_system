from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


phone_validator = RegexValidator(
    regex=r'^\+977\s98\d{8}$',
    message="Phone number must be in the format: +977 98XXXXXXXX"
)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField( max_length=15, blank=True, validators=[phone_validator])
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username