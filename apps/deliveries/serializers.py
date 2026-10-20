from rest_framework import serializers

from .models import Delivery, DeliveryStatus


class DeliveryReadSerializer(serializers.ModelSerializer):
    order_status = serializers.CharField(source="order.status", read_only=True)

    class Meta:
        model = Delivery
        fields = (
            "delivery_id",
            "order",
            "order_status",
            "delivery_address",
            "delivery_method",
            "tracking_number",
            "status",
            "shipping_fee",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminDeliveryReadSerializer(DeliveryReadSerializer):
    customer_email = serializers.EmailField(source="order.user.email", read_only=True)

    class Meta(DeliveryReadSerializer.Meta):
        fields = ("customer_email",) + DeliveryReadSerializer.Meta.fields


class DeliveryUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=DeliveryStatus.choices, required=False)

    class Meta:
        model = Delivery
        fields = (
            "delivery_address",
            "delivery_method",
            "tracking_number",
            "status",
            "shipping_fee",
        )

    def validate_status(self, value):
        current = self.instance.status
        allowed = {
            DeliveryStatus.PENDING: {
                DeliveryStatus.IN_TRANSIT,
                DeliveryStatus.FAILED,
                DeliveryStatus.RETURNED,
            },
            DeliveryStatus.IN_TRANSIT: {
                DeliveryStatus.OUT_FOR_DELIVERY,
                DeliveryStatus.DELIVERED,
                DeliveryStatus.FAILED,
                DeliveryStatus.RETURNED,
            },
            DeliveryStatus.OUT_FOR_DELIVERY: {
                DeliveryStatus.DELIVERED,
                DeliveryStatus.FAILED,
                DeliveryStatus.RETURNED,
            },
            DeliveryStatus.FAILED: {
                DeliveryStatus.IN_TRANSIT,
                DeliveryStatus.RETURNED,
            },
            DeliveryStatus.DELIVERED: set(),
            DeliveryStatus.RETURNED: set(),
        }
        if value != current and value not in allowed[current]:
            raise serializers.ValidationError(
                f"A delivery cannot move from {current} to {value}."
            )
        return value
