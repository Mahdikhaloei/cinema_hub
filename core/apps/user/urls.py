from apps.user.views import EmailVerificationView, LoginView, LogoutView, RegisterUserView
from django.urls import path

app_name = "auth"

urlpatterns = [
    path("email/", EmailVerificationView.as_view(), name="auth_request"),
    path("login-password/", LoginView.as_view(), name="login"),
    path("register/", RegisterUserView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
