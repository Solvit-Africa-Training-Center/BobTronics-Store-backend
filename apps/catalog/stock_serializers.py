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
