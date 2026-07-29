from django.views.generic import TemplateView, CreateView
from .models import User
from .forms import RegistrationForm, UserLoginForm
from django.urls import reverse_lazy
from django.contrib import messages

class LoginView(TemplateView):
    template_name = "accounts/login.html"
    authentication_form = UserLoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")

        if not remember_me:
            self.request.session.set_expiry(0)

        messages.success(self.request, "Logged in successfully.")

        return super().form_valid(form)

    def get_success_url(self):

        user = self.request.user

        if user.is_superuser:
            return reverse_lazy("admin:index")

        # if user.groups.filter(name="Teacher").exists():  # here we check the data is present in the Teacher 
        #     return reverse_lazy("teacher:teacher_dashboard")    # it render the user in the teacher urls.py file

        # if user.groups.filter(name="Student").exists():
        #     return reverse_lazy("student_dashboard")

        return reverse_lazy("home")


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