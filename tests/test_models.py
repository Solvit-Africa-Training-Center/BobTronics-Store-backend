from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.accounts.models import User, Role
from apps.catalog.models import Category, Product, ProductImage
from apps.promotions.models import Discount, DiscountType
from apps.reviews.models import Feedback
from apps.cart.models import CartItem
from apps.wishlist.models import Wishlist, WishlistItem
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.payments.models import Payment, PaymentMethod, PaymentStatus
from apps.deliveries.models import Delivery, DeliveryMethod, DeliveryStatus
from apps.services.models import Service, ServiceType, ServiceStatus
from apps.audit.models import AuditLog


class BobTronicsModelsTestCase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="jane@bobtronics.com",
            password="StrongPassword123!",
            first_name="Jane",
            last_name="Doe",
            phone="+250788111222",
            residence="Kigali, Kicukiro",
        )
        self.category = Category.objects.create(
            name="Smartphones",
            description="All smartphones and mobile devices",
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Samsung Galaxy S24 Ultra",
            brand="Samsung",
            description="Snapdragon 8 Gen 3, Titanium Yellow, 512GB",
            price=Decimal("1300.00"),
            stock_quantity=10,
            warranty="1 Year Official Samsung Warranty",
            is_available=True,
        )

    def test_user_creation_and_roles(self):
        self.assertEqual(self.customer.role, Role.CUSTOMER)
        self.assertTrue(self.customer.check_password("StrongPassword123!"))
        self.assertEqual(self.customer.full_name, "Jane Doe")
        self.assertFalse(self.customer.is_staff)

        # Duplicate email should fail
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="jane@bobtronics.com",
                password="AnotherPassword!",
                first_name="Duplicate",
                last_name="User",
            )

    def test_product_and_category_relationship(self):
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.category.products.count(), 1)
        self.assertEqual(self.category.products.first(), self.product)

    def test_cart_item_unique_constraint(self):
        CartItem.objects.create(
            user=self.customer,
            product=self.product,
            quantity=1,
        )
        # Duplicate product in user cart should violate unique constraint
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                user=self.customer,
                product=self.product,
                quantity=2,
            )

    def test_wishlist_unique_constraint(self):
        wishlist = Wishlist.objects.create(user=self.customer)
        WishlistItem.objects.create(
            wishlist=wishlist,
            product=self.product,
        )
        with self.assertRaises(IntegrityError):
            WishlistItem.objects.create(
                wishlist=wishlist,
                product=self.product,
            )

    def test_order_and_items_lifecycle(self):
        order = Order.objects.create(
            user=self.customer,
            status=OrderStatus.PENDING,
            total_amount=Decimal("1300.00"),
            shipping_address="KG 567 St, Kigali",
            phone="+250788111222",
        )
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            discount_amount=Decimal("0.00"),
            subtotal=self.product.price,
        )
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order_item.subtotal, Decimal("1300.00"))

        # Payment
        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method=PaymentMethod.MTN_MOMO,
            transaction_reference="TX-TEST-001",
            status=PaymentStatus.PAID,
            payment_date=timezone.now(),
        )
        self.assertEqual(payment.order, order)

        # Delivery
        delivery = Delivery.objects.create(
            order=order,
            delivery_address=order.shipping_address,
            delivery_method=DeliveryMethod.STANDARD,
            tracking_number="TRK-TEST-999",
            status=DeliveryStatus.PENDING,
            shipping_fee=Decimal("10.00"),
        )
        self.assertEqual(delivery.order, order)

    def test_service_request(self):
        service = Service.objects.create(
            user=self.customer,
            name="Laptop Motherboard Repair",
            description="Diagnose liquid spill damage and repair power IC",
            service_type=ServiceType.HARDWARE_MAINTENANCE,
            status=ServiceStatus.NEW,
            estimated_cost=Decimal("150.00"),
        )
        self.assertEqual(service.status, ServiceStatus.NEW)
        self.assertEqual(self.customer.services.count(), 1)

    def test_audit_log_persists_on_user_deletion(self):
        temp_user = User.objects.create_user(
            email="temp@bobtronics.com",
            password="Password123!",
            first_name="Temp",
            last_name="User",
        )
        log = AuditLog.objects.create(
            user=temp_user,
            action="CREATE_PRODUCT",
            entity_type="Product",
            entity_id=self.product.product_id,
            description="Added Samsung Galaxy S24 Ultra",
        )
        temp_user.delete()
        log.refresh_from_db()
        self.assertIsNone(log.user)  # on_delete=models.SET_NULL preserves audit history
