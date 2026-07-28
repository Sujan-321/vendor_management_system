from django.views.generic import TemplateView, CreateView
from .models import User
from .forms import RegistrationForm
from django.urls import reverse_lazy
from django.contrib import messages

class LoginView(TemplateView):
    template_name = "accounts/login.html"


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_invalid(self, form):
        print(form.errors)   # Look in your terminal
        return super().form_invalid(form)

    def form_valid(self, form):
        messages.success(
            self.request,
            "Account created successfully. Please log in."
        )
        return super().form_valid(form)


class ProfileView(TemplateView):
    template_name = "accounts/profile.html"


class ProfileUpdateView(TemplateView):
    template_name = "accounts/profile_update.html"


class ChangePasswordView(TemplateView):
    template_name = "accounts/change_password.html"


class PasswordResetView(TemplateView):
    template_name = "accounts/password_reset.html"


class PasswordResetDoneView(TemplateView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(TemplateView):
    template_name = "accounts/password_reset_confirm.html"


class PasswordResetCompleteView(TemplateView):
    template_name = "accounts/password_reset_complete.html"