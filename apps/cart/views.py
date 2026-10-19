from decimal import Decimal
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CartItem
from .serializers import (
    CartItemAddSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
)


class CartView(APIView):
    """
    GET: Retrieve the authenticated user's current shopping cart,
    including aggregated item counts, totals, and line item details.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="View Shopping Cart",
        description="Returns all items in the authenticated user's cart along with summary totals.",
        responses={200: CartItemSerializer(many=True)},
    )
    def get(self, request):
        items = (
            CartItem.objects.filter(user=request.user)
            .select_related("product", "product__category")
            .order_by("-added_at")
        )

        serializer = CartItemSerializer(items, many=True)
        serialized_items = serializer.data

        # Calculate totals using DB expression / aggregate
        total_items = sum(item.quantity for item in items)
        total_price = sum(item.subtotal for item in items) or Decimal("0.00")
        has_out_of_stock = any(not item["is_in_stock"] for item in serialized_items)

        return Response(
            {
                "success": True,
                "data": {
                    "items": serialized_items,
                    "total_items": total_items,
                    "total_price": str(total_price),
                    "has_out_of_stock_items": has_out_of_stock,
                },
            },
            status=status.HTTP_200_OK,
        )


class CartItemAddView(APIView):
    """
    POST: Add a product to the user's cart or increment its quantity if already present.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add Product to Cart",
        description="Adds a product to the cart or increments existing quantity with stock validation.",
        request=CartItemAddSerializer,
        responses={
            201: CartItemSerializer,
            400: OpenApiResponse(description="Validation or insufficient stock error"),
        },
    )
    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])

        # Reload with relations for clean serialized response
        cart_item = (
            CartItem.objects.select_related("product", "product__category")
            .get(pk=cart_item.pk)
        )

        return Response(
            {
                "success": True,
                "message": "Product added to cart successfully.",
                "data": CartItemSerializer(cart_item).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    """
    PATCH: Update the quantity of a specific item in the cart.
    DELETE: Remove a specific item from the cart.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, user, cart_item_id):
        return get_object_or_404(
            CartItem.objects.select_related("product", "product__category"),
            user=user,
            cart_item_id=cart_item_id,
        )

    @extend_schema(
        summary="Update Cart Item Quantity",
        description="Updates the quantity of an item currently in the cart with stock validation.",
        request=CartItemUpdateSerializer,
        responses={200: CartItemSerializer},
    )
    def patch(self, request, cart_item_id):
        cart_item = self.get_object(request.user, cart_item_id)
        serializer = CartItemUpdateSerializer(
            data=request.data, context={"cart_item": cart_item}
        )
        serializer.is_valid(raise_exception=True)

        cart_item.quantity = serializer.validated_data["quantity"]
        cart_item.save(update_fields=["quantity"])

        return Response(
            {
                "success": True,
                "message": "Cart item quantity updated.",
                "data": CartItemSerializer(cart_item).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Remove Cart Item",
        description="Remplements an item from the customer's cart.",
        responses={200: OpenApiResponse(description="Item removed successfully.")},
    )
    def delete(self, request, cart_item_id):
        cart_item = self.get_object(request.user, cart_item_id)
        product_name = cart_item.product.name
        cart_item.delete()

        return Response(
            {
                "success": True,
                "message": f"'{product_name}' was removed from your cart.",
            },
            status=status.HTTP_200_OK,
        )


class CartClearView(APIView):
    """
    DELETE: Remove all items from the customer's shopping cart.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Clear Cart",
        description="Empties the customer's shopping cart.",
        responses={200: OpenApiResponse(description="Cart cleared successfully.")},
    )
    def delete(self, request):
        count, _ = CartItem.objects.filter(user=request.user).delete()
        return Response(
            {
                "success": True,
                "message": "Your cart has been cleared.",
                "deleted_count": count,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        return self.delete(request)
