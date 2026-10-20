from rest_framework import serializers

from .models import Discount, DiscountType, PromoCode


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = (
            "discount_id",
            "product",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("discount_id", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        kind = attrs.get(
            "discount_type", getattr(self.instance, "discount_type", DiscountType.PERCENTAGE)
        )
        value = attrs.get(
            "discount_value", getattr(self.instance, "discount_value", None)
        )
        errors = {}
        if start and end and end < start:
            errors["end_date"] = "End date must be on or after the start date."
        if kind == DiscountType.PERCENTAGE and value is not None and value > 100:
            errors["discount_value"] = "Percentage discounts cannot exceed 100%."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = (
            "promo_id",
            "code",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "minimum_order_amount",
            "usage_limit",
            "usage_count",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("promo_id", "usage_count", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        kind = attrs.get(
            "discount_type", getattr(self.instance, "discount_type", DiscountType.PERCENTAGE)
        )
        value = attrs.get(
            "discount_value", getattr(self.instance, "discount_value", None)
        )
        usage_limit = attrs.get("usage_limit", getattr(self.instance, "usage_limit", None))
        usage_count = getattr(self.instance, "usage_count", 0)
        errors = {}
        if start and end and end < start:
            errors["end_date"] = "End date must be on or after the start date."
        if kind == DiscountType.PERCENTAGE and value is not None and value > 100:
            errors["discount_value"] = "Percentage discounts cannot exceed 100%."
        if usage_limit is not None and usage_limit < usage_count:
            errors["usage_limit"] = "Usage limit cannot be below current usage."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
