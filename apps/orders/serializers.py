from decimal import Decimal
from rest_framework import serializers

from apps.catalog.models import Product
from .models import Order, OrderItem, OrderStatus


class OrderItemProductNestedSerializer(serializers.ModelSerializer):
    """Product summary within order line item."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "brand",
            "category_name",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """Line item in an order."""

    product = OrderItemProductNestedSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "order_item_id",
            "product",
            "quantity",
            "unit_price",
            "discount_amount",
            "subtotal",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Complete order representation including line items."""

    items = OrderItemSerializer(many=True, read_only=True)
    delivery = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()
    estimated_delivery = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_id",
            "customer_email",
            "customer_name",
            "order_date",
            "status",
            "status_display",
            "total_amount",
            "shipping_address",
            "phone",
            "payment_status",
            "payment_method",
            "payment_reference",
            "estimated_delivery",
            "items",
            "delivery",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_payment_status(self, obj) -> str:
        payment = getattr(obj, "payment", None)
        return payment.status if payment else "pending"

    def get_payment_method(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.payment_method if payment else None

    def get_payment_reference(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.transaction_reference if payment else None

    def get_estimated_delivery(self, obj):
        delivery = getattr(obj, "delivery", None)
        if delivery and delivery.delivered_at:
            return delivery.delivered_at.isoformat()
        return None

    def get_delivery(self, obj):
        delivery = getattr(obj, "delivery", None)
        if not delivery:
            return None
        return {
            "delivery_id": delivery.delivery_id,
            "status": delivery.status,
            "status_display": delivery.get_status_display(),
            "delivery_method": delivery.delivery_method,
            "delivery_method_display": delivery.get_delivery_method_display(),
            "tracking_number": delivery.tracking_number,
            "shipping_fee": str(delivery.shipping_fee),
            "estimated_delivery": self.get_estimated_delivery(obj),
            "shipped_at": delivery.shipped_at,
            "delivered_at": delivery.delivered_at,
        }


class OrderListSerializer(serializers.ModelSerializer):
    """Compact summary serializer for order listings."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_items = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    estimated_delivery = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_id",
            "customer_email",
            "customer_name",
            "order_date",
            "status",
            "status_display",
            "total_amount",
            "total_items",
            "shipping_address",
            "phone",
            "payment_status",
            "payment_method",
            "payment_reference",
            "delivery_status",
            "estimated_delivery",
            "created_at",
        ]
        read_only_fields = fields

    def get_total_items(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_customer_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_payment_status(self, obj) -> str:
        payment = getattr(obj, "payment", None)
        return payment.status if payment else "pending"

    def get_payment_method(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.payment_method if payment else None

    def get_payment_reference(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.transaction_reference if payment else None

    def get_delivery_status(self, obj):
        delivery = getattr(obj, "delivery", None)
        return delivery.status if delivery else None

    def get_estimated_delivery(self, obj):
        delivery = getattr(obj, "delivery", None)
        if delivery and delivery.delivered_at:
            return delivery.delivered_at.isoformat()
        return None


class OrderCheckoutSerializer(serializers.Serializer):
    """Payload to checkout the current shopping cart and create an order."""

    shipping_address = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=500,
        help_text="Destination address for delivery. Defaults to saved profile residence if omitted.",
    )
    phone = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=30,
        help_text="Contact phone number for delivery. Defaults to saved profile phone if omitted.",
    )
    delivery_method = serializers.ChoiceField(
        choices=["standard", "express", "store_pickup"],
        default="standard",
        required=False,
        help_text="Selected fulfillment option: standard, express, or store_pickup.",
    )

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        # Resolve shipping address
        address = attrs.get("shipping_address")
        if not address and user:
            address = getattr(user, "residence", "")
        if not address or not address.strip():
            raise serializers.ValidationError(
                {"shipping_address": "Shipping address is required to place an order."}
            )
        attrs["shipping_address"] = address.strip()

        # Resolve phone
        phone = attrs.get("phone")
        if not phone and user:
            phone = getattr(user, "phone", "")
        if not phone or not phone.strip():
            raise serializers.ValidationError(
                {"phone": "A valid phone number is required to place an order."}
            )
        attrs["phone"] = phone.strip()

        return attrs


class AdminOrderStatusUpdateSerializer(serializers.Serializer):
    """Admin payload to transition order status."""

    status = serializers.ChoiceField(choices=OrderStatus.choices)
