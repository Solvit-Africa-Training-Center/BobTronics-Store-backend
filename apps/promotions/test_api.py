from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.cart.models import CartItem
from apps.catalog.models import Category, Product
from apps.orders.models import Order
from apps.promotions.models import Discount, DiscountType
from apps.promotions.services import calculate_discount, calculate_discounted_price

User = get_user_model()


class DiscountApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="discount-admin@test.local",
            password="SafePass123!",
            first_name="Ada",
            last_name="Admin",
            role=Role.ADMIN,
        )
        cls.customer = User.objects.create_user(
            email="regular@test.local",
            password="SafePass123!",
            first_name="Chris",
            last_name="Customer",
            role=Role.CUSTOMER,
        )
        cls.category = Category.objects.create(name="Discount devices")
        cls.product = Product.objects.create(
            category=cls.category,
            name="Discount phone",
            brand="Example",
            price=Decimal("100.00"),
            stock_quantity=10,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def payload(self, **overrides):
        payload = {
            "product": self.product.pk,
            "discount_type": "percentage",
            "discount_value": "15.00",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=5)).isoformat(),
            "is_active": True,
        }
        payload.update(overrides)
        return payload

    def test_admin_can_create_discount(self):
        response = self.client.post(
            reverse("admin-discount-list"), self.payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Discount.objects.count(), 1)

    def test_percentage_over_100_is_rejected(self):
        response = self.client.post(
            reverse("admin-discount-list"),
            self.payload(discount_value="101.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_date_before_start_date_is_rejected(self):
        response = self.client.post(
            reverse("admin-discount-list"),
            self.payload(start_date="2026-11-10", end_date="2026-11-09"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_manage_discounts(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("admin-discount-list"), self.payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_calculator_uses_best_valid_discount_without_stacking(self):
        today = date.today()
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value="10.00",
            start_date=today,
            end_date=today,
        )
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED,
            discount_value="20.00",
            start_date=today,
            end_date=today,
        )
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED,
            discount_value="99.00",
            start_date=today - timedelta(days=2),
            end_date=today - timedelta(days=1),
        )
        self.assertEqual(
            calculate_discount(self.product, on_date=today), Decimal("20.00")
        )
        self.assertEqual(
            calculate_discounted_price(self.product, on_date=today),
            Decimal("80.00"),
        )

    def test_fixed_discount_is_capped_at_product_price(self):
        today = date.today()
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED,
            discount_value="150.00",
            start_date=today,
            end_date=today,
        )
        self.assertEqual(
            calculate_discount(self.product, on_date=today), Decimal("100.00")
        )
        self.assertEqual(
            calculate_discounted_price(self.product, on_date=today), Decimal("0.00")
        )

    def test_public_active_promotions_list(self):
        self.client.logout()
        today = date.today()
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value="25.00",
            start_date=today,
            end_date=today + timedelta(days=3),
            is_active=True,
        )
        response = self.client.get(reverse("promotions-active"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["savings_amount"], "25.00")
        self.assertEqual(results[0]["discounted_price"], "75.00")

    def test_public_product_discount_endpoint(self):
        self.client.logout()
        today = date.today()
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED,
            discount_value="15.00",
            start_date=today,
            end_date=today + timedelta(days=2),
            is_active=True,
        )
        url = reverse(
            "promotions-product-discount", kwargs={"product_id": self.product.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_discount"])
        self.assertEqual(Decimal(str(response.data["savings_amount"])), Decimal("15.00"))
        self.assertEqual(Decimal(str(response.data["discounted_price"])), Decimal("85.00"))

    def test_order_checkout_applies_active_discount(self):
        today = date.today()
        # 20% discount on $100 product = $20 discount per unit, $80 discounted price
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value="20.00",
            start_date=today,
            end_date=today + timedelta(days=5),
            is_active=True,
        )

        # Customer adds 2 units to cart (Total without discount: $200. Total with discount: $160)
        CartItem.objects.create(
            user=self.customer, product=self.product, quantity=2
        )

        self.client.force_authenticate(self.customer)
        checkout_url = reverse("orders:order-checkout")
        payload = {
            "shipping_address": "Kigali, Nyarugenge",
            "phone": "+250788111999",
            "delivery_method": "standard",
        }
        response = self.client.post(checkout_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order_data = response.data["data"]
        # Expected total = 2 * ($100 - $20) = $160.00
        self.assertEqual(Decimal(str(order_data["total_amount"])), Decimal("160.00"))

        # Verify line item saved discount
        order = Order.objects.get(pk=order_data["order_id"])
        item = order.items.first()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("100.00"))
        self.assertEqual(item.discount_amount, Decimal("40.00"))  # $20 * 2
        self.assertEqual(item.subtotal, Decimal("160.00"))

    def test_order_checkout_ignores_expired_discount(self):
        today = date.today()
        # Expired yesterday
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED,
            discount_value="30.00",
            start_date=today - timedelta(days=5),
            end_date=today - timedelta(days=1),
            is_active=True,
        )

        CartItem.objects.create(
            user=self.customer, product=self.product, quantity=1
        )

        self.client.force_authenticate(self.customer)
        checkout_url = reverse("orders:order-checkout")
        payload = {
            "shipping_address": "Kigali, Gasabo",
            "phone": "+250788111999",
        }
        response = self.client.post(checkout_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order_data = response.data["data"]
        # Full price charged because promotion expired
        self.assertEqual(Decimal(str(order_data["total_amount"])), Decimal("100.00"))
        order = Order.objects.get(pk=order_data["order_id"])
        item = order.items.first()
        self.assertEqual(item.discount_amount, Decimal("0.00"))
        self.assertEqual(item.subtotal, Decimal("100.00"))
