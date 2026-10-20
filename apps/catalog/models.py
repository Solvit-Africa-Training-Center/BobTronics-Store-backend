from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    """
    Electronic device category (e.g., Mobile Phones, Laptops, Cameras, Printers, Machines).
    """

    category_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=500, blank=True)
    image_file = models.ImageField(
        upload_to="category-images/%Y/%m/",
        blank=True,
        null=True,
    )
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
    image_url = models.CharField(max_length=500, blank=True)
    image_file = models.ImageField(
        upload_to="product-images/%Y/%m/",
        blank=True,
        null=True,
    )
    is_primary = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"Image for {self.product.name} (Primary: {self.is_primary})"
