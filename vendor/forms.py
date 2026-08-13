from django import forms
from .models import Product, ProductImage, Vendor


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





class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput()
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            result = []

            for file in data:
                result.append(
                    single_file_clean(file, initial)
                )

            return result

        if data:
            return [single_file_clean(data, initial)]

        return []
        

class ProductImageForm(forms.Form):

    images = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={
            "class": "d-none",
            "accept": "image/png,image/jpeg,image/jpg",
        })
    )

    def clean_images(self):

        images = self.cleaned_data["images"]

        if not images:
            raise forms.ValidationError(
                "Please select at least one image."
            )

        for image in images:

            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    f"{image.name} is larger than 5MB."
                )

            if image.content_type not in [
                "image/jpeg",
                "image/png",
            ]:
                raise forms.ValidationError(
                    f"{image.name} is not a valid JPG or PNG image."
                )

        return images






class ShopInformationForm(forms.ModelForm):

    class Meta:
        model = Vendor
        fields = [
            "shop_name",
            "description",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "website",
            "is_active",
        ]

        widgets = {
            "shop_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter shop name",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your shop",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter shop address",
                }
            ),

            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter city",
                }
            ),

            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter state/province",
                }
            ),

            "country": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter country",
                }
            ),

            "postal_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter postal code",
                }
            ),

            "website": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }





