"""
Stock service.

This is the only place that should change Product.stock_quantity for
orders and inventory adjustments. Other apps (orders, cart) call these
functions instead of touching the field directly.

Items are always a list of (product_id, quantity) pairs, for example:

    deduct_stock([(5, 2), (9, 1)])

Every function that changes stock is all-or-nothing: if one line fails,
no line is changed.
"""

from collections import defaultdict

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Product


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StockError(Exception):
    """Base class for every stock problem."""


class InvalidQuantityError(StockError):
    """A quantity was not a positive whole number, or no items were given."""


class ProductNotFoundError(StockError):
    def __init__(self, product_ids):
        self.product_ids = sorted(product_ids)
        super().__init__("One or more products could not be found.")


class ProductUnavailableError(StockError):
    def __init__(self, product_id, name):
        self.product_id = product_id
        self.name = name
        super().__init__(f"{name} is unavailable.")


class InsufficientStockError(StockError):
    def __init__(self, product_id, name, requested, available):
        self.product_id = product_id
        self.name = name
        self.requested = requested
        self.available = available
        super().__init__(
            f"Only {available} left for {name}; {requested} requested."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_items(items):
    """Validate quantities and merge repeated products into one line each."""
    wanted = defaultdict(int)
    for product_id, quantity in items:
        is_whole_number = isinstance(quantity, int) and not isinstance(quantity, bool)
        if not is_whole_number or quantity <= 0:
            raise InvalidQuantityError(
                "Quantity must be a positive whole number."
            )
        wanted[product_id] += quantity

    if not wanted:
        raise InvalidQuantityError("No items were provided.")
    return dict(wanted)


def _load_products(product_ids, *, lock):
    """
    Fetch products by id. With lock=True the rows are locked until the
    surrounding transaction ends (PostgreSQL and MySQL). Rows are always
    read in primary-key order so two orders can't deadlock each other.
    """
    queryset = Product.objects.filter(pk__in=list(product_ids)).order_by("pk")
    if lock:
        queryset = queryset.select_for_update()

    products = {product.pk: product for product in queryset}
    missing = set(product_ids) - set(products)
    if missing:
        raise ProductNotFoundError(missing)
    return products


def _validate(products, wanted, require_available):
    for product_id in sorted(wanted):
        product = products[product_id]
        quantity = wanted[product_id]

        if require_available and not product.is_available:
            raise ProductUnavailableError(product.pk, product.name)

        if product.stock_quantity < quantity:
            raise InsufficientStockError(
                product.pk, product.name, quantity, product.stock_quantity
            )


def _current_levels(product_ids):
    return dict(
        Product.objects.filter(pk__in=list(product_ids)).values_list(
            "pk", "stock_quantity"
        )
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_stock(items, *, require_available=True):
    """
    Raise a StockError if the items could not be supplied right now.
    Changes nothing, so it is safe for carts and checkout pages. Remember
    the answer can be out of date a moment later: use deduct_stock to
    actually reserve the units.
    """
    wanted = _merge_items(items)
    products = _load_products(wanted, lock=False)
    _validate(products, wanted, require_available)


@transaction.atomic
def deduct_stock(items, *, require_available=True):
    """
    Reduce stock for every item. Returns {product_id: stock_left}.

    Raises (and changes nothing) if a product is missing, unavailable
    (unless require_available=False) or has too little stock.
    """
    wanted = _merge_items(items)
    products = _load_products(wanted, lock=True)
    _validate(products, wanted, require_available)

    now = timezone.now()
    for product_id in sorted(wanted):
        quantity = wanted[product_id]

        # The stock_quantity__gte condition makes the check and the update one
        # step, so two buyers can never both take the last unit, even on a
        # database that ignores row locks (such as SQLite).
        updated = Product.objects.filter(
            pk=product_id, stock_quantity__gte=quantity
        ).update(stock_quantity=F("stock_quantity") - quantity, updated_at=now)

        if updated != 1:
            available = (
                Product.objects.filter(pk=product_id)
                .values_list("stock_quantity", flat=True)
                .first()
                or 0
            )
            raise InsufficientStockError(
                product_id, products[product_id].name, quantity, available
            )

    return _current_levels(wanted)


@transaction.atomic
def restore_stock(items):
    """
    Add units back to stock (cancelled or refunded orders, restocking).
    Returns {product_id: stock_now}.
    """
    wanted = _merge_items(items)
    _load_products(wanted, lock=True)  # checks the products exist and locks them

    now = timezone.now()
    for product_id in sorted(wanted):
        Product.objects.filter(pk=product_id).update(
            stock_quantity=F("stock_quantity") + wanted[product_id],
            updated_at=now,
        )

    return _current_levels(wanted)
