from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.catalog.models import Category, Product
from apps.promotions.models import Discount, DiscountType
from apps.promotions.services import calculate_discount, calculate_discounted_price

User = get_user_model()


class DiscountApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(email="discount-admin@test.local", password="SafePass123!", first_name="Ada", last_name="Admin", role=Role.ADMIN)
        cls.category = Category.objects.create(name="Discount devices")
        cls.product = Product.objects.create(category=cls.category, name="Discount phone", brand="Example", price=Decimal("100.00"), stock_quantity=5)

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
        response = self.client.post(reverse("admin-discount-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Discount.objects.count(), 1)

    def test_percentage_over_100_is_rejected(self):
        response = self.client.post(reverse("admin-discount-list"), self.payload(discount_value="101.00"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_date_before_start_date_is_rejected(self):
        response = self.client.post(reverse("admin-discount-list"), self.payload(start_date="2026-11-10", end_date="2026-11-09"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_manage_discounts(self):
        customer = User.objects.create_user(email="regular@test.local", password="SafePass123!", first_name="Chris", last_name="Customer", role=Role.CUSTOMER)
        self.client.force_authenticate(customer)
        response = self.client.post(reverse("admin-discount-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_calculator_uses_best_valid_discount_without_stacking(self):
        today = date.today()
        Discount.objects.create(product=self.product, discount_type=DiscountType.PERCENTAGE, discount_value="10.00", start_date=today, end_date=today)
        Discount.objects.create(product=self.product, discount_type=DiscountType.FIXED, discount_value="20.00", start_date=today, end_date=today)
        Discount.objects.create(product=self.product, discount_type=DiscountType.FIXED, discount_value="99.00", start_date=today - timedelta(days=2), end_date=today - timedelta(days=1))
        self.assertEqual(calculate_discount(self.product, on_date=today), Decimal("20.00"))
        self.assertEqual(calculate_discounted_price(self.product, on_date=today), Decimal("80.00"))

    def test_fixed_discount_is_capped_at_product_price(self):
        today = date.today()
        Discount.objects.create(product=self.product, discount_type=DiscountType.FIXED, discount_value="150.00", start_date=today, end_date=today)
        self.assertEqual(calculate_discount(self.product, on_date=today), Decimal("100.00"))
        self.assertEqual(calculate_discounted_price(self.product, on_date=today), Decimal("0.00"))
