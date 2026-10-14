from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import Discount, DiscountType

CENT = Decimal("0.01")


def calculate_discount(product, *, on_date=None):
    """Return the largest active per-unit discount; discounts do not stack."""
    on_date = on_date or timezone.localdate()
    price = Decimal(product.price).quantize(CENT, rounding=ROUND_HALF_UP)
    discounts = Discount.objects.filter(product=product, is_active=True, start_date__lte=on_date, end_date__gte=on_date)
    savings = []
    for discount in discounts:
        amount = (
            price * discount.discount_value / Decimal("100")
            if discount.discount_type == DiscountType.PERCENTAGE
            else discount.discount_value
        )
        savings.append(min(price, amount).quantize(CENT, rounding=ROUND_HALF_UP))
    return max(savings, default=Decimal("0.00"))


def calculate_discounted_price(product, *, on_date=None):
    """Return the unit price after the best applicable discount."""
    price = Decimal(product.price).quantize(CENT, rounding=ROUND_HALF_UP)
    return max(Decimal("0.00"), price - calculate_discount(product, on_date=on_date))
