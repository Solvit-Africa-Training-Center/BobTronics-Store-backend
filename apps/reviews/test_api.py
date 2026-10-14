from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.reviews.models import Feedback

User = get_user_model()


class FeedbackApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(email="buyer@test.local", password="SafePass123!", first_name="Bea", last_name="Buyer", role=Role.CUSTOMER)
        cls.other_customer = User.objects.create_user(email="other@test.local", password="SafePass123!", first_name="Ollie", last_name="Other", role=Role.CUSTOMER)
        category = Category.objects.create(name="Feedback devices")
        cls.product = Product.objects.create(category=category, name="Reviewed phone", brand="Example", price=Decimal("100.00"), stock_quantity=5)

    def create_order(self, user, status_value):
        order = Order.objects.create(user=user, status=status_value, total_amount=Decimal("100.00"), shipping_address="1 Main Street", phone="+250700000000")
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=Decimal("100.00"), subtotal=Decimal("100.00"))
        return order

    def test_delivered_buyer_can_create_feedback(self):
        self.create_order(self.customer, OrderStatus.DELIVERED)
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 5, "comment": "Good device"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.customer.pk)
        self.assertEqual(Feedback.objects.get().user, self.customer)

    def test_customer_without_delivered_order_cannot_review(self):
        self.create_order(self.customer, OrderStatus.PENDING)
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 4}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_review_another_users_purchase(self):
        self.create_order(self.customer, OrderStatus.DELIVERED)
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 4}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_review_per_customer_and_product(self):
        self.create_order(self.customer, OrderStatus.DELIVERED)
        Feedback.objects.create(user=self.customer, product=self.product, rating=4, comment="Already reviewed")
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_id_cannot_be_supplied_by_client(self):
        self.create_order(self.customer, OrderStatus.DELIVERED)
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 5, "user": self.other_customer.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.customer.pk)

    def test_feedback_list_is_public_and_filterable_by_product(self):
        Feedback.objects.create(user=self.customer, product=self.product, rating=4)
        response = self.client.get(reverse("feedback-list"), {"product": self.product.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_rating_outside_range_is_rejected(self):
        self.create_order(self.customer, OrderStatus.DELIVERED)
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("feedback-list"), {"product": self.product.pk, "rating": 6}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
