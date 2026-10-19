import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Role, User
from apps.accounts.views import LoginRateThrottle


@override_settings(CACHES={
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "auth-login-tests",
    }
})
class LoginAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("auth-login")
        self.refresh_url = reverse("token-refresh")

        # 1. Active Customer
        self.active_user = User.objects.create_user(
            email="pacifique@bobtronics.com",
            password="StrongPassword123!",
            first_name="Pacifique",
            last_name="Ishimwe",
            role=Role.CUSTOMER,
            is_active=True,
        )

        # 2. Inactive Customer (registered but email not yet verified)
        self.inactive_user = User.objects.create_user(
            email="unverified@bobtronics.com",
            password="StrongPassword123!",
            first_name="Unverified",
            last_name="User",
            role=Role.CUSTOMER,
            is_active=False,
        )

    def test_successful_login_returns_tokens_and_profile(self):
        data = {
            "email": "pacifique@bobtronics.com",
            "password": "StrongPassword123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        access_token = AccessToken(response.data["tokens"]["access"])
        self.assertEqual(access_token["exp"] - access_token["iat"], 15 * 60)

        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "pacifique@bobtronics.com")
        self.assertEqual(response.data["user"]["role"], Role.CUSTOMER)
        self.assertEqual(response.data["user"]["first_name"], "Pacifique")

    def test_login_case_insensitive_email(self):
        data = {
            "email": "PACIFIQUE@BOBTRONICS.COM",
            "password": "StrongPassword123!",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "pacifique@bobtronics.com")

    def test_inactive_user_cannot_login(self):
        data = {
            "email": "unverified@bobtronics.com",
            "password": "StrongPassword123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn(
            "Verify your email before logging in.",
            response.data["error"]["message"],
        )

    def test_wrong_password_returns_generic_error(self):
        data = {
            "email": "pacifique@bobtronics.com",
            "password": "WrongPassword999!",
        }
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("Invalid email or password.", response.data["error"]["message"])

    def test_nonexistent_email_returns_generic_error(self):
        data = {
            "email": "ghost@bobtronics.com",
            "password": "SomePassword123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("Invalid email or password.", response.data["error"]["message"])

    @patch.dict(LoginRateThrottle.THROTTLE_RATES, {"auth_login": "100/minute"})
    def test_five_failed_attempts_lock_login_for_that_email_and_ip(self):
        data = {"email": "pacifique@bobtronics.com", "password": "wrong-password"}
        with patch.object(User, "check_password", return_value=False):
            for _ in range(5):
                response = self.client.post(self.login_url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.login_url,
            {"email": "pacifique@bobtronics.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid email or password.", response.data["error"]["message"])

    @patch.dict(LoginRateThrottle.THROTTLE_RATES, {"auth_login": "100/minute"})
    def test_lockout_expires(self):
        data = {"email": "pacifique@bobtronics.com", "password": "wrong-password"}
        with patch("apps.accounts.serializers.LOGIN_LOCKOUT_SECONDS", 1):
            with patch.object(User, "check_password", return_value=False):
                for _ in range(5):
                    self.client.post(self.login_url, data, format="json")
            time.sleep(1.1)
            with patch.object(User, "check_password", return_value=True):
                response = self.client.post(
                    self.login_url,
                    {"email": "pacifique@bobtronics.com", "password": "StrongPassword123!"},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.dict(LoginRateThrottle.THROTTLE_RATES, {"auth_login": "100/minute"})
    def test_successful_login_clears_failed_attempts(self):
        wrong = {"email": "pacifique@bobtronics.com", "password": "wrong-password"}
        correct = {"email": "pacifique@bobtronics.com", "password": "StrongPassword123!"}
        outcomes = [False] * 4 + [True] + [False] * 4 + [True]
        with patch.object(User, "check_password", side_effect=outcomes):
            for _ in range(4):
                response = self.client.post(self.login_url, wrong, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.client.post(self.login_url, correct, format="json").status_code, status.HTTP_200_OK)
            for _ in range(4):
                response = self.client.post(self.login_url, wrong, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response = self.client.post(self.login_url, correct, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh_workflow(self):
        # First login to obtain refresh token
        login_response = self.client.post(
            self.login_url,
            {"email": "pacifique@bobtronics.com", "password": "StrongPassword123!"},
            format="json",
        )
        refresh_token = login_response.data["tokens"]["refresh"]

        # Use refresh token to obtain a new access token
        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)
