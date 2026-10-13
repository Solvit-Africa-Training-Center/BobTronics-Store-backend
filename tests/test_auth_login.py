from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User


class LoginAPITestCase(APITestCase):
    def setUp(self):
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
            "Account is not activated. Please verify your email before logging in.",
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
