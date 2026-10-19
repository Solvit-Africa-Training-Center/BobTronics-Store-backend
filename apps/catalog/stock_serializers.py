from rest_framework import serializers

from .serializers import MAX_STOCK_QUANTITY


class LowStockQuerySerializer(serializers.Serializer):
    threshold = serializers.IntegerField(
        min_value=0,
        required=True,
        help_text="Required minimum stock threshold; products at or below it are returned.",
    )


class StockAdjustmentSerializer(serializers.Serializer):
    delta = serializers.IntegerField(
        help_text=(
            "Units to add (positive) or remove (negative). "
            "For example 20 for a delivery, -2 for damaged items."
        )
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Optional note, written to the server log.",
    )

    def validate_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Delta cannot be zero.")
        if abs(value) > MAX_STOCK_QUANTITY:
            raise serializers.ValidationError(
                f"Delta cannot be larger than {MAX_STOCK_QUANTITY}."
            )
        return value


class StockMovementHistorySerializer(serializers.Serializer):
    """Represents a historic stock adjustment / deduction / restoration."""

    movement_id = serializers.IntegerField(read_only=True)
    delta = serializers.IntegerField(source="quantity_change", read_only=True)
    quantity_before = serializers.IntegerField(read_only=True)
    resulting_stock_quantity = serializers.IntegerField(source="quantity_after", read_only=True)
    movement_type = serializers.CharField(read_only=True)
    reason = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_user(self, obj):
        if not obj.actor:
            return None
        return {
            "user_id": obj.actor.user_id,
            "name": f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.email,
            "email": obj.actor.email,
        }

