from django.db import transaction
from django.urls import reverse
from rest_framework import status

from .stock_service import (
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    ProductUnavailableError,
    check_stock,
    deduct_stock,
    low_stock_products,
    restore_stock,
)
from .models import StockMovement, StockMovementType
from .tests import CatalogTestBase


class StockServiceTests(CatalogTestBase):
    """
    From CatalogTestBase: phone has 10 in stock, laptop has 0,
    hidden (unavailable) has 5.
    """

    def stock_of(self, product):
        product.refresh_from_db()
        return product.stock_quantity

    # ---- deduct ----

    def test_deduct_reduces_stock(self):
        levels = deduct_stock([(self.phone.pk, 3)])
        self.assertEqual(self.stock_of(self.phone), 7)
        self.assertEqual(levels, {self.phone.pk: 7})

    def test_deduct_records_signed_change_and_context(self):
        deduct_stock(
            [(self.phone.pk, 3)],
            source="checkout",
            reason="Stock reserved during checkout",
            actor=self.customer,
        )
        movement = StockMovement.objects.get(product=self.phone)
        self.assertEqual(movement.movement_type, StockMovementType.DEDUCTION)
        self.assertEqual(movement.quantity_change, -3)
        self.assertEqual(movement.quantity_before, 10)
        self.assertEqual(movement.quantity_after, 7)
        self.assertEqual(movement.source, "checkout")
        self.assertEqual(movement.actor, self.customer)

    def test_deduct_merges_repeated_lines(self):
        deduct_stock([(self.phone.pk, 2), (self.phone.pk, 3)])
        self.assertEqual(self.stock_of(self.phone), 5)

    def test_deduct_can_take_the_last_units(self):
        deduct_stock([(self.phone.pk, 10)])
        self.assertEqual(self.stock_of(self.phone), 0)

    def test_deduct_more_than_available_fails_and_changes_nothing(self):
        with self.assertRaises(InsufficientStockError) as ctx:
            deduct_stock([(self.phone.pk, 11)])
        self.assertEqual(ctx.exception.available, 10)
        self.assertEqual(ctx.exception.requested, 11)
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_deduct_is_all_or_nothing(self):
        # first line is fine, second line is not
        with self.assertRaises(InsufficientStockError):
            deduct_stock([(self.phone.pk, 2), (self.laptop.pk, 1)])
        self.assertEqual(self.stock_of(self.phone), 10)
        self.assertFalse(StockMovement.objects.exists())

    def test_movement_and_stock_roll_back_with_outer_transaction(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                deduct_stock([(self.phone.pk, 2)], source="checkout")
                raise RuntimeError("roll back the order")
        self.assertEqual(self.stock_of(self.phone), 10)
        self.assertFalse(StockMovement.objects.exists())

    def test_deduct_unavailable_product_fails(self):
        with self.assertRaises(ProductUnavailableError):
            deduct_stock([(self.hidden.pk, 1)])
        self.assertEqual(self.stock_of(self.hidden), 5)

    def test_deduct_unavailable_allowed_when_not_required(self):
        deduct_stock([(self.hidden.pk, 2)], require_available=False)
        self.assertEqual(self.stock_of(self.hidden), 3)

    def test_deduct_unknown_product_fails(self):
        with self.assertRaises(ProductNotFoundError):
            deduct_stock([(999999, 1)])

    def test_invalid_quantities_are_rejected(self):
        for bad in (0, -3, 2.5, "2", True):
            with self.assertRaises(InvalidQuantityError, msg=repr(bad)):
                deduct_stock([(self.phone.pk, bad)])
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_empty_item_list_is_rejected(self):
        with self.assertRaises(InvalidQuantityError):
            deduct_stock([])

    def test_deduct_updates_the_updated_at_timestamp(self):
        before = self.phone.updated_at
        deduct_stock([(self.phone.pk, 1)])
        self.phone.refresh_from_db()
        self.assertGreater(self.phone.updated_at, before)

    # ---- restore ----

    def test_restore_adds_stock_back(self):
        deduct_stock([(self.phone.pk, 4)])
        levels = restore_stock([(self.phone.pk, 4)])
        self.assertEqual(self.stock_of(self.phone), 10)
        self.assertEqual(levels, {self.phone.pk: 10})

    def test_restore_records_reference_and_before_after_levels(self):
        restore_stock(
            [(self.phone.pk, 2)],
            source="order_cancellation",
            reason="Cancelled order",
            actor=self.customer,
            reference_id=123,
        )
        movement = StockMovement.objects.get(product=self.phone)
        self.assertEqual(movement.movement_type, StockMovementType.RESTORATION)
        self.assertEqual(movement.quantity_change, 2)
        self.assertEqual(movement.quantity_before, 10)
        self.assertEqual(movement.quantity_after, 12)
        self.assertEqual(movement.reference_id, "123")

    def test_restore_works_on_unavailable_products(self):
        restore_stock([(self.hidden.pk, 5)])
        self.assertEqual(self.stock_of(self.hidden), 10)

    def test_restore_unknown_product_fails(self):
        with self.assertRaises(ProductNotFoundError):
            restore_stock([(999999, 1)])

    def test_restore_rejects_bad_quantity(self):
        with self.assertRaises(InvalidQuantityError):
            restore_stock([(self.phone.pk, 0)])

    # ---- check ----

    def test_check_stock_passes_without_changing_anything(self):
        check_stock([(self.phone.pk, 10)])
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_check_stock_fails_when_short(self):
        with self.assertRaises(InsufficientStockError):
            check_stock([(self.phone.pk, 11)])

    def test_check_stock_fails_for_unavailable(self):
        with self.assertRaises(ProductUnavailableError):
            check_stock([(self.hidden.pk, 1)])

    def test_low_stock_products_includes_products_at_threshold_and_hidden_products(self):
        products = list(low_stock_products(5))
        self.assertEqual(products, [self.laptop, self.hidden])

    def test_low_stock_products_zero_threshold_returns_out_of_stock_only(self):
        self.assertEqual(list(low_stock_products(0)), [self.laptop])

    def test_low_stock_products_rejects_invalid_thresholds(self):
        for threshold in (-1, True, 1.5, "1"):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    low_stock_products(threshold)


class LowStockApiTests(CatalogTestBase):
    def url(self):
        return reverse("admin-product-low-stock")

    def test_admin_can_list_products_at_or_below_threshold(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url(), {"threshold": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, ["ThinkBook 14", "Old Phone"])

    def test_threshold_is_required(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_or_non_integer_threshold_is_rejected(self):
        self.client.force_authenticate(self.admin)
        for threshold in ("-1", "abc", "1.5"):
            with self.subTest(threshold=threshold):
                response = self.client.get(self.url(), {"threshold": threshold})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url(), {"threshold": 5})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_is_rejected(self):
        response = self.client.get(self.url(), {"threshold": 5})
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class StockAdjustmentApiTests(CatalogTestBase):
    def url(self, product):
        return reverse("admin-product-adjust-stock", args=[product.pk])

    def stock_of(self, product):
        product.refresh_from_db()
        return product.stock_quantity

    def test_admin_can_add_stock(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url(self.phone), {"delta": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["stock_quantity"], 15)
        self.assertEqual(self.stock_of(self.phone), 15)
        movement = StockMovement.objects.get(product=self.phone)
        self.assertEqual(movement.movement_type, StockMovementType.ADJUSTMENT)
        self.assertEqual(movement.quantity_change, 5)
        self.assertEqual(movement.source, "inventory_adjustment")
        self.assertEqual(movement.actor, self.admin)

    def test_admin_can_remove_stock(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url(self.phone),
            {"delta": -4, "reason": "Damaged in storage"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.stock_of(self.phone), 6)
        movement = StockMovement.objects.get(product=self.phone)
        self.assertEqual(movement.quantity_change, -4)
        self.assertEqual(movement.reason, "Damaged in storage")
        self.assertEqual(movement.movement_type, StockMovementType.ADJUSTMENT)

    def test_removing_more_than_available_is_a_conflict(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url(self.phone), {"delta": -11}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_hidden_product_stock_can_be_written_off(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url(self.hidden), {"delta": -2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.stock_of(self.hidden), 3)

    def test_zero_delta_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url(self.phone), {"delta": 0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_delta_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url(self.phone), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_absurd_delta_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url(self.phone), {"delta": 5_000_000}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_restock_that_would_pass_the_limit_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url(self.phone), {"delta": 999_995}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_unknown_product_is_404(self):
        self.client.force_authenticate(self.admin)
        url = reverse("admin-product-adjust-stock", args=[999999])
        response = self.client.post(url, {"delta": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url(self.phone), {"delta": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.stock_of(self.phone), 10)

    def test_anonymous_is_rejected(self):
        response = self.client.post(self.url(self.phone), {"delta": 5}, format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertEqual(self.stock_of(self.phone), 10)
