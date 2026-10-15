from decimal import Decimal
from rest_framework import serializers

from apps.catalog.models import Product
from .models import Discount, DiscountType
from .services import calculate_discount, calculate_discounted_price


class DiscountSerializer(serializers.ModelSerializer):
    """Full serializer for administrative discount management."""

    class Meta:
        model = Discount
        fields = [
            "discount_id",
            "product",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["discount_id", "created_at", "updated_at"]

    def validate(self, attrs):
        discount_type = attrs.get(
            "discount_type", getattr(self.instance, "discount_type", DiscountType.PERCENTAGE)
        )
        value = attrs.get("discount_value", getattr(self.instance, "discount_value", None))
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        errors = {}
        if value is not None and value <= 0:
            errors["discount_value"] = "Discount value must be greater than zero."
        if discount_type == DiscountType.PERCENTAGE and value is not None and value > 100:
            errors["discount_value"] = "Percentage discount cannot exceed 100."
        if start and end and end < start:
            errors["end_date"] = "End date must be on or after the start date."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ActivePromotionProductSerializer(serializers.ModelSerializer):
    """Summary of the product under promotion for public listings."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "brand",
            "price",
            "category_name",
            "is_available",
            "primary_image",
        ]

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        primary = next((i for i in images if i.is_primary), None) or (
            images[0] if images else None
        )
        return primary.image_url if primary else None


class ActivePromotionSerializer(serializers.ModelSerializer):
    """Public representation of an active promotional deal."""

    product = ActivePromotionProductSerializer(read_only=True)
    discount_type_display = serializers.CharField(
        source="get_discount_type_display", read_only=True
    )
    savings_amount = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = [
            "discount_id",
            "product",
            "discount_type",
            "discount_type_display",
            "discount_value",
            "savings_amount",
            "discounted_price",
            "start_date",
            "end_date",
            "is_active",
        ]

    def get_savings_amount(self, obj) -> str:
        return str(calculate_discount(obj.product))

    def get_discounted_price(self, obj) -> str:
        return str(calculate_discounted_price(obj.product))


class ProductDiscountDetailSerializer(serializers.Serializer):
    """Detailed discount verification for a specific product."""

    has_discount = serializers.BooleanField()
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    original_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_type = serializers.CharField(allow_null=True)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    savings_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    discounted_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
