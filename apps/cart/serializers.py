from rest_framework import serializers

from apps.catalog.models import Product
from apps.catalog.serializers import ProductListSerializer
from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ("cart_item_id", "product", "quantity", "subtotal", "added_at")
        read_only_fields = fields


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(is_available=True),
        required=False,
    )
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)

    def validate(self, attrs):
        product = attrs.get("product")
        if product and attrs["quantity"] > product.stock_quantity:
            raise serializers.ValidationError(
                {"quantity": "The requested quantity is not available."}
            )
        return attrs


class PromoCartLineSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(is_available=True),
    )
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)

    def validate(self, attrs):
        if attrs["quantity"] > attrs["product"].stock_quantity:
            raise serializers.ValidationError(
                {"quantity": "The requested quantity is not available."}
            )
        return attrs


class PromoValidationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, trim_whitespace=True)
    items = PromoCartLineSerializer(many=True, allow_empty=False)

    def validate_code(self, value):
        return value.strip().upper()
