from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Product, ProductImage

MAX_IMAGES_PER_PRODUCT = 10
MAX_STOCK_QUANTITY = 1_000_000
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024


def clean_text(value):
    """Trim the ends and collapse repeated inner spaces."""
    return " ".join(value.split())


def uploaded_image_url(serializer, image_file):
    if not image_file:
        return None
    url = image_file.url
    request = serializer.context.get("request")
    return request.build_absolute_uri(url) if request else url


def delete_replaced_image(old_file, new_file):
    if old_file and old_file.name and (
        not new_file or old_file.name != new_file.name
    ):
        old_file.storage.delete(old_file.name)


class CategorySerializer(serializers.ModelSerializer):
    image_file = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = [
            "category_id",
            "name",
            "description",
            "image",
            "image_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "category_id",
            "created_at",
            "updated_at",
        ]

    def validate_image_file(self, value):
        if value and value.size > MAX_IMAGE_UPLOAD_BYTES:
            raise serializers.ValidationError("Image files must be 5 MB or smaller.")
        return value

    def validate(self, attrs):
        if attrs.get("image_file") and attrs.get("image"):
            raise serializers.ValidationError(
                {"image": "Provide an image URL or upload a file, not both."}
            )
        return attrs

    def create(self, validated_data):
        if validated_data.get("image_file"):
            validated_data["image"] = ""
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_file = instance.image_file
        old_name = old_file.name if old_file else None

        if validated_data.get("image_file"):
            validated_data["image"] = ""
        elif "image" in validated_data:
            validated_data["image_file"] = None

        instance = super().update(instance, validated_data)
        if old_name:
            delete_replaced_image(old_file, instance.image_file)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image_file:
            data["image"] = uploaded_image_url(self, instance.image_file)
        return data

    def validate_name(self, value):
        value = clean_text(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Use at least 2 characters for the category name."
            )

        duplicates = Category.objects.filter(name__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "This category already exists."
            )
        return value


class ProductImageSerializer(serializers.ModelSerializer):
    """Full serializer. Use for the admin image endpoints (needs `product`)."""

    image_file = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProductImage
        fields = [
            "image_id",
            "product",
            "image_url",
            "image_file",
            "is_primary",
            "created_at",
        ]
        read_only_fields = [
            "image_id",
            "created_at",
        ]

    def validate_image_url(self, value):
        value = value.strip()
        if not value:
            return value
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError(
                "Enter a valid image URL starting with http:// or https://."
            )
        return value

    def validate_image_file(self, value):
        if value and value.size > MAX_IMAGE_UPLOAD_BYTES:
            raise serializers.ValidationError("Image files must be 5 MB or smaller.")
        return value

    def validate(self, attrs):
        instance = self.instance
        product = attrs.get("product", getattr(instance, "product", None))
        url = attrs.get("image_url", getattr(instance, "image_url", None))
        image_file = attrs.get("image_file", getattr(instance, "image_file", None))

        if attrs.get("image_file") and attrs.get("image_url"):
            raise serializers.ValidationError(
                {"image_url": "Provide an image URL or upload a file, not both."}
            )
        if attrs.get("image_file"):
            url = ""
        elif "image_url" in attrs:
            image_file = None

        if not url and not image_file:
            raise serializers.ValidationError(
                {"image_file": "Upload an image file or provide an image URL."}
            )

        siblings = ProductImage.objects.filter(product=product)
        if instance:
            siblings = siblings.exclude(pk=instance.pk)

        if url and siblings.filter(image_url=url).exists():
            raise serializers.ValidationError(
                {"image_url": "This image is already added to the product."}
            )

        if instance is None and siblings.count() >= MAX_IMAGES_PER_PRODUCT:
            raise serializers.ValidationError(
                {
                    "product": (
                        f"A product can have up to {MAX_IMAGES_PER_PRODUCT} images."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        if validated_data.get("image_file"):
            validated_data["image_url"] = ""
        if not ProductImage.objects.filter(product=validated_data["product"]).exists():
            validated_data["is_primary"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_file = instance.image_file
        old_name = old_file.name if old_file else None

        if validated_data.get("image_file"):
            validated_data["image_url"] = ""
        elif "image_url" in validated_data:
            validated_data["image_file"] = None

        instance = super().update(instance, validated_data)
        if old_name:
            delete_replaced_image(old_file, instance.image_file)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image_file:
            data["image_url"] = uploaded_image_url(self, instance.image_file)
        return data

class ProductImageNestedSerializer(serializers.ModelSerializer):
    """Used inside a product payload, where `product` would be redundant."""

    class Meta:
        model = ProductImage
        fields = ["image_id", "image_url", "is_primary"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image_file:
            data["image_url"] = uploaded_image_url(self, instance.image_file)
        return data


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
        if not primary:
            return None
        if primary.image_file:
            return uploaded_image_url(self, primary.image_file)
        return primary.image_url or None


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
                "Use at least 2 characters for the product name."
            )
        return value

    def validate_brand(self, value):
        value = clean_text(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Use at least 2 characters for the brand."
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a price greater than zero.")
        return value

    def validate_stock_quantity(self, value):
        if value > MAX_STOCK_QUANTITY:
            raise serializers.ValidationError(
                f"Stock cannot exceed {MAX_STOCK_QUANTITY} units."
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
                            "This product already exists in this category."
                        )
                    }
                )
        return attrs
