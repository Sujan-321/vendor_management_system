from django.urls import path
from .views import (
    LoginView,
    RegisterView,
    ProfileView,
    ProfileUpdateView,
    ChangePasswordView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

app_name = 'accounts'

urlpatterns = [
    path("", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/update/", ProfileUpdateView.as_view(), name="profile_update"),
    path("password/change/", ChangePasswordView.as_view(), name="change_password"),
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path("password/reset/done/", PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]