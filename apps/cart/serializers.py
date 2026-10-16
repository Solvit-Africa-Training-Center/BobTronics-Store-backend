from decimal import Decimal
from rest_framework import serializers

from apps.catalog.models import Product
from .models import CartItem


class CartProductNestedSerializer(serializers.ModelSerializer):
    """Minimal product representation for cart item responses."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "brand",
            "price",
            "stock_quantity",
            "is_available",
            "category_name",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    """Read serializer for items in the customer's shopping cart."""

    product = CartProductNestedSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "cart_item_id",
            "product",
            "quantity",
            "subtotal",
            "is_in_stock",
            "added_at",
        ]
        read_only_fields = ["cart_item_id", "subtotal", "is_in_stock", "added_at"]

    def get_is_in_stock(self, obj) -> bool:
        return obj.product.is_available and obj.product.stock_quantity >= obj.quantity


class CartItemAddSerializer(serializers.Serializer):
    """Payload to add a product to the user's cart."""

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
    )
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate(self, attrs):
        product = attrs["product"]
        quantity = attrs.get("quantity", 1)

        if not product.is_available:
            raise serializers.ValidationError(
                {"product_id": f"{product.name} is unavailable."}
            )

        # Check existing quantity in the user's cart if any
        request = self.context.get("request")
        existing_qty = 0
        if request and request.user.is_authenticated:
            existing_item = CartItem.objects.filter(
                user=request.user, product=product
            ).first()
            if existing_item:
                existing_qty = existing_item.quantity

        total_requested = existing_qty + quantity
        if product.stock_quantity < total_requested:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        f"Only {product.stock_quantity} available; {total_requested} requested."
                    )
                }
            )

        return attrs


class CartItemUpdateSerializer(serializers.Serializer):
    """Payload to update the quantity of an existing item in the cart."""

    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        cart_item = self.context.get("cart_item")
        if cart_item:
            product = cart_item.product
            if not product.is_available:
                raise serializers.ValidationError(
                    f"{product.name} is unavailable."
                )
            if product.stock_quantity < value:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity} available; {value} requested."
                )
        return value
