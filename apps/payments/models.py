from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "mtn_momo", "MTN Mobile Money"
    AIRTEL_MONEY = "airtel_money", "Airtel Money"
    CARD = "card", "Credit/Debit Card"
    CASH_ON_DELIVERY = "cash_on_delivery", "Cash on Delivery"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    """
    Payment transaction record associated with an Order.
    """

    payment_id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment",
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
    )
    transaction_reference = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "payment_method"], name="idx_pay_status_method"),
        ]

    def __str__(self):
        return f"Payment #{self.payment_id} - Ref: {self.transaction_reference} ({self.get_status_display()})"
