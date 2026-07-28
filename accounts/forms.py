from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm

from .models import User

class RegistrationForm(UserCreationForm):
    ROLE_CHOICES = (
        ("Customer", "Customer"),
        ("Vendor", "Vendor"),
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "johndoe",
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
        })
    )

    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+977 9812345678",
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••",
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••",
        })
    )


    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select"
        })
    )

    agree_terms = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input"
        })
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "profile_image",
            "password1",
            "password2",
        )


    def clean_email(self):
        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already register")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.profile_image = self.cleaned_data.get("profile_image")

        if commit:
            user.save()

            role = self.cleaned_data["role"]

            group, created = Group.objects.get_or_create(name=role)
            user.groups.add(group)

        return user


