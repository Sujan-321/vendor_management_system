from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    # vendor, category, name, slug, sku, description, price, discount_price, stock
    # image, is_active, is_featured

    class Meta:
        model = Product
        fields = [
            "vendor",
            "category",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "discount_price",
            "stock",
            "image"
        ]