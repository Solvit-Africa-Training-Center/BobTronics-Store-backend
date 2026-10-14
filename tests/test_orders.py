from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.cart.models import CartItem
from apps.catalog.models import Category, Product, StockMovement
from apps.orders.models import Order, OrderItem, OrderStatus


def make_user(email="order_customer@bobtronics.com", role=Role.CUSTOMER, residence="Kigali, Rwanda", phone="+250788000001"):
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": "Test",
            "last_name": "User",
            "role": role,
            "residence": residence,
            "phone": phone,
            "is_active": True,
        },
    )
    user.set_password("Password123!")
    user.save()
    return user


def get_auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class OrderAPITestCase(APITestCase):
    def setUp(self):
        self.customer = make_user("customer1@bobtronics.com")
        self.other_customer = make_user("customer2@bobtronics.com")
        self.admin = make_user("admin_orders@bobtronics.com", role=Role.ADMIN)

        self.customer_auth = get_auth_header(self.customer)
        self.other_auth = get_auth_header(self.other_customer)
        self.admin_auth = get_auth_header(self.admin)

        self.category = Category.objects.create(name="Audio")
        self.headphone = Product.objects.create(
            category=self.category,
            name="Sony WH-1000XM5",
            brand="Sony",
            price=Decimal("400.00"),
            stock_quantity=10,
            is_available=True,
        )
        self.earbuds = Product.objects.create(
            category=self.category,
            name="AirPods Pro",
            brand="Apple",
            price=Decimal("250.00"),
            stock_quantity=5,
            is_available=True,
        )

        self.checkout_url = reverse("orders:order-checkout")
        self.order_list_url = reverse("orders:order-list")
        self.admin_order_list_url = reverse("orders:admin-order-list")

    def test_checkout_with_empty_cart_fails(self):
        response = self.client.post(
            self.checkout_url,
            {"shipping_address": "Remera, Kigali", "phone": "+250788111222"},
            format="json",
            **self.customer_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_success_deducts_stock_and_clears_cart(self):
        # 1. Add items to cart: 2 Headphones, 1 Earbuds
        CartItem.objects.create(user=self.customer, product=self.headphone, quantity=2)
        CartItem.objects.create(user=self.customer, product=self.earbuds, quantity=1)

        initial_headphone_stock = self.headphone.stock_quantity  # 10
        initial_earbuds_stock = self.earbuds.stock_quantity      # 5

        payload = {
            "shipping_address": "Kacyiru, Kigali",
            "phone": "+250788333444",
        }
        response = self.client.post(self.checkout_url, payload, format="json", **self.customer_auth)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(response.data["data"]["total_amount"])), Decimal("1050.00"))  # (2*400) + (1*250)
        self.assertEqual(response.data["data"]["status"], OrderStatus.PENDING)

        # 2. Check stock was atomically decremented in database
        self.headphone.refresh_from_db()
        self.earbuds.refresh_from_db()
        self.assertEqual(self.headphone.stock_quantity, initial_headphone_stock - 2)
        self.assertEqual(self.earbuds.stock_quantity, initial_earbuds_stock - 1)

        # 3. Check Cart was cleared
        self.assertEqual(CartItem.objects.filter(user=self.customer).count(), 0)

        # 4. Check Order Items
        order_id = response.data["data"]["order_id"]
        order = Order.objects.get(order_id=order_id)
        self.assertEqual(order.items.count(), 2)
        movements = StockMovement.objects.filter(source="checkout", actor=self.customer)
        self.assertEqual(movements.count(), 2)
        self.assertSetEqual(
            set(movements.values_list("reference_id", flat=True)),
            {str(order_id)},
        )
        self.assertSetEqual(
            set(movements.values_list("quantity_change", flat=True)),
            {-2, -1},
        )

    def test_checkout_uses_default_profile_address_when_omitted(self):
        CartItem.objects.create(user=self.customer, product=self.headphone, quantity=1)

        response = self.client.post(self.checkout_url, {}, format="json", **self.customer_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["shipping_address"], self.customer.residence)
        self.assertEqual(response.data["data"]["phone"], self.customer.phone)

    def test_checkout_fails_atomically_when_stock_is_insufficient(self):
        # Request 15 headphones when only 10 available
        CartItem.objects.create(user=self.customer, product=self.headphone, quantity=15)

        response = self.client.post(self.checkout_url, {}, format="json", **self.customer_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify stock was NOT touched (atomic rollback)
        self.headphone.refresh_from_db()
        self.assertEqual(self.headphone.stock_quantity, 10)

        # Verify no order was created
        self.assertEqual(Order.objects.filter(user=self.customer).count(), 0)

        # Verify cart items remain untouched
        self.assertEqual(CartItem.objects.filter(user=self.customer).count(), 1)

    def test_order_list_and_detail(self):
        order = Order.objects.create(
            user=self.customer,
            shipping_address="Gikondo, Kigali",
            phone="+250788555666",
            total_amount=Decimal("400.00"),
            status=OrderStatus.PENDING,
        )
        OrderItem.objects.create(
            order=order,
            product=self.headphone,
            quantity=1,
            unit_price=Decimal("400.00"),
            discount_amount=Decimal("0.00"),
            subtotal=Decimal("400.00"),
        )

        # List
        list_response = self.client.get(self.order_list_url, **self.customer_auth)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

        # Detail
        detail_url = reverse("orders:order-detail", kwargs={"order_id": order.order_id})
        detail_response = self.client.get(detail_url, **self.customer_auth)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["data"]["order_id"], order.order_id)
        self.assertEqual(len(detail_response.data["data"]["items"]), 1)

    def test_customer_cannot_view_other_customers_order(self):
        order = Order.objects.create(
            user=self.customer,
            shipping_address="Kigali",
            phone="+250788555666",
            total_amount=Decimal("400.00"),
        )
        detail_url = reverse("orders:order-detail", kwargs={"order_id": order.order_id})

        response = self.client.get(detail_url, **self.other_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_order_restores_stock(self):
        # Initially 10 in stock
        order = Order.objects.create(
            user=self.customer,
            shipping_address="Kigali",
            phone="+250788555666",
            total_amount=Decimal("800.00"),
            status=OrderStatus.PENDING,
        )
        OrderItem.objects.create(
            order=order,
            product=self.headphone,
            quantity=3,
            unit_price=Decimal("400.00"),
            subtotal=Decimal("1200.00"),
        )

        cancel_url = reverse("orders:order-cancel", kwargs={"order_id": order.order_id})
        response = self.client.post(cancel_url, **self.customer_auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

        # Stock restored: 10 + 3 = 13
        self.headphone.refresh_from_db()
        self.assertEqual(self.headphone.stock_quantity, 13)

        # The restoration is traceable to the cancelled order.
        movement = StockMovement.objects.get(
            product=self.headphone,
            source="order_cancellation",
            reference_id=str(order.order_id),
        )
        self.assertEqual(movement.quantity_change, 3)
        self.assertEqual(movement.actor, self.customer)

    def test_cannot_cancel_shipped_order(self):
        order = Order.objects.create(
            user=self.customer,
            shipping_address="Kigali",
            phone="+250788555666",
            total_amount=Decimal("400.00"),
            status=OrderStatus.SHIPPED,
        )
        cancel_url = reverse("orders:order-cancel", kwargs={"order_id": order.order_id})
        response = self.client.post(cancel_url, **self.customer_auth)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_order_list_and_status_update(self):
        order = Order.objects.create(
            user=self.customer,
            shipping_address="Kigali",
            phone="+250788555666",
            total_amount=Decimal("400.00"),
            status=OrderStatus.PENDING,
        )

        # Admin lists all orders
        response = self.client.get(self.admin_order_list_url, **self.admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

        # Regular customer cannot access admin order list
        customer_response = self.client.get(self.admin_order_list_url, **self.customer_auth)
        self.assertEqual(customer_response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin updates status to PROCESSING
        status_url = reverse("orders:admin-order-status-update", kwargs={"order_id": order.order_id})
        update_response = self.client.patch(
            status_url,
            {"status": OrderStatus.PROCESSING},
            format="json",
            **self.admin_auth,
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PROCESSING)
