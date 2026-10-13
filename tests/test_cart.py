from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.cart.models import CartItem
from apps.catalog.models import Category, Product


def make_user(email="customer@bobtronics.com", role=Role.CUSTOMER):
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": "Test",
            "last_name": "Customer",
            "role": role,
            "is_active": True,
        },
    )
    user.set_password("Password123!")
    user.save()
    return user


def get_auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class CartAPITestCase(APITestCase):
    def setUp(self):
        self.customer = make_user("cart_customer@bobtronics.com")
        self.auth = get_auth_header(self.customer)

        self.category = Category.objects.create(name="Laptops")
        self.product = Product.objects.create(
            category=self.category,
            name="ThinkPad X1",
            brand="Lenovo",
            price=Decimal("1200.00"),
            stock_quantity=10,
            is_available=True,
        )
        self.product_out_of_stock = Product.objects.create(
            category=self.category,
            name="MacBook Pro",
            brand="Apple",
            price=Decimal("2000.00"),
            stock_quantity=0,
            is_available=True,
        )
        self.product_unavailable = Product.objects.create(
            category=self.category,
            name="Old Laptop",
            brand="Dell",
            price=Decimal("500.00"),
            stock_quantity=5,
            is_available=False,
        )

        self.cart_url = reverse("cart:cart-summary")
        self.add_item_url = reverse("cart:cart-add-item")
        self.clear_cart_url = reverse("cart:cart-clear")

    def test_unauthenticated_cart_access_is_rejected(self):
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_cart_returns_zero_totals(self):
        response = self.client.get(self.cart_url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["total_items"], 0)
        self.assertEqual(response.data["data"]["total_price"], "0.00")
        self.assertEqual(len(response.data["data"]["items"]), 0)

    def test_add_product_to_cart_success(self):
        payload = {"product_id": self.product.product_id, "quantity": 2}
        response = self.client.post(self.add_item_url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["quantity"], 2)
        self.assertEqual(Decimal(str(response.data["data"]["subtotal"])), Decimal("2400.00"))

        cart_item = CartItem.objects.get(user=self.customer, product=self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_adding_existing_product_increments_quantity(self):
        # Add 2 first
        self.client.post(self.add_item_url, {"product_id": self.product.product_id, "quantity": 2}, format="json", **self.auth)
        # Add 3 more
        response = self.client.post(self.add_item_url, {"product_id": self.product.product_id, "quantity": 3}, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["quantity"], 5)

        cart_item = CartItem.objects.get(user=self.customer, product=self.product)
        self.assertEqual(cart_item.quantity, 5)

    def test_cannot_add_exceeding_stock_quantity(self):
        payload = {"product_id": self.product.product_id, "quantity": 15}  # stock is 10
        response = self.client.post(self.add_item_url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_add_out_of_stock_product(self):
        payload = {"product_id": self.product_out_of_stock.product_id, "quantity": 1}
        response = self.client.post(self.add_item_url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_add_unavailable_product(self):
        payload = {"product_id": self.product_unavailable.product_id, "quantity": 1}
        response = self.client.post(self.add_item_url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_cart_item_quantity(self):
        item = CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        url = reverse("cart:cart-item-detail", kwargs={"cart_item_id": item.cart_item_id})

        response = self.client.patch(url, {"quantity": 4}, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_update_cart_item_exceeding_stock_fails(self):
        item = CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        url = reverse("cart:cart-item-detail", kwargs={"cart_item_id": item.cart_item_id})

        response = self.client.patch(url, {"quantity": 15}, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_delete_cart_item(self):
        item = CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        url = reverse("cart:cart-item-detail", kwargs={"cart_item_id": item.cart_item_id})

        response = self.client.delete(url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CartItem.objects.filter(cart_item_id=item.cart_item_id).exists())

    def test_clear_cart(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=1)
        response = self.client.delete(self.clear_cart_url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CartItem.objects.filter(user=self.customer).count(), 0)

    def test_cart_summary_aggregates_multiple_products(self):
        product2 = Product.objects.create(
            category=self.category,
            name="Mouse",
            brand="Logitech",
            price=Decimal("50.00"),
            stock_quantity=20,
            is_available=True,
        )
        CartItem.objects.create(user=self.customer, product=self.product, quantity=2)   # 2400.00
        CartItem.objects.create(user=self.customer, product=product2, quantity=3)       # 150.00

        response = self.client.get(self.cart_url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["total_items"], 5)
        self.assertEqual(Decimal(response.data["data"]["total_price"]), Decimal("2550.00"))
