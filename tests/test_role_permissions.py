from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsCustomer, IsOwnerOrAdmin, IsSuperAdmin


class DefaultProtectedView(APIView):
    def get(self, request):
        return Response({"ok": True})


class RolePermissionTests(TestCase):
    def setUp(self):
        self.customer = self.create_user("customer@example.com", Role.CUSTOMER)
        self.admin = self.create_user("admin@example.com", Role.ADMIN)
        self.super_admin = self.create_user("super@example.com", Role.SUPER_ADMIN)
        self.staff_customer = self.create_user("staff-customer@example.com", Role.CUSTOMER, is_staff=True)
        self.factory = APIRequestFactory()

    @staticmethod
    def create_user(email, role, **extra_fields):
        return User.objects.create_user(
            email=email,
            password="Test-password-42!",
            first_name="Test",
            last_name="User",
            role=role,
            **extra_fields,
        )

    def request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_customer_permission_accepts_only_customer_role(self):
        permission = IsCustomer()
        self.assertTrue(permission.has_permission(self.request_for(self.customer), None))
        self.assertFalse(permission.has_permission(self.request_for(self.admin), None))
        self.assertFalse(permission.has_permission(self.request_for(AnonymousUser()), None))

    def test_admin_permission_uses_roles_not_django_staff_flags(self):
        permission = IsAdminOrSuperAdmin()
        self.assertTrue(permission.has_permission(self.request_for(self.admin), None))
        self.assertTrue(permission.has_permission(self.request_for(self.super_admin), None))
        self.assertFalse(permission.has_permission(self.request_for(self.customer), None))
        self.assertFalse(permission.has_permission(self.request_for(self.staff_customer), None))

    def test_super_admin_permission_is_restricted_to_super_admin_role(self):
        permission = IsSuperAdmin()
        self.assertTrue(permission.has_permission(self.request_for(self.super_admin), None))
        self.assertFalse(permission.has_permission(self.request_for(self.admin), None))

    def test_owner_permission_allows_customer_own_records_and_admins(self):
        permission = IsOwnerOrAdmin()
        own_record = SimpleNamespace(user=self.customer)
        other_record = SimpleNamespace(user=self.admin)
        request = self.request_for(self.customer)

        self.assertTrue(permission.has_permission(request, None))
        self.assertTrue(permission.has_object_permission(request, None, self.customer))
        self.assertTrue(permission.has_object_permission(request, None, own_record))
        self.assertFalse(permission.has_object_permission(request, None, other_record))
        self.assertTrue(permission.has_object_permission(self.request_for(self.admin), None, other_record))

    def test_unconfigured_api_view_requires_authentication_by_default(self):
        view = DefaultProtectedView.as_view()
        anonymous_response = view(self.factory.get("/"))
        self.assertEqual(anonymous_response.status_code, 401)

        request = self.factory.get("/")
        force_authenticate(request, user=self.customer)
        authenticated_response = view(request)
        self.assertEqual(authenticated_response.status_code, 200)

    def test_health_schema_and_swagger_remain_public(self):
        client = Client(HTTP_HOST="localhost")
        for endpoint in ("/api/v1/health/", "/api/v1/schema/", "/api/v1/docs/"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(client.get(endpoint).status_code, 200)
