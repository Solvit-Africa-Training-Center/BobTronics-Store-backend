from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed Amount"


class Discount(models.Model):
    """
    Promotional discounts applied to electronic devices.
    """

    discount_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="discounts",
        db_index=True,
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "discounts"
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["product", "is_active"], name="idx_disc_prod_active"),
            models.Index(fields=["start_date", "end_date"], name="idx_disc_dates"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.get_discount_type_display()} ({self.discount_value})"


class PromoCode(models.Model):
    """Order-level promo code that can be checked against a submitted cart."""

    promo_id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    minimum_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "promo_codes"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["is_active", "start_date", "end_date"], name="idx_promo_active_dates"),
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        if self.end_date < self.start_date:
            errors["end_date"] = "End date must be on or after the start date."
        if (
            self.discount_type == DiscountType.PERCENTAGE
            and self.discount_value > 100
        ):
            errors["discount_value"] = "Percentage discounts cannot exceed 100%."
        if self.usage_limit is not None and self.usage_count > self.usage_limit:
            errors["usage_limit"] = "Usage limit cannot be below the current usage count."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.code
