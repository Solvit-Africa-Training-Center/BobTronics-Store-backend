from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.cart.models import CartItem
from apps.catalog.models import Category, Product
from apps.deliveries.models import Delivery, DeliveryMethod, DeliveryStatus
from apps.deliveries.services import (
    calculate_shipping_fee,
    create_delivery_for_order,
    generate_tracking_number,
)
from apps.orders.models import Order, OrderStatus

User = get_user_model()


class DeliveryServiceTests(APITestCase):
    """Unit tests for delivery services."""

    def setUp(self):
        self.customer = User.objects.create_user(
            email="deliveryservice@test.com",
            password="StrongPassword123!",
            first_name="Jean",
            last_name="Paul",
            role=Role.CUSTOMER,
        )
        self.order = Order.objects.create(
            user=self.customer,
            shipping_address="KG 100 St, Kigali",
            phone="+250788111222",
            total_amount=Decimal("500.00"),
            status=OrderStatus.PENDING,
        )

    def test_calculate_shipping_fee(self):
        self.assertEqual(calculate_shipping_fee(DeliveryMethod.STORE_PICKUP), Decimal("0.00"))
        self.assertEqual(calculate_shipping_fee(DeliveryMethod.STANDARD), Decimal("1500.00"))
        self.assertEqual(calculate_shipping_fee(DeliveryMethod.EXPRESS), Decimal("4000.00"))

    def test_generate_tracking_number_format(self):
        tracking = generate_tracking_number()
        self.assertTrue(tracking.startswith("BT-DEL-"))
        self.assertEqual(len(tracking), 20)

    def test_create_delivery_for_order(self):
        delivery = create_delivery_for_order(
            order=self.order,
            delivery_address="KG 100 St, Kigali",
            delivery_method=DeliveryMethod.EXPRESS,
        )
        self.assertEqual(delivery.order, self.order)
        self.assertEqual(delivery.status, DeliveryStatus.PENDING)
        self.assertEqual(delivery.delivery_method, DeliveryMethod.EXPRESS)
        self.assertEqual(delivery.shipping_fee, Decimal("4000.00"))
        self.assertTrue(delivery.tracking_number.startswith("BT-DEL-"))
        self.assertIsNone(delivery.shipped_at)
        self.assertIsNone(delivery.delivered_at)

    def test_create_delivery_idempotent_if_already_exists(self):
        d1 = create_delivery_for_order(self.order)
        d2 = create_delivery_for_order(self.order)
        self.assertEqual(d1.pk, d2.pk)


