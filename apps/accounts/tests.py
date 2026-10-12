from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Role, User


class UserModelTests(TestCase):
    def test_model_includes_all_user_erd_fields(self):
        expected_fields = {
            "user_id",
            "first_name",
            "last_name",
            "email",
            "password",
            "phone",
            "residence",
            "role",
            "created_at",
            "updated_at",
        }
        model_fields = {field.name for field in User._meta.get_fields()}
        self.assertTrue(expected_fields.issubset(model_fields))

    def test_email_is_unique(self):
        User.objects.create_user(
            email="pacifique@example.com",
            password="safe-password",
            first_name="Pacifique",
            last_name="Ishimwe",
        )
        duplicate = User(
            email="pacifique@example.com",
            first_name="Another",
            last_name="Customer",
        )

        with self.assertRaises(ValidationError) as raised:
            duplicate.full_clean()

        self.assertIn("email", raised.exception.message_dict)

    def test_password_is_stored_as_a_hash(self):
        user = User.objects.create_user(
            email="pacifique@example.com",
            password="safe-password",
            first_name="Pacifique",
            last_name="Ishimwe",
        )

        self.assertNotEqual(user.password, "safe-password")
        self.assertTrue(user.check_password("safe-password"))

    def test_registration_defaults_to_customer_role(self):
        user = User.objects.create_user(
            email="customer@example.com",
            password="safe-password",
            first_name="New",
            last_name="Customer",
        )

        self.assertEqual(user.role, Role.CUSTOMER)

    def test_email_is_required_by_user_manager(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="safe-password")

    def test_create_superuser_sets_required_flags(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="safe-password",
            first_name="Store",
            last_name="Admin",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_guest_is_not_a_persisted_user_role(self):
        role_values = {value for value, _label in Role.choices}

        self.assertNotIn("visitor", role_values)
