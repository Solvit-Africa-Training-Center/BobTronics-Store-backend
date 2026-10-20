from rest_framework import serializers

from apps.catalog.models import Product
from apps.deliveries.models import DeliveryMethod

from .models import Order, OrderItem, OrderStatus


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.filter(is_available=True)
    )
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


class OrderCreateSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(max_length=2000)
    phone = serializers.CharField(max_length=30)
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    promo_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    items = OrderItemInputSerializer(many=True, allow_empty=False)

    def validate_promo_code(self, value):
        return value.strip().upper()

    def validate_items(self, items):
        product_ids = [item["product"].pk for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Include each product once and set its quantity."
            )
        return items


class OrderItemReadSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.product_id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "order_item_id",
            "product_id",
            "product_name",
            "quantity",
            "unit_price",
            "discount_amount",
            "subtotal",
        )
        read_only_fields = fields


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    delivery_method = serializers.SerializerMethodField()
    tracking_number = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "order_id",
            "order_date",
            "status",
            "total_amount",
            "promo_code",
            "promo_discount_amount",
            "shipping_address",
            "phone",
            "delivery_method",
            "tracking_number",
            "items",
        )
        read_only_fields = fields

    @staticmethod
    def get_delivery_method(obj):
        delivery = getattr(obj, "delivery", None)
        return delivery.delivery_method if delivery else None

    @staticmethod
    def get_tracking_number(obj):
        delivery = getattr(obj, "delivery", None)
        return delivery.tracking_number if delivery else None


class AdminOrderReadSerializer(OrderReadSerializer):
    customer_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(OrderReadSerializer.Meta):
        fields = ("customer_email",) + OrderReadSerializer.Meta.fields


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=(
            (OrderStatus.PENDING, "Pending"),
            (OrderStatus.CONFIRMED, "Confirmed"),
            (OrderStatus.PROCESSING, "Processing"),
            (OrderStatus.CANCELLED, "Cancelled"),
        )
    )

    class Meta:
        model = Order
        fields = ("status",)

    def validate_status(self, value):
        current = self.instance.status
        allowed = {
            OrderStatus.PENDING: {
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
            },
            OrderStatus.CONFIRMED: {
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
            },
            OrderStatus.PROCESSING: {OrderStatus.CANCELLED},
            OrderStatus.SHIPPED: set(),
            OrderStatus.DELIVERED: set(),
            OrderStatus.CANCELLED: set(),
            OrderStatus.FAILED: set(),
            OrderStatus.RETURNED: set(),
        }
        if value != current and value not in allowed[current]:
            raise serializers.ValidationError(
                f"An order cannot move from {current} to {value}."
            )
        return value