class DeliveryApiTests(APITestCase):
    """Integration API tests for customer and admin delivery flows."""

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@bobtronics.test",
            password="StrongPassword123!",
            first_name="Aline",
            last_name="Mutesi",
            role=Role.CUSTOMER,
        )
        self.other_customer = User.objects.create_user(
            email="other@bobtronics.test",
            password="StrongPassword123!",
            first_name="Bob",
            last_name="Buyer",
            role=Role.CUSTOMER,
        )
        self.admin = User.objects.create_user(
            email="admin@bobtronics.test",
            password="StrongPassword123!",
            first_name="Admin",
            last_name="User",
            role=Role.ADMIN,
        )

        self.category = Category.objects.create(name="Accessories", description="Gadgets")
        self.product = Product.objects.create(
            category=self.category,
            name="Power Bank 20000mAh",
            brand="Anker",
            price=Decimal("45.00"),
            stock_quantity=20,
            is_available=True,
        )

        self.order = Order.objects.create(
            user=self.customer,
            shipping_address="Remera, Kigali",
            phone="+250788333444",
            total_amount=Decimal("45.00"),
            status=OrderStatus.PENDING,
        )
        self.delivery = create_delivery_for_order(
            order=self.order,
            delivery_address="Remera, Kigali",
            delivery_method=DeliveryMethod.STANDARD,
        )

    def test_customer_can_view_own_order_delivery(self):
        self.client.force_authenticate(self.customer)
        url = reverse("deliveries:order-delivery", kwargs={"order_id": self.order.order_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["tracking_number"], self.delivery.tracking_number)
        self.assertEqual(response.data["data"]["status"], DeliveryStatus.PENDING)

    def test_other_customer_cannot_view_foreign_order_delivery(self):
        self.client.force_authenticate(self.other_customer)
        url = reverse("deliveries:order-delivery", kwargs={"order_id": self.order.order_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_package_tracking_without_authentication(self):
        url = reverse("deliveries:public-tracking", kwargs={"tracking_number": self.delivery.tracking_number})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["tracking_number"], self.delivery.tracking_number)
        self.assertEqual(response.data["data"]["delivery_method"], "standard")

    def test_public_package_tracking_not_found(self):
        url = reverse("deliveries:public-tracking", kwargs={"tracking_number": "NON-EXISTENT-TRACKING"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_list_all_deliveries(self):
        self.client.force_authenticate(self.admin)
        url = reverse("deliveries:admin-delivery-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_regular_customer_blocked_from_admin_delivery_list(self):
        self.client.force_authenticate(self.customer)
        url = reverse("deliveries:admin-delivery-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_update_delivery_status_to_in_transit(self):
        self.client.force_authenticate(self.admin)
        url = reverse(
            "deliveries:admin-delivery-status-update",
            kwargs={"delivery_id": self.delivery.delivery_id},
        )
        response = self.client.patch(url, {"status": DeliveryStatus.IN_TRANSIT}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, DeliveryStatus.IN_TRANSIT)
        self.assertIsNotNone(self.delivery.shipped_at)

        # Linked order moves to SHIPPED
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.SHIPPED)
        self.assertTrue(
            AuditLog.objects.filter(
                action="delivery.status_changed",
                entry_type="Delivery",
                entity_id=self.delivery.delivery_id,
                user=self.admin,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="order.status_changed",
                entry_type="Order",
                entity_id=self.order.order_id,
                user=self.admin,
            ).exists()
        )

    def test_admin_update_delivery_status_to_delivered(self):
        self.client.force_authenticate(self.admin)
        # First transition to IN_TRANSIT
        self.delivery.status = DeliveryStatus.IN_TRANSIT
        self.delivery.save()

        url = reverse(
            "deliveries:admin-delivery-status-update",
            kwargs={"delivery_id": self.delivery.delivery_id},
        )
        response = self.client.patch(url, {"status": DeliveryStatus.DELIVERED}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, DeliveryStatus.DELIVERED)
        self.assertIsNotNone(self.delivery.delivered_at)

        # Linked order moves to DELIVERED
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)

    def test_admin_invalid_status_transition_is_rejected(self):
        self.client.force_authenticate(self.admin)
        # Cannot jump straight from PENDING to DELIVERED
        url = reverse(
            "deliveries:admin-delivery-status-update",
            kwargs={"delivery_id": self.delivery.delivery_id},
        )
        response = self.client.patch(url, {"status": DeliveryStatus.DELIVERED}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_automatically_creates_delivery_record(self):
        self.client.force_authenticate(self.customer)
        # Add item to cart
        CartItem.objects.create(user=self.customer, product=self.product, quantity=2)

        checkout_url = reverse("orders:order-checkout")
        response = self.client.post(
            checkout_url,
            {
                "shipping_address": "Kimironko, Kigali",
                "phone": "+250788777888",
                "delivery_method": DeliveryMethod.EXPRESS,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_data = response.data["data"]

        # Verify delivery is included in order response
        self.assertIn("delivery", order_data)
        self.assertIsNotNone(order_data["delivery"])
        self.assertEqual(order_data["delivery"]["delivery_method"], "express")
        self.assertEqual(order_data["delivery"]["status"], "pending")
        self.assertTrue(order_data["delivery"]["tracking_number"].startswith("BT-DEL-"))

        # Verify delivery exists in DB
        delivery_row = Delivery.objects.get(order_id=order_data["order_id"])
        self.assertEqual(delivery_row.delivery_method, DeliveryMethod.EXPRESS)
        self.assertEqual(delivery_row.shipping_fee, Decimal("4000.00"))
