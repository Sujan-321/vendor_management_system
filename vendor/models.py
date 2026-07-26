from django.db import models
from django.utils.text import slugify
from accounts.models import User


class Vendor(models.Model):

    APPROVAL_STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor")
    shop_name = models.CharField(max_length=200)
    shop_slug = models.SlugField(max_length=220, unique=True, blank=True)
    owner_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    logo = models.ImageField(upload_to="vendors/logo/", blank=True, null=True)
    banner = models.ImageField(upload_to="vendors/banner/", blank=True, null=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    approval_status = models.CharField(max_length=10, choices=APPROVAL_STATUS, default="PENDING")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["shop_name"]
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        return self.shop_name

    def save(self, *args, **kwargs):
        if not self.shop_slug:
            self.shop_slug = slugify(self.shop_name)
        super().save(*args, **kwargs)