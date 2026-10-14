import secrets
from decimal import Decimal
from django.utils import timezone
from .models import Delivery, DeliveryMethod, DeliveryStatus

# Shipping fee rates (default values)
DEFAULT_SHIPPING_FEES = {
    DeliveryMethod.STORE_PICKUP: Decimal("0.00"),
    DeliveryMethod.STANDARD: Decimal("1500.00"),
    DeliveryMethod.EXPRESS: Decimal("4000.00"),
}


def calculate_shipping_fee(delivery_method: str) -> Decimal:
    """Calculate the shipping fee for a chosen delivery method."""
    return DEFAULT_SHIPPING_FEES.get(delivery_method, Decimal("1500.00"))


def generate_tracking_number() -> str:
    """Generate a collision-free, human-readable tracking number: BT-DEL-YYYYMM-XXXXXX."""
    date_part = timezone.now().strftime("%Y%m")
    random_part = secrets.token_hex(3).upper()
    return f"BT-DEL-{date_part}-{random_part}"


def create_delivery_for_order(
    order,
    delivery_address: str = "",
    delivery_method: str = DeliveryMethod.STANDARD,
    shipping_fee: Decimal = None,
) -> Delivery:
    """
    Initialize a delivery record for a newly placed order.
    """
    if hasattr(order, "delivery"):
        return order.delivery

    address = delivery_address.strip() if delivery_address else order.shipping_address
    fee = shipping_fee if shipping_fee is not None else calculate_shipping_fee(delivery_method)
    tracking_number = generate_tracking_number()

    while Delivery.objects.filter(tracking_number=tracking_number).exists():
        tracking_number = generate_tracking_number()

    return Delivery.objects.create(
        order=order,
        delivery_address=address,
        delivery_method=delivery_method,
        tracking_number=tracking_number,
        status=DeliveryStatus.PENDING,
        shipping_fee=fee,
    )
