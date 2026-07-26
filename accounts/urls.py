from django.urls import path
from .views import LoginView, RegisterView, ProfileUpdateView, ProfileView, ChangePasswordView

app_name = 'accounts'

urlpatterns = [
    path("", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("profile-update/<int:pk>/", ProfileUpdateView.as_view(), name="profile_update"),
    path("profile/<int:pk>/", ProfileView.as_view(), name="profile"),
    path("password-change/<int:pk>/", ChangePasswordView.as_view(), name="password_change"),
    path("password-change/<int:pk>/", ChangePasswordView.as_view(), name="password_reset"),
]