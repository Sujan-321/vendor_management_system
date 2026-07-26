from django.views.generic import TemplateView


class LoginView(TemplateView):
    template_name = "accounts/login.html"


class RegisterView(TemplateView):
    template_name = "accounts/register.html"


class ProfileView(TemplateView):
    template_name = "accounts/profile.html"


class ProfileUpdateView(TemplateView):
    template_name = "accounts/profile_update.html"


class ChangePasswordView(TemplateView):
    template_name = "accounts/change_password.html"