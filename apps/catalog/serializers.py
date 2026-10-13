from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Product, ProductImage

MAX_IMAGES_PER_PRODUCT = 10
MAX_STOCK_QUANTITY = 1_000_000


def clean_text(value):
    """Trim the ends and collapse repeated inner spaces."""
    return " ".join(value.split())


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "category_id",
            "name",
            "description",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "category_id",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = clean_text(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Category name must be at least 2 characters long."
            )

        duplicates = Category.objects.filter(name__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )
        return value


class ProductImageSerializer(serializers.ModelSerializer):
    """Full serializer. Use for the admin image endpoints (needs `product`)."""

    class Meta:
        model = ProductImage
        fields = [
            "image_id",
            "product",
            "image_url",
            "is_primary",
            "created_at",
        ]
        read_only_fields = [
            "image_id",
            "created_at",
        ]

    def validate_image_url(self, value):
        value = value.strip()
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError(
                "Image URL must start with http:// or https://."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        product = attrs.get("product", getattr(instance, "product", None))
        url = attrs.get("image_url", getattr(instance, "image_url", None))

        siblings = ProductImage.objects.filter(product=product)
        if instance:
            siblings = siblings.exclude(pk=instance.pk)

        if url and siblings.filter(image_url=url).exists():
            raise serializers.ValidationError(
                {"image_url": "This image is already attached to the product."}
            )

        if instance is None and siblings.count() >= MAX_IMAGES_PER_PRODUCT:
            raise serializers.ValidationError(
                {
                    "product": (
                        f"A product can have at most {MAX_IMAGES_PER_PRODUCT} images."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        # The first image of a product is always its primary image.
        if not ProductImage.objects.filter(product=validated_data["product"]).exists():
            validated_data["is_primary"] = True
        return super().create(validated_data)


class ProductImageNestedSerializer(serializers.ModelSerializer):
    """Used inside a product payload, where `product` would be redundant."""

    class Meta:
        model = ProductImage
        fields = ["image_id", "image_url", "is_primary"]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight card for listings: one primary image, no full gallery."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "product_id",
            "category",
            "category_name",
            "name",
            "brand",
            "price",
            "stock_quantity",
            "is_available",
            "primary_image",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_primary_image(self, obj):
        # Uses the prefetched images, so no extra query per product.
        images = list(obj.images.all())
        primary = next((i for i in images if i.is_primary), None) or (
            images[0] if images else None
        )
        return primary.image_url if primary else None


class ProductSerializer(serializers.ModelSerializer):
    """Full product detail, also used for admin create and update."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    images = ProductImageNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "category",
            "category_name",
            "name",
            "description",
            "brand",
            "price",
            "stock_quantity",
            "warranty",
            "is_available",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "product_id",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = clean_text(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Product name must be at least 2 characters long."
            )
        return value

    def validate_brand(self, value):
        value = clean_text(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Brand must be at least 2 characters long."
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_stock_quantity(self, value):
        if value > MAX_STOCK_QUANTITY:
            raise serializers.ValidationError(
                f"Stock quantity cannot exceed {MAX_STOCK_QUANTITY}."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        name = attrs.get("name", getattr(instance, "name", None))
        brand = attrs.get("brand", getattr(instance, "brand", None))
        category = attrs.get("category", getattr(instance, "category", None))

        if name and brand and category:
            duplicates = Product.objects.filter(
                category=category,
                name__iexact=name,
                brand__iexact=brand,
            )
            if instance:
                duplicates = duplicates.exclude(pk=instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {
                        "name": (
                            "A product with this name and brand already "
                            "exists in this category."
                        )
                    }
                )
        return attrs