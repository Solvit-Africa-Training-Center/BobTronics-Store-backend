from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    """
    Electronic device category (e.g., Mobile Phones, Laptops, Cameras, Printers, Machines).
    """

    category_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Electronic device product belonging to a Category.
    """

    product_id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        db_index=True,
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    warranty = models.CharField(max_length=150, blank=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "brand"], name="idx_prod_cat_brand"),
            models.Index(fields=["is_available", "price"], name="idx_prod_avail_price"),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand})"


class ProductImage(models.Model):
    """
    Gallery images for electronic devices.
    """

    image_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        db_index=True,
    )
    image_url = models.CharField(max_length=500)
    is_primary = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"Image for {self.product.name} (Primary: {self.is_primary})"


class StockMovementType(models.TextChoices):
    DEDUCTION = "deduction", "Deduction"
    RESTORATION = "restoration", "Restoration"
    ADJUSTMENT = "adjustment", "Adjustment"


class StockMovement(models.Model):
    """Immutable record of a product stock change."""

    movement_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        db_index=True,
    )
    movement_type = models.CharField(max_length=20, choices=StockMovementType.choices)
    source = models.CharField(max_length=50, default="other", db_index=True)
    quantity_change = models.IntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    reference_id = models.CharField(max_length=64, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-created_at", "-movement_id"]
        indexes = [
            models.Index(fields=["product", "created_at"], name="idx_stock_prod_date"),
            models.Index(fields=["source", "created_at"], name="idx_stock_source_date"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity_change=0),
                name="stock_movement_change_nonzero",
            ),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.quantity_change:+d} ({self.source})"
