from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

from apps.orders.models import OrderStatus
from .models import Delivery, DeliveryMethod, DeliveryStatus


class DeliveryOrderNestedSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(read_only=True)
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    order_status = serializers.CharField(source="status", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    def get_customer_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class DeliverySerializer(serializers.ModelSerializer):
    """Full delivery representation."""

    order = DeliveryOrderNestedSerializer(read_only=True)
    delivery_method_display = serializers.CharField(source="get_delivery_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "delivery_id",
            "order",
            "delivery_address",
            "delivery_method",
            "delivery_method_display",
            "tracking_number",
            "status",
            "status_display",
            "shipping_fee",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    """Public customer package tracking summary."""

    delivery_method_display = serializers.CharField(source="get_delivery_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_id = serializers.IntegerField(source="order.order_id", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "tracking_number",
            "order_id",
            "status",
            "status_display",
            "delivery_method",
            "delivery_method_display",
            "delivery_address",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DeliveryStatusUpdateSerializer(serializers.Serializer):
    """Admin payload to advance delivery state and manage tracking."""

    status = serializers.ChoiceField(choices=DeliveryStatus.choices)
    tracking_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    delivery_address = serializers.CharField(required=False, allow_blank=False)

    VALID_TRANSITIONS = {
        DeliveryStatus.PENDING: [DeliveryStatus.IN_TRANSIT, DeliveryStatus.OUT_FOR_DELIVERY, DeliveryStatus.FAILED],
        DeliveryStatus.IN_TRANSIT: [DeliveryStatus.OUT_FOR_DELIVERY, DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.RETURNED],
        DeliveryStatus.OUT_FOR_DELIVERY: [DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.RETURNED],
        DeliveryStatus.FAILED: [DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT, DeliveryStatus.RETURNED],
        DeliveryStatus.DELIVERED: [],
        DeliveryStatus.RETURNED: [],
    }

    def validate_status(self, new_status):
        instance = self.context.get("delivery")
        if instance:
            current_status = instance.status
            if current_status == new_status:
                return new_status
            allowed = self.VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                raise serializers.ValidationError(
                    f"Invalid status transition from '{current_status}' to '{new_status}'. "
                    f"Allowed transitions: {allowed if allowed else 'None (terminal state)'}."
                )
        return new_status

    def validate_tracking_number(self, value):
        if value:
            instance = self.context.get("delivery")
            qs = Delivery.objects.filter(tracking_number=value)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError("This tracking number is already in use.")
        return value

    def save(self, **kwargs):
        delivery = self.context["delivery"]
        new_status = self.validated_data["status"]
        now = timezone.now()

        delivery.status = new_status

        if "tracking_number" in self.validated_data and self.validated_data["tracking_number"]:
            delivery.tracking_number = self.validated_data["tracking_number"].strip()

        if "delivery_address" in self.validated_data:
            delivery.delivery_address = self.validated_data["delivery_address"].strip()

        # Update timestamps and synchronize order status
        if new_status in (DeliveryStatus.IN_TRANSIT, DeliveryStatus.OUT_FOR_DELIVERY) and not delivery.shipped_at:
            delivery.shipped_at = now
            if delivery.order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING):
                delivery.order.status = OrderStatus.SHIPPED
                delivery.order.save(update_fields=["status", "updated_at"])

        elif new_status == DeliveryStatus.DELIVERED and not delivery.delivered_at:
            delivery.delivered_at = now
            if delivery.order.status != OrderStatus.CANCELLED:
                delivery.order.status = OrderStatus.DELIVERED
                delivery.order.save(update_fields=["status", "updated_at"])

        delivery.save()
        return delivery
