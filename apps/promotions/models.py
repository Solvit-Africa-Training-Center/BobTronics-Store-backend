from decimal import Decimal
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
