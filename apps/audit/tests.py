from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .models import AuditLog
from .services import log_audit_event

User = get_user_model()


class AuditLogServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="audit-user@example.test",
            password="StrongPassword123!",
            first_name="Audit",
            last_name="User",
        )

    def test_log_audit_event_records_actor_entry_and_server_ip(self):
        request = RequestFactory().post("/api/v1/orders/")
        request.META["REMOTE_ADDR"] = "192.0.2.20"

        event = log_audit_event(
            action="order.created",
            entry_type="Order",
            entity_id=42,
            user=self.user,
            description="Order created with status pending.",
            request=request,
        )

        self.assertEqual(event.action, "order.created")
        self.assertEqual(event.entry_type, "Order")
        self.assertEqual(event.entity_id, 42)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.ip_address, "192.0.2.20")

    def test_audit_event_can_be_created_without_user_or_request(self):
        event = log_audit_event(
            action="system.event",
            entry_type="Order",
            description="Automated action.",
        )

        self.assertIsNone(event.user)
        self.assertIsNone(event.ip_address)

# Create your tests here.
