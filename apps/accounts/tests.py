import smtplib
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
import yaml

from apps.accounts.models import Role, User


class UserModelTests(TestCase):
    def test_model_includes_all_user_erd_fields(self):
        expected_fields = {
            "user_id", "first_name", "last_name", "email", "password", "phone",
            "residence", "role", "created_at", "updated_at",
        }
        model_fields = {field.name for field in User._meta.get_fields()}
        self.assertTrue(expected_fields.issubset(model_fields))

    def test_email_is_unique(self):
        User.objects.create_user(
            email="pacifique@example.com", password="safe-password",
            first_name="Pacifique", last_name="Ishimwe",
        )
        duplicate = User(email="pacifique@example.com", first_name="Another", last_name="Customer")
        with self.assertRaises(ValidationError) as raised:
            duplicate.full_clean()
        self.assertIn("email", raised.exception.message_dict)

    def test_password_is_stored_as_a_hash(self):
        user = User.objects.create_user(
            email="pacifique@example.com", password="safe-password",
            first_name="Pacifique", last_name="Ishimwe",
        )
        self.assertNotEqual(user.password, "safe-password")
        self.assertTrue(user.check_password("safe-password"))

    def test_registration_defaults_to_customer_role(self):
        user = User.objects.create_user(
            email="customer@example.com", password="safe-password",
            first_name="New", last_name="Customer",
        )
        self.assertEqual(user.role, Role.CUSTOMER)

    def test_email_is_required_by_user_manager(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="safe-password")

    def test_create_superuser_sets_required_flags(self):
        user = User.objects.create_superuser(
            email="admin@example.com", password="safe-password",
            first_name="Store", last_name="Admin",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_guest_is_not_a_persisted_user_role(self):
        self.assertNotIn("visitor", {value for value, _label in Role.choices})


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountApiTests(APITestCase):
    base_url = "/api/v1/accounts/"
    password = "Violet-Coffee!94-River"

    def create_user(self, *, email="aline@example.com", is_active=True):
        return User.objects.create_user(
            email=email, password=self.password, first_name="Aline", last_name="Uwase",
            is_active=is_active,
        )

    @staticmethod
    def email_credentials(message):
        fields = {}
        for line in message.body.splitlines():
            if line.startswith("Account reference: "):
                fields["uid"] = line.partition(": ")[2]
            elif line.startswith("Verification token: "):
                fields["token"] = line.partition(": ")[2]
        return fields

    def test_registration_creates_inactive_customer_and_sends_validation_email(self):
        response = self.client.post(self.base_url + "register/", {
            "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
            "password": self.password, "password_confirm": self.password,
            "phone": "+250780000000", "residence": "Kigali",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="aline@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("password", response.data["user"])

    @override_settings(
        SITE_URL="https://accounts.example.test",
        DEFAULT_FROM_EMAIL="BobTronics <accounts@example.test>",
    )
    def test_activation_email_uses_configured_sender_and_site_url(self):
        self.client.post(self.base_url + "register/", {
            "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
            "password": self.password, "password_confirm": self.password,
        }, format="json")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.from_email, "BobTronics <accounts@example.test>")
        self.assertIn("Link: https://accounts.example.test/api/v1/accounts/activate/?", message.body)
        self.assertIn("API endpoint: https://accounts.example.test/api/v1/accounts/activate/", message.body)

    @override_settings(SITE_URL="https://accounts.example.test")
    def test_activation_link_from_email_activates_the_registered_account(self):
        self.client.post(self.base_url + "register/", {
            "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
            "password": self.password, "password_confirm": self.password,
        }, format="json")
        user = User.objects.get(email="aline@example.com")
        self.assertFalse(user.is_active)

        activation_link = next(
            line.removeprefix("Link: ")
            for line in mail.outbox[0].body.splitlines()
            if line.startswith("Link: ")
        )
        parsed_link = urlsplit(activation_link)
        activation_response = self.client.get(parsed_link.path, parse_qs(parsed_link.query))

        self.assertEqual(activation_response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_email_delivery_failure_keeps_registration_and_reset_responses_safe(self):
        self.create_user()
        secret_error_detail = "smtp-password-must-not-be-logged"
        smtp_error = smtplib.SMTPAuthenticationError(535, secret_error_detail.encode())

        with self.assertLogs("apps.accounts.services", level="WARNING") as captured_logs:
            with patch("apps.accounts.services.send_mail", side_effect=smtp_error) as send_mock:
                registration = self.client.post(self.base_url + "register/", {
                    "first_name": "New", "last_name": "Customer", "email": "new@example.com",
                    "password": self.password, "password_confirm": self.password,
                }, format="json")
                known_reset = self.client.post(
                    self.base_url + "password-reset/", {"email": "aline@example.com"}, format="json",
                )
                unknown_reset = self.client.post(
                    self.base_url + "password-reset/", {"email": "nobody@example.com"}, format="json",
                )

        self.assertEqual(registration.status_code, 201)
        self.assertEqual(registration.data["message"], "Registration successful. Check your email for account activation instructions.")
        self.assertEqual(known_reset.status_code, 200)
        self.assertEqual(known_reset.data, unknown_reset.data)
        self.assertEqual(send_mock.call_count, 2)
        self.assertNotIn(secret_error_detail, "\n".join(captured_logs.output))
        self.assertNotIn("aline@example.com", "\n".join(captured_logs.output))

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(self.base_url + "register/", {
            "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
            "password": self.password, "password_confirm": "different-password",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="aline@example.com").exists())

    def test_activation_validates_account_once(self):
        user = self.create_user(is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(self.base_url + "activate/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        replay = self.client.post(self.base_url + "activate/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(replay.status_code, 400)

    def test_password_reset_request_is_generic_for_known_and_unknown_email(self):
        self.create_user()
        known = self.client.post(self.base_url + "password-reset/", {"email": "aline@example.com"}, format="json")
        unknown = self.client.post(self.base_url + "password-reset/", {"email": "nobody@example.com"}, format="json")

        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_changes_password(self):
        user = self.create_user()
        self.client.post(self.base_url + "password-reset/", {"email": user.email}, format="json")
        credentials = self.email_credentials(mail.outbox[-1])
        response = self.client.post(self.base_url + "password-reset/confirm/", {
            **credentials,
            "new_password": "New-Violet-Coffee!59-River",
            "password_confirm": "New-Violet-Coffee!59-River",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("New-Violet-Coffee!59-River"))

    def test_current_user_requires_authentication_and_returns_safe_profile(self):
        response = self.client.get(self.base_url + "me/")
        self.assertEqual(response.status_code, 401)
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.base_url + "me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], user.email)
        self.assertNotIn("password", response.data)

    def test_refresh_rotates_token_and_rejects_old_token(self):
        user = self.create_user()
        old_refresh = str(RefreshToken.for_user(user))
        response = self.client.post(self.base_url + "token/refresh/", {"refresh": old_refresh}, format="json")

        self.assertEqual(response.status_code, 200)
        new_refresh = response.data["refresh"]
        self.assertNotEqual(new_refresh, old_refresh)
        rejected = self.client.post(self.base_url + "token/refresh/", {"refresh": old_refresh}, format="json")
        self.assertEqual(rejected.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        user = self.create_user()
        refresh = str(RefreshToken.for_user(user))
        response = self.client.post(self.base_url + "logout/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200)

        rejected = self.client.post(self.base_url + "token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(rejected.status_code, 401)

    def test_auth_endpoints_appear_in_openapi_schema(self):
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, 200)
        schema = yaml.safe_load(response.content)
        paths = schema["paths"]
        for endpoint in (
            "/api/v1/accounts/register/", "/api/v1/accounts/activate/",
            "/api/v1/accounts/me/", "/api/v1/accounts/password-reset/",
            "/api/v1/accounts/password-reset/confirm/", "/api/v1/accounts/logout/",
            "/api/v1/accounts/token/refresh/",
        ):
            self.assertIn(endpoint, paths)
