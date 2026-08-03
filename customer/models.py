from django.db import models
from accounts.models import User
from vendor.models import Product

class Customer(models.Model):

    GENDER = (
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer")
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="customers/profile/", blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return self.full_name


class Cart(models.Model):
    customer = models.OneToOneField(
        "Customer",
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.full_name} Cart"

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def subtotal(self):
        return self.product.final_price * self.quantity

    def __str__(self):
        return self.product.name

class Wishlist(models.Model):
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="wishlist"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "product")

    def __str__(self):
        return f"{self.customer.full_name} - {self.product.name}"