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


class PasswordResetView(TemplateView):
    template_name = "accounts/password_reset.html"


class PasswordResetDoneView(TemplateView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(TemplateView):
    template_name = "accounts/password_reset_confirm.html"


class PasswordResetCompleteView(TemplateView):
    template_name = "accounts/password_reset_complete.html"