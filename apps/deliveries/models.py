from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class DeliveryMethod(models.TextChoices):
    STANDARD = "standard", "Standard Delivery"
    EXPRESS = "express", "Express Delivery"
    STORE_PICKUP = "store_pickup", "Store Pick-up"


class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_TRANSIT = "in_transit", "In Transit"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    RETURNED = "returned", "Returned"


class Delivery(models.Model):
    """
    Fulfillment and shipment tracking for an Order.
    """

    delivery_id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="delivery",
        db_index=True,
    )
    delivery_address = models.TextField()
    delivery_method = models.CharField(
        max_length=50,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.STANDARD,
    )
    tracking_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deliveries"
        verbose_name = "Delivery"
        verbose_name_plural = "Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "delivery_method"], name="idx_deliv_status_method"),
        ]

    def __str__(self):
        return f"Delivery for Order #{self.order_id} ({self.get_status_display()})"
