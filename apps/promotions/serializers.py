from rest_framework import serializers

from .models import Discount, DiscountType


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ["discount_id", "product", "discount_type", "discount_value", "start_date", "end_date", "is_active", "created_at", "updated_at"]
        read_only_fields = ["discount_id", "created_at", "updated_at"]

    def validate(self, attrs):
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", DiscountType.PERCENTAGE))
        value = attrs.get("discount_value", getattr(self.instance, "discount_value", None))
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        errors = {}
        if value is not None and value <= 0:
            errors["discount_value"] = "Discount must be above zero."
        if discount_type == DiscountType.PERCENTAGE and value is not None and value > 100:
            errors["discount_value"] = "Percentage discount cannot exceed 100%."
        if start and end and end < start:
            errors["end_date"] = "End date must be on or after the start date."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
