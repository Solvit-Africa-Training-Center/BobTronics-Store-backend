from rest_framework import serializers

from .serializers import MAX_STOCK_QUANTITY


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
            raise serializers.ValidationError("Enter a non-zero stock change.")
        if abs(value) > MAX_STOCK_QUANTITY:
            raise serializers.ValidationError(
                f"Stock change cannot exceed {MAX_STOCK_QUANTITY} units."
            )
        return value
