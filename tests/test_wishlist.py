from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.cart.models import CartItem
from apps.catalog.models import Category, Product
from apps.wishlist.models import Wishlist, WishlistItem


def make_user(email="wishlist_user@bobtronics.com", role=Role.CUSTOMER):
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


class WishlistAPITestCase(APITestCase):
    def setUp(self):
        self.customer = make_user("wish_customer@bobtronics.com")
        self.auth = get_auth_header(self.customer)

        self.category = Category.objects.create(name="Smartphones")
        self.product_in_stock = Product.objects.create(
            category=self.category,
            name="Galaxy S24",
            brand="Samsung",
            price=Decimal("900.00"),
            stock_quantity=5,
            is_available=True,
        )
        self.product_out_of_stock = Product.objects.create(
            category=self.category,
            name="iPhone 16 Pro",
            brand="Apple",
            price=Decimal("1200.00"),
            stock_quantity=0,
            is_available=True,
        )

        self.wishlist_url = reverse("wishlist:wishlist-detail")
        self.add_url = reverse("wishlist:wishlist-add-item")

    def test_unauthenticated_wishlist_access_is_rejected(self):
        response = self.client.get(self.wishlist_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_product_to_wishlist(self):
        payload = {"product_id": self.product_out_of_stock.product_id}
        response = self.client.post(self.add_url, payload, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["data"]["product"]["product_id"],
            self.product_out_of_stock.product_id,
        )
        self.assertFalse(response.data["data"]["product"]["is_in_stock"])

    def test_adding_duplicate_product_to_wishlist_is_rejected(self):
        payload = {"product_id": self.product_in_stock.product_id}
        self.client.post(self.add_url, payload, format="json", **self.auth)

        response = self.client.post(self.add_url, payload, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_wishlist(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.customer)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_in_stock)

        response = self.client.get(self.wishlist_url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["total_saved"], 1)

    def test_remove_product_from_wishlist(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.customer)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_in_stock)

        url = reverse("wishlist:wishlist-remove-item", kwargs={"product_id": self.product_in_stock.product_id})
        response = self.client.delete(url, **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(WishlistItem.objects.filter(wishlist=wishlist, product=self.product_in_stock).exists())

    def test_move_in_stock_item_from_wishlist_to_cart(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.customer)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_in_stock)

        url = reverse("wishlist:wishlist-move-to-cart", kwargs={"product_id": self.product_in_stock.product_id})
        response = self.client.post(url, {"quantity": 2}, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be removed from wishlist
        self.assertFalse(WishlistItem.objects.filter(wishlist=wishlist, product=self.product_in_stock).exists())
        # Should be added to cart
        cart_item = CartItem.objects.get(user=self.customer, product=self.product_in_stock)
        self.assertEqual(cart_item.quantity, 2)

    def test_move_out_of_stock_item_to_cart_is_rejected(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.customer)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_out_of_stock)

        url = reverse("wishlist:wishlist-move-to-cart", kwargs={"product_id": self.product_out_of_stock.product_id})
        response = self.client.post(url, {"quantity": 1}, format="json", **self.auth)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Item remains in wishlist
        self.assertTrue(WishlistItem.objects.filter(wishlist=wishlist, product=self.product_out_of_stock).exists())
