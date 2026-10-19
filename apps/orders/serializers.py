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
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.SerializerMethodField()

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
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "order_id",
            "customer_email",
            "customer_name",
            "order_date",
            "status",
            "status_display",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class OrderListSerializer(serializers.ModelSerializer):
    """Compact summary serializer for order listings."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_items = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_id",
            "customer_email",
            "order_date",
            "status",
            "status_display",
            "total_amount",
            "total_items",
            "shipping_address",
            "phone",
            "created_at",
        ]
        read_only_fields = fields

    def get_total_items(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())


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

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        # Resolve shipping address
        address = attrs.get("shipping_address")
        if not address and user:
            address = getattr(user, "residence", "")
        if not address or not address.strip():
            raise serializers.ValidationError(
                {"shipping_address": "Enter a shipping address."}
            )
        attrs["shipping_address"] = address.strip()

        # Resolve phone
        phone = attrs.get("phone")
        if not phone and user:
            phone = getattr(user, "phone", "")
        if not phone or not phone.strip():
            raise serializers.ValidationError(
                {"phone": "Enter a valid phone number."}
            )
        attrs["phone"] = phone.strip()

        return attrs


class AdminOrderStatusUpdateSerializer(serializers.Serializer):
    """Admin payload to transition order status."""

    status = serializers.ChoiceField(choices=OrderStatus.choices)
