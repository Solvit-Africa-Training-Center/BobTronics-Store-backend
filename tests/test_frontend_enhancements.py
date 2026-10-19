from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.catalog.models import Category, Product, StockMovement, StockMovementType
from apps.cart.models import CartItem
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.reviews.models import Feedback

User = get_user_model()


class FrontendEnhancementsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="customer@example.com",
            password=self.password,
            first_name="Jane",
            last_name="Doe",
            phone="+250781111111",
            residence="Kigali",
            role=Role.CUSTOMER,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self.password,
            first_name="Admin",
            last_name="Boss",
            role=Role.ADMIN,
            is_active=True,
        )
        self.category = Category.objects.create(name="Audio", description="Audio accessories")
        self.product = Product.objects.create(
            category=self.category,
            name="Wireless Headphones",
            brand="Sony",
            price=Decimal("120.00"),
            stock_quantity=15,
            is_available=True,
        )

    def test_patch_accounts_me(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch("/api/v1/accounts/me/", {
            "first_name": "Janet",
            "residence": "Musanze",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Janet")
        self.assertEqual(self.user.residence, "Musanze")

    def test_change_password(self):
        self.client.force_authenticate(user=self.user)
        # Invalid current password
        bad_response = self.client.post("/api/v1/accounts/change-password/", {
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePassword456!",
            "password_confirm": "NewSecurePassword456!",
        }, format="json")
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Successful change
        good_response = self.client.post("/api/v1/accounts/change-password/", {
            "current_password": self.password,
            "new_password": "NewSecurePassword456!",
            "password_confirm": "NewSecurePassword456!",
        }, format="json")
        self.assertEqual(good_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePassword456!"))

    def test_cart_clear_via_post(self):
        self.client.force_authenticate(user=self.user)
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        response = self.client.post("/api/v1/cart/clear/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)

    def test_delivery_fees_endpoint(self):
        response = self.client.get("/api/v1/deliveries/fees/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        methods = [item["method"] for item in response.data["data"]]
        self.assertIn("standard", methods)

    def test_delivery_admin_url_aliases(self):
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("120.00"),
            shipping_address="Kigali",
            phone="+250781111111",
            status=OrderStatus.PENDING,
        )
        delivery = Delivery.objects.create(
            order=order,
            delivery_address="Kigali",
            status=DeliveryStatus.PENDING,
        )

        self.client.force_authenticate(user=self.admin)
        # Test GET /deliveries/admin/
        list_response = self.client.get("/api/v1/deliveries/admin/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Test PATCH /deliveries/admin/{id}/
        patch_response = self.client.patch(
            f"/api/v1/deliveries/admin/{delivery.delivery_id}/",
            {"status": "in_transit", "tracking_number": "TRK-999"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DeliveryStatus.IN_TRANSIT)
        self.assertEqual(delivery.tracking_number, "TRK-999")

    def test_product_ratings_and_stock_history(self):
        # Add a review
        Feedback.objects.create(
            user=self.user,
            product=self.product,
            rating=5,
            comment="Great headset",
        )
        # Test product list includes average_rating
        response = self.client.get(f"/api/v1/catalog/products/{self.product.product_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], 5.0)
        self.assertEqual(response.data["review_count"], 1)

        # Record a stock movement
        StockMovement.objects.create(
            product=self.product,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity_change=5,
            quantity_before=15,
            quantity_after=20,
            reason="Restock",
            actor=self.admin,
        )

        self.client.force_authenticate(user=self.admin)
        history_res = self.client.get(f"/api/v1/catalog/admin/products/{self.product.product_id}/stock-history/")
        self.assertEqual(history_res.status_code, status.HTTP_200_OK)
        results = history_res.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["delta"], 5)
        self.assertEqual(results[0]["resulting_stock_quantity"], 20)
