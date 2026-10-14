from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.audit.models import AuditLog
from apps.accounts.models import Role
from apps.orders.models import Order

from .admin import PaymentAdmin
from .models import Payment, PaymentMethod, PaymentStatus

User = get_user_model()


class PaymentAdminAuditTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="payment-admin@example.test",
            password="StrongPassword123!",
            first_name="Payment",
            last_name="Admin",
            role=Role.ADMIN,
            is_staff=True,
        )
        customer = User.objects.create_user(
            email="payment-customer@example.test",
            password="StrongPassword123!",
            first_name="Payment",
            last_name="Customer",
        )
        self.order = Order.objects.create(
            user=customer,
            shipping_address="Kigali",
            phone="+250780000000",
            total_amount=Decimal("250.00"),
        )
        self.request = RequestFactory().post("/admin/")
        self.request.user = self.admin_user
        self.request.META["REMOTE_ADDR"] = "192.0.2.15"
        self.payment_admin = PaymentAdmin(Payment, admin.site)

    def test_payment_creation_and_status_change_are_audited(self):
        payment = Payment(
            order=self.order,
            amount=Decimal("250.00"),
            payment_method=PaymentMethod.CASH_ON_DELIVERY,
            transaction_reference="test-payment-ref",
            status=PaymentStatus.PENDING,
        )
        self.payment_admin.save_model(self.request, payment, form=None, change=False)

        payment.status = PaymentStatus.PAID
        self.payment_admin.save_model(self.request, payment, form=None, change=True)

        self.assertTrue(
            AuditLog.objects.filter(
                action="payment.created",
                entry_type="Payment",
                entity_id=payment.payment_id,
                user=self.admin_user,
            ).exists()
        )
        status_event = AuditLog.objects.get(
            action="payment.status_changed",
            entry_type="Payment",
            entity_id=payment.payment_id,
        )
        self.assertEqual(status_event.user, self.admin_user)
        self.assertEqual(status_event.ip_address, "192.0.2.15")
        self.assertIn("pending to paid", status_event.description)
