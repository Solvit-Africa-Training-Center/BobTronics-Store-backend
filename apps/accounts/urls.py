from django.urls import path

from apps.accounts.views import (
    ActivateView,
    CurrentUserView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activate/", ActivateView.as_view(), name="activate"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
]
