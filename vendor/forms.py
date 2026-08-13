from django import forms
from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "category",
            "name",
            "sku",
            "description",
            "price",
            "discount_price",
            "stock",
            "weight",
            "image",
            "is_active",
            "is_featured",
        ]

        widgets = {
            "category": forms.Select(attrs={
                "class": "form-select",
            }),

            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product name",
            }),

            "sku": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "samsung s24 ultra=> SM-S24-UA",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Describe the product",
            }),

            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "1000.00",
            }),

            "discount_price": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "800.00",
            }),


            "stock": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "0",
            }),

            "weight": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "1.5",
            }),

            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/png,image/jpeg",
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "is_featured": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")

        if (
            price is not None
            and discount_price is not None
            and discount_price >= price
        ):
            self.add_error(
                "discount_price",
                "Discount price must be less than the regular price."
            )

        return cleaned_data