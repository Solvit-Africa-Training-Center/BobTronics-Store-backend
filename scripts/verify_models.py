import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from django.utils import timezone
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()



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


def _run_verification():
    print("=== STARTING BOB TRONICS MODEL VERIFICATION ===")
    run_id = uuid4().hex

    # 1. Accounts: User
    customer = User.objects.create_user(

        email=f"customer-{run_id}@verification.invalid",
        password="SecurePassword123!",
        first_name="Pacifique",
        last_name="Ishimwe",
        phone="+250788000111",
        residence="Kigali, Gasabo",
        role=Role.CUSTOMER,
    )
    print(f"[PASS] Created Customer: {customer} (Role: {customer.role})")

    admin = User.objects.create_superuser(
        email=f"admin-{run_id}@verification.invalid",
        password="AdminSuperPassword123!",
        first_name="Bob",
        last_name="Admin",
    )
    print(f"[PASS] Created Super Admin: {admin} (Role: {admin.role}, Staff: {admin.is_staff})")

    # 2. Catalog: Category & Products (Devices: Phones, Laptops, Machines, etc.)
    phones_cat = Category.objects.create(
        name=f"Mobile Phones {run_id}",
        description="Smartphones from Apple, Samsung, Google Pixel, and Sony",
    )
    laptops_cat = Category.objects.create(
        name=f"Laptops {run_id}",
        description="High-performance laptops from HP, Dell, MacBook, Lenovo, and Acer",
    )
    machines_cat = Category.objects.create(
        name=f"Electronic Machines & Printers {run_id}",
        description="Printers, 3D printers, and office automation hardware",
    )
    print(f"[PASS] Created Categories: {phones_cat}, {laptops_cat}, {machines_cat}")

    # Electronic devices
    phone_prod = Product.objects.create(
        category=phones_cat,
        name="iPhone 15 Pro Max 256GB",
        brand="Apple",
        description="A17 Pro chip, titanium design, 48MP camera",
        price=Decimal("1450.00"),
        stock_quantity=15,
        warranty="1 Year Official Apple Warranty",
        is_available=True,
    )
    laptop_prod = Product.objects.create(
        category=laptops_cat,
        name="HP Spectre x360 14",
        brand="HP",
        description="Intel Core Ultra 7, 16GB RAM, 1TB SSD OLED 2-in-1",
        price=Decimal("1299.99"),
        stock_quantity=8,
        warranty="2 Years Manufacturer Warranty",
        is_available=True,
    )
    print(f"[PASS] Created Products: {phone_prod}, {laptop_prod}")

    # Product Images
    img1 = ProductImage.objects.create(
        product=phone_prod,
        is_primary=True,
    )
    img2 = ProductImage.objects.create(
        product=phone_prod,
        is_primary=False,
    )
    print(f"[PASS] Added Product Images for {phone_prod.name}: Primary={img1.is_primary}, Gallery={img2.is_primary}")

    # 3. Promotions: Discount
    discount = Discount.objects.create(
        product=laptop_prod,
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("10.00"),
        start_date=date.today(),
        end_date=date.today() + timedelta(days=14),
        is_active=True,
    )
    print(f"[PASS] Created Discount: {discount}")

    # 4. Reviews: Feedback
    feedback = Feedback.objects.create(
        user=customer,
        product=phone_prod,
        rating=5,
        comment="Incredible build quality and fast battery life. Recommended!",
    )
    print(f"[PASS] Created Customer Feedback: {feedback}")

    # 5. Cart: CartItem
    cart_item = CartItem.objects.create(
        user=customer,
        product=laptop_prod,
        quantity=1,
    )
    print(f"[PASS] Added to Cart: {cart_item} (Subtotal: ${cart_item.subtotal})")

    # 6. Wishlist: Wishlist & WishlistItem
    wishlist = Wishlist.objects.create(user=customer)
    wishlist_item = WishlistItem.objects.create(
        wishlist=wishlist,
        product=phone_prod,
    )
    print(f"[PASS] Added to Wishlist: {wishlist_item}")

    # 7. Orders: Order & OrderItem
    order = Order.objects.create(
        user=customer,
        status=OrderStatus.PENDING,
        total_amount=Decimal("1299.99"),
        shipping_address="KG 125 St, Nyarutarama, Kigali",
        phone="+250788000111",
    )
    order_item = OrderItem.objects.create(
        order=order,
        product=laptop_prod,
        quantity=1,
        unit_price=laptop_prod.price,
        discount_amount=Decimal("0.00"),
        subtotal=laptop_prod.price,
    )
    print(f"[PASS] Created Order: {order} with item {order_item}")

    # 8. Payments: Payment
    payment = Payment.objects.create(
        order=order,
        amount=order.total_amount,
        payment_method=PaymentMethod.MTN_MOMO,
        transaction_reference=f"VERIFY-MOMO-{run_id}",
        status=PaymentStatus.PAID,
        payment_date=timezone.now(),
    )
    order.status = OrderStatus.CONFIRMED
    order.save()
    print(f"[PASS] Processed Payment: {payment}")

    # 9. Deliveries: Delivery
    delivery = Delivery.objects.create(
        order=order,
        delivery_address=order.shipping_address,
        delivery_method=DeliveryMethod.EXPRESS,
        tracking_number=f"VERIFY-DELIVERY-{run_id}",
        status=DeliveryStatus.IN_TRANSIT,
        shipping_fee=Decimal("15.00"),
        shipped_at=timezone.now(),
    )
    print(f"[PASS] Created Delivery: {delivery} (Tracking: {delivery.tracking_number})")

    # 10. Services: Service (Consultancy)
    service_req = Service.objects.create(
        user=customer,
        name="Enterprise Office Network Installation",
        description="Deploy secure Wi-Fi 6 mesh network and rack-mounted firewall for office of 30 staff.",
        service_type=ServiceType.NETWORK_INFRASTRUCTURE,
        status=ServiceStatus.IN_PROGRESS,
        estimated_cost=Decimal("2500.00"),
    )
    print(f"[PASS] Created Service Request: {service_req}")

    # 11. Audit: AuditLog
    audit_entry = AuditLog.objects.create(
        user=admin,
        action="UPDATE_ORDER_STATUS",
        entity_type="Order",
        entity_id=order.order_id,
        description=f"Status advanced to {order.status} after payment verification",
        ip_address="192.168.1.50",
    )
    print(f"[PASS] Logged Audit Event: {audit_entry}")

    print("\n=== ALL 15 ENTITIES VERIFIED SUCCESSFULLY IN DATABASE ===")



def run_verification():
    """Run model checks without leaving temporary rows in the configured DB."""
    class RollbackVerification(Exception):
        pass

    try:
        with transaction.atomic():
            _run_verification()
            raise RollbackVerification
    except RollbackVerification:
        print("Verification complete; temporary database records were rolled back.")


if __name__ == "__main__":
    run_verification()
