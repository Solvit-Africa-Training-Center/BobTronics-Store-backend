"""
Test suite for Member C — Day 2: Customer Profile & Address APIs

Endpoints covered:
    GET  /api/v1/customers/profile/          (CustomerProfileView)
    PUT  /api/v1/customers/profile/          (CustomerProfileView)
    PATCH /api/v1/customers/profile/         (CustomerProfileView)
    GET  /api/v1/customers/address/          (CustomerAddressView)
    PUT  /api/v1/customers/address/          (CustomerAddressView)
    PATCH /api/v1/customers/address/         (CustomerAddressView)
    GET  /api/v1/customers/                  (AdminCustomerListView)
    GET  /api/v1/customers/<user_id>/        (AdminCustomerDetailView)
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_jwt_header(user):
    """Return an Authorization header dict for the given user."""
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}


def make_customer(email, first_name="Test", last_name="Customer",
                  phone="", residence="", is_active=True):
    return User.objects.create_user(
        email=email,
        password="StrongPass123!",
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        residence=residence,
        role=Role.CUSTOMER,
        is_active=is_active,
    )


def make_admin(email, role=Role.ADMIN):
    return User.objects.create_user(
        email=email,
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
        role=role,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. Customer Profile  (GET / PUT / PATCH)
# ---------------------------------------------------------------------------

class CustomerProfileGetTestCase(APITestCase):
    """GET /api/v1/customers/profile/"""

    def setUp(self):
        self.url = reverse("customers:customer-profile")
        self.customer = make_customer(
            email="alice@bobtronics.com",
            first_name="Alice",
            last_name="Munro",
            phone="+250788000001",
            residence="Kigali, Rwanda",
        )
        self.auth = get_jwt_header(self.customer)

    def test_authenticated_customer_can_fetch_profile(self):
        response = self.client.get(self.url, **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "alice@bobtronics.com")
        self.assertEqual(response.data["first_name"], "Alice")
        self.assertEqual(response.data["last_name"], "Munro")
        self.assertEqual(response.data["phone"], "+250788000001")
        self.assertEqual(response.data["residence"], "Kigali, Rwanda")
        self.assertEqual(response.data["role"], Role.CUSTOMER)

    def test_profile_response_includes_order_analytics(self):
        response = self.client.get(self.url, **self.auth)

        self.assertIn("total_orders", response.data)
        self.assertIn("total_spent", response.data)
        # New customer has no orders
        self.assertEqual(response.data["total_orders"], 0)
        self.assertEqual(response.data["total_spent"], "0.00")

    def test_profile_response_includes_read_only_timestamps(self):
        response = self.client.get(self.url, **self.auth)

        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomerProfileUpdateTestCase(APITestCase):
    """PUT / PATCH /api/v1/customers/profile/"""

    def setUp(self):
        self.url = reverse("customers:customer-profile")
        self.customer = make_customer(
            email="bob@bobtronics.com",
            first_name="Bob",
            last_name="Tronics",
        )
        self.auth = get_jwt_header(self.customer)

    def test_put_updates_all_allowed_fields(self):
        payload = {
            "first_name": "Robert",
            "last_name":  "Tronics-Updated",
            "phone":      "+250788999888",
            "residence":  "Musanze, Rwanda",
        }
        response = self.client.put(self.url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        user_data = response.data["user"]
        self.assertEqual(user_data["first_name"], "Robert")
        self.assertEqual(user_data["last_name"], "Tronics-Updated")
        self.assertEqual(user_data["phone"], "+250788999888")
        self.assertEqual(user_data["residence"], "Musanze, Rwanda")

    def test_patch_updates_only_supplied_fields(self):
        payload = {"phone": "+250700111222"}
        response = self.client.patch(self.url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["phone"], "+250700111222")
        # Other fields remain unchanged
        self.assertEqual(response.data["user"]["first_name"], "Bob")

    def test_email_field_is_immutable(self):
        """Email must be ignored on update — it is a protected field."""
        payload = {"email": "hacked@evil.com", "first_name": "Bob"}
        response = self.client.put(self.url, payload, format="json", **self.auth)

        # Request still succeeds (extra fields are ignored, not rejected)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "bob@bobtronics.com")

    def test_role_field_is_immutable(self):
        payload = {"role": Role.ADMIN, "first_name": "Bob"}
        self.client.patch(self.url, payload, format="json", **self.auth)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, Role.CUSTOMER)

    def test_blank_first_name_is_rejected(self):
        payload = {"first_name": "   "}
        response = self.client.patch(self.url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data)

    def test_blank_last_name_is_rejected(self):
        payload = {"last_name": "   "}
        response = self.client.patch(self.url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last_name", response.data)

    def test_whitespace_is_stripped_from_name_fields(self):
        payload = {"first_name": "  Robert  ", "last_name": "  Tech  "}
        response = self.client.patch(self.url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["first_name"], "Robert")
        self.assertEqual(response.data["user"]["last_name"], "Tech")

    def test_unauthenticated_update_is_rejected(self):
        response = self.client.patch(self.url, {"first_name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 2. Customer Address  (GET / PUT / PATCH)
# ---------------------------------------------------------------------------

class CustomerAddressTestCase(APITestCase):
    """GET / PUT / PATCH /api/v1/customers/address/"""

    def setUp(self):
        self.url = reverse("customers:customer-address")
        self.customer = make_customer(
            email="carol@bobtronics.com",
            first_name="Carol",
            last_name="Kariuki",
            phone="+250783000001",
            residence="Huye, Rwanda",
        )
        self.auth = get_jwt_header(self.customer)

    def test_get_returns_current_address(self):
        response = self.client.get(self.url, **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["residence"], "Huye, Rwanda")
        self.assertEqual(response.data["phone"], "+250783000001")

    def test_put_updates_address_and_phone(self):
        payload = {"residence": "Rubavu, Rwanda", "phone": "+250789123456"}
        response = self.client.put(self.url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("address", response.data)
        self.assertEqual(response.data["address"]["residence"], "Rubavu, Rwanda")
        self.assertEqual(response.data["address"]["phone"], "+250789123456")

    def test_patch_updates_only_residence(self):
        payload = {"residence": "Nyagatare, Rwanda"}
        response = self.client.patch(self.url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["address"]["residence"], "Nyagatare, Rwanda")

    def test_blank_residence_is_rejected(self):
        payload = {"residence": "   "}
        response = self.client.put(self.url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("residence", response.data)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_success_response_includes_message(self):
        payload = {"residence": "Kicukiro, Kigali"}
        response = self.client.put(self.url, payload, format="json", **self.auth)
        self.assertIn("message", response.data)


# ---------------------------------------------------------------------------
# 3. Admin Customer List  (GET /api/v1/customers/)
# ---------------------------------------------------------------------------

class AdminCustomerListTestCase(APITestCase):
    """GET /api/v1/customers/  — AdminCustomerListView"""

    def setUp(self):
        self.url = reverse("customers:customer-list")

        self.admin = make_admin("admin@bobtronics.com", role=Role.ADMIN)
        self.super_admin = make_admin("super@bobtronics.com", role=Role.SUPER_ADMIN)
        self.customer = make_customer("david@bobtronics.com",
                                     first_name="David", last_name="Dufitumukiza")

        self.admin_auth = get_jwt_header(self.admin)
        self.super_admin_auth = get_jwt_header(self.super_admin)
        self.customer_auth = get_jwt_header(self.customer)

    def test_admin_can_list_customers(self):
        response = self.client.get(self.url, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_super_admin_can_list_customers(self):
        response = self.client.get(self.url, **self.super_admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_access_admin_list(self):
        response = self.client.get(self.url, **self.customer_auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_response_is_paginated(self):
        response = self.client.get(self.url, **self.admin_auth)
        # DRF PageNumberPagination returns count + results
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)

    def test_list_contains_only_customers(self):
        response = self.client.get(self.url, **self.admin_auth)
        for item in response.data["results"]:
            self.assertEqual(item["role"], Role.CUSTOMER)

    def test_list_result_contains_total_orders_field(self):
        response = self.client.get(self.url, **self.admin_auth)
        for item in response.data["results"]:
            self.assertIn("total_orders", item)

    def test_search_by_first_name(self):
        response = self.client.get(self.url, {"search": "David"}, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["first_name"], "David")

    def test_search_by_email(self):
        response = self.client.get(self.url, {"search": "david@"}, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_ordering_by_created_at(self):
        response = self.client.get(self.url, {"ordering": "created_at"}, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 4. Admin Customer Detail  (GET /api/v1/customers/<user_id>/)
# ---------------------------------------------------------------------------

class AdminCustomerDetailTestCase(APITestCase):
    """GET /api/v1/customers/<user_id>/  — AdminCustomerDetailView"""

    def setUp(self):
        self.admin = make_admin("admin2@bobtronics.com")
        self.customer = make_customer(
            email="eve@bobtronics.com",
            first_name="Eve",
            last_name="Ingabire",
            phone="+250780001111",
            residence="Gasabo, Kigali",
        )
        self.url = reverse("customers:customer-detail",
                           kwargs={"user_id": self.customer.user_id})
        self.admin_auth = get_jwt_header(self.admin)
        self.customer_auth = get_jwt_header(self.customer)

    def test_admin_can_fetch_customer_detail(self):
        response = self.client.get(self.url, **self.admin_auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "eve@bobtronics.com")
        self.assertEqual(response.data["first_name"], "Eve")

    def test_detail_response_includes_analytics_and_recent_orders(self):
        response = self.client.get(self.url, **self.admin_auth)

        self.assertIn("total_orders", response.data)
        self.assertIn("total_spent", response.data)
        self.assertIn("recent_orders", response.data)
        self.assertIsInstance(response.data["recent_orders"], list)

    def test_customer_cannot_access_other_customer_detail(self):
        response = self.client.get(self.url, **self.customer_auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_customer_returns_404(self):
        url = reverse("customers:customer-detail", kwargs={"user_id": 999999})
        response = self.client.get(url, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
