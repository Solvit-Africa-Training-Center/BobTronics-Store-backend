from rest_framework import serializers

from apps.catalog.models import Product
from .models import Wishlist, WishlistItem


class WishlistProductNestedSerializer(serializers.ModelSerializer):
    """Product details formatted for wishlist item responses."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    is_in_stock = serializers.SerializerMethodField()

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
            "is_in_stock",
        ]

    def get_is_in_stock(self, obj) -> bool:
        return obj.is_available and obj.stock_quantity > 0


class WishlistItemSerializer(serializers.ModelSerializer):
    """Read serializer for saved items in the user's wishlist."""

    product = WishlistProductNestedSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "wishlist_item_id",
            "product",
            "added_at",
        ]
        read_only_fields = ["wishlist_item_id", "added_at"]


class WishlistItemAddSerializer(serializers.Serializer):
    """Payload to add a product to the user's wishlist."""

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
    )

    def validate(self, attrs):
        product = attrs.get("product")
        request = self.context.get("request")
        if request and request.user.is_authenticated and product:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist and WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
                raise serializers.ValidationError(
                    {"product_id": f"Product '{product.name}' is already in your wishlist."}
                )
        return attrs


class MoveToCartSerializer(serializers.Serializer):
    """Optional quantity when moving an item from wishlist to cart."""

    quantity = serializers.IntegerField(default=1, min_value=1)
