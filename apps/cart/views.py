from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from django.shortcuts import get_object_or_404

from apps.accounts.permissions import IsCustomer
from apps.promotions.models import DiscountType, PromoCode

from .models import CartItem
from .serializers import CartItemSerializer, CartItemWriteSerializer, PromoValidationSerializer


class CartView(GenericAPIView):
    permission_classes = [IsCustomer]
    serializer_class = CartItemWriteSerializer

    def get(self, request, *args, **kwargs):
        items = (
            CartItem.objects.filter(user=request.user)
            .select_related("product", "product__category")
            .prefetch_related("product__images")
        )
        data = CartItemSerializer(items, many=True, context={"request": request}).data
        subtotal = sum(
            (item.subtotal for item in items), Decimal("0.00")
        ).quantize(Decimal("0.01"))
        return Response({"items": data, "count": len(data), "subtotal": str(subtotal)})

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data.get("product")
        if product is None:
            raise serializers.ValidationError({"product_id": "Choose a product."})

        quantity = serializer.validated_data["quantity"]
        item = CartItem.objects.filter(user=request.user, product=product).first()
        new_quantity = quantity + (item.quantity if item else 0)
        if new_quantity > product.stock_quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock_quantity} unit(s) are available."}
            )
        if item:
            item.quantity = new_quantity
            item.save(update_fields=("quantity",))
        else:
            item = CartItem.objects.create(
                user=request.user, product=product, quantity=quantity
            )
        return Response(
            {
                "message": "Cart updated.",
                "item": CartItemSerializer(item, context={"request": request}).data,
            },
            status=status.HTTP_200_OK if new_quantity != quantity else status.HTTP_201_CREATED,
        )

    def delete(self, request, *args, **kwargs):
        CartItem.objects.filter(user=request.user).delete()
        return Response({"message": "Cart cleared."})


class CartItemDetailView(GenericAPIView):
    permission_classes = [IsCustomer]
    serializer_class = CartItemWriteSerializer
    lookup_field = "cart_item_id"

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related(
            "product", "product__category"
        ).prefetch_related("product__images")

    def patch(self, request, cart_item_id):
        item = get_object_or_404(self.get_queryset(), cart_item_id=cart_item_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        if quantity > item.product.stock_quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {item.product.stock_quantity} unit(s) are available."}
            )
        item.quantity = quantity
        item.save(update_fields=("quantity",))
        return Response(
            {
                "message": "Cart updated.",
                "item": CartItemSerializer(item, context={"request": request}).data,
            }
        )

    def delete(self, request, cart_item_id):
        item = get_object_or_404(self.get_queryset(), cart_item_id=cart_item_id)
        item.delete()
        return Response({"message": "Product removed from your cart."})


class PromoValidationView(generics.GenericAPIView):
    """Validate a promo code and calculate its value against current product prices."""

    permission_classes = [IsCustomer]
    serializer_class = PromoValidationSerializer

    def get_permissions(self):
        if self.request.method == "OPTIONS":
            return [AllowAny()]
        return super().get_permissions()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        today = timezone.localdate()
        promo = PromoCode.objects.filter(code=data["code"]).first()

        if (
            promo is None
            or not promo.is_active
            or today < promo.start_date
            or today > promo.end_date
            or (promo.usage_limit is not None and promo.usage_count >= promo.usage_limit)
        ):
            return Response({"valid": False, "message": "This promo code is not available."})

        subtotal = sum(
            (line["product"].price * line["quantity"] for line in data["items"]),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))
        if subtotal < promo.minimum_order_amount:
            return Response(
                {
                    "valid": False,
                    "message": "Your cart does not meet this promo's minimum spend.",
                    "minimum_order_amount": str(promo.minimum_order_amount),
                }
            )

        if promo.discount_type == DiscountType.PERCENTAGE:
            if promo.discount_value > 100:
                return Response(
                    {"valid": False, "message": "This promo code is configured incorrectly."},
                )
            discount = subtotal * promo.discount_value / Decimal("100")
        else:
            discount = promo.discount_value
        discount = min(discount, subtotal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return Response(
            {
                "valid": True,
                "code": promo.code,
                "discount_type": promo.discount_type,
                "discount_value": str(promo.discount_value),
                "subtotal": str(subtotal),
                "discount_amount": str(discount),
                "total": str(subtotal - discount),
                "message": "Promo code applied.",
            }
        )
