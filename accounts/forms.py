from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm

from .models import User

class RegistrationForm(UserCreationForm):
    ROLE_CHOICES = (
        ('Customer', 'Customer'),
        ('Vendor', 'Vendor'),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class":"form-select"})
    )

    agree_terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields=(
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


