from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "google-auth-tests",
        }
    }
)
class GoogleAuthAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.api_v1_url = reverse("auth-google-login")
        self.direct_url = reverse("auth-google-login-direct")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_unconfigured_client_id_returns_503_api_v1(self):
        response = self.client.post(self.api_v1_url, {"credential": "dummy-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Google sign-in is not configured", str(response.data))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_unconfigured_client_id_returns_503_direct_url(self):
        response = self.client.post(self.direct_url, {"credential": "dummy-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Google sign-in is not configured", str(response.data))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_successful_google_login_new_user(self, mock_verify):
        mock_verify.return_value = {
            "sub": "1234567890",
            "email": "alice@gmail.com",
            "email_verified": True,
            "name": "Alice Munezero",
            "given_name": "Alice",
            "family_name": "Munezero",
        }
        response = self.client.post(self.api_v1_url, {"credential": "valid-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "alice@gmail.com")

        # Verify user created in DB
        user = User.objects.get(email="alice@gmail.com")
        self.assertEqual(user.google_sub, "1234567890")
        self.assertEqual(user.first_name, "Alice")
        self.assertEqual(user.last_name, "Munezero")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_successful_google_login_existing_user(self, mock_verify):
        user = User.objects.create_user(
            email="bob@gmail.com",
            first_name="Bob",
            last_name="Smith",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
            is_active=True,
        )
        mock_verify.return_value = {
            "sub": "9876543210",
            "email": "bob@gmail.com",
            "email_verified": True,
            "name": "Bob Smith",
            "given_name": "Bob",
            "family_name": "Smith",
        }
        response = self.client.post(self.direct_url, {"credential": "valid-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.google_sub, "9876543210")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_unverified_email_returns_400(self, mock_verify):
        mock_verify.return_value = {
            "sub": "11111",
            "email": "unverified@gmail.com",
            "email_verified": False,
        }
        response = self.client.post(self.api_v1_url, {"credential": "unverified-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
