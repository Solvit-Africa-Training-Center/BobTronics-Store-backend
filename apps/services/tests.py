from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.audit.models import AuditLog

from .models import Service, ServiceStatus, ServiceType

User = get_user_model()


class ServiceApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            email="customer@bobtronics.test",
            password="StrongPass123!",
            first_name="Casey",
            last_name="Customer",
            role=Role.CUSTOMER,
        )
        cls.other_customer = User.objects.create_user(
            email="other@bobtronics.test",
            password="StrongPass123!",
            first_name="Rory",
            last_name="Customer",
            role=Role.CUSTOMER,
        )
        cls.admin = User.objects.create_user(
            email="admin@bobtronics.test",
            password="StrongPass123!",
            first_name="Alex",
            last_name="Admin",
            role=Role.ADMIN,
        )

    def customer_url(self):
        return reverse("services:service-list-create")

    def customer_detail_url(self, service):
        return reverse("services:service-detail", args=[service.service_id])

    def admin_url(self):
        return reverse("services:admin-service-list")

    def admin_detail_url(self, service):
        return reverse("services:admin-service-detail", args=[service.service_id])

    def make_service(self, user=None, **overrides):
        fields = {
            "user": user or self.customer,
            "name": "Laptop repair",
            "description": "The laptop does not start.",
            "service_type": ServiceType.HARDWARE_MAINTENANCE,
        }
        fields.update(overrides)
        return Service.objects.create(**fields)

    def test_customer_can_create_service_request(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.customer_url(),
            {
                "name": "Network setup",
                "description": "Set up a small office network.",
                "service_type": ServiceType.NETWORK_INFRASTRUCTURE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ServiceStatus.NEW)
        self.assertEqual(response.data["user_id"], self.customer.user_id)
        self.assertIsNone(response.data["estimated_cost"])
        self.assertIsNone(response.data["final_cost"])
        self.assertTrue(
            AuditLog.objects.filter(
                action="service_request.created",
                entry_type="Service",
                entity_id=response.data["service_id"],
                user=self.customer,
            ).exists()
        )

    def test_customer_cannot_set_owner_status_or_costs(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.customer_url(),
            {
                "name": "Repair request",
                "description": "Please inspect this device.",
                "service_type": ServiceType.OTHER,
                "user": self.admin.user_id,
                "status": ServiceStatus.COMPLETED,
                "estimated_cost": "1.00",
                "final_cost": "1.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user_id"], self.customer.user_id)
        self.assertEqual(response.data["status"], ServiceStatus.NEW)
        self.assertIsNone(response.data["estimated_cost"])
        self.assertIsNone(response.data["final_cost"])

    def test_invalid_service_type_is_rejected(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.customer_url(),
            {
                "name": "Repair request",
                "description": "Please inspect this device.",
                "service_type": "not-a-service",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_list_contains_only_their_requests(self):
        own = self.make_service()
        self.make_service(user=self.other_customer, name="Other request")
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.customer_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["service_id"] for item in response.data["results"]],
            [own.service_id],
        )

    def test_customer_can_view_own_request(self):
        service = self.make_service()
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.customer_detail_url(service))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["service_id"], service.service_id)

    def test_customer_cannot_view_another_customers_request(self):
        service = self.make_service(user=self.other_customer)
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.customer_detail_url(service))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_customer_routes_are_rejected(self):
        response = self.client.get(self.customer_url())
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_admin_cannot_use_customer_self_service_routes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.customer_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_filter_service_requests(self):
        selected = self.make_service()
        self.make_service(
            user=self.other_customer,
            name="Consultation",
            service_type=ServiceType.IT_CONSULTANCY,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            self.admin_url(),
            {"status": ServiceStatus.NEW, "service_type": ServiceType.HARDWARE_MAINTENANCE},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["service_id"] for item in response.data["results"]],
            [selected.service_id],
        )

    def test_customer_cannot_access_admin_routes(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.admin_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_must_move_request_to_in_progress_before_completion(self):
        service = self.make_service()
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.admin_detail_url(service),
            {"status": ServiceStatus.COMPLETED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.NEW)
        self.assertIsNone(service.completed_at)

    def test_admin_can_progress_and_complete_request_with_final_cost(self):
        service = self.make_service()
        self.client.force_authenticate(self.admin)

        started = self.client.patch(
            self.admin_detail_url(service),
            {"status": ServiceStatus.IN_PROGRESS, "estimated_cost": "75.50"},
            format="json",
        )
        self.assertEqual(started.status_code, status.HTTP_200_OK)
        self.assertEqual(started.data["status"], ServiceStatus.IN_PROGRESS)

        completed = self.client.patch(
            self.admin_detail_url(service),
            {"status": ServiceStatus.COMPLETED, "final_cost": "70.00"},
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.data["status"], ServiceStatus.COMPLETED)
        self.assertEqual(completed.data["final_cost"], "70.00")
        service.refresh_from_db()
        self.assertIsNotNone(service.completed_at)
        self.assertEqual(
            AuditLog.objects.filter(
                action="service_request.status_changed",
                entry_type="Service",
                entity_id=service.service_id,
                user=self.admin,
            ).count(),
            2,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="service_request.costs_changed",
                entry_type="Service",
                entity_id=service.service_id,
                user=self.admin,
            ).exists()
        )

    def test_admin_cannot_set_final_cost_before_completion(self):
        service = self.make_service()
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.admin_detail_url(service),
            {"final_cost": "70.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_set_negative_cost(self):
        service = self.make_service()
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.admin_detail_url(service),
            {"estimated_cost": "-1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_reopen_terminal_request(self):
        service = self.make_service(status=ServiceStatus.COMPLETED)
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.admin_detail_url(service),
            {"status": ServiceStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
