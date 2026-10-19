from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import CartItem
from apps.catalog.models import Product
from .models import Wishlist, WishlistItem
from .serializers import (
    MoveToCartSerializer,
    WishlistItemAddSerializer,
    WishlistItemSerializer,
)


class WishlistView(APIView):
    """
    GET: Retrieve all products saved in the authenticated customer's wishlist.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="View Wishlist",
        description="Returns all products saved in the user's wishlist.",
        responses={200: WishlistItemSerializer(many=True)},
    )
    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        items = (
            WishlistItem.objects.filter(wishlist=wishlist)
            .select_related("product", "product__category")
            .order_by("-added_at")
        )
        serializer = WishlistItemSerializer(items, many=True)
        return Response(
            {
                "success": True,
                "data": {
                    "items": serializer.data,
                    "total_saved": items.count(),
                },
            },
            status=status.HTTP_200_OK,
        )


class WishlistItemAddView(APIView):
    """
    POST: Save a product to the user's wishlist (e.g. out-of-stock or saved for later).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add Product to Wishlist",
        description="Adds a product to the user's wishlist.",
        request=WishlistItemAddSerializer,
        responses={
            201: WishlistItemSerializer,
            400: OpenApiResponse(description="Product already in wishlist or invalid"),
        },
    )
    def post(self, request):
        serializer = WishlistItemAddSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        product = serializer.validated_data["product"]

        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product,
        )

        item = (
            WishlistItem.objects.select_related("product", "product__category")
            .get(pk=item.pk)
        )

        return Response(
            {
                "success": True,
                "message": "Saved to wishlist.",
                "data": WishlistItemSerializer(item).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WishlistItemDetailView(APIView):
    """
    DELETE: Remove a product from the user's wishlist.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove Product from Wishlist",
        description="Removes a product from the user's wishlist by product ID.",
        responses={200: OpenApiResponse(description="Item removed from wishlist.")},
    )
    def delete(self, request, product_id):
        wishlist = get_object_or_404(Wishlist, user=request.user)
        item = get_object_or_404(
            WishlistItem.objects.select_related("product"),
            wishlist=wishlist,
            product_id=product_id,
        )
        product_name = item.product.name
        item.delete()

        return Response(
            {
                "success": True,
                "message": "Removed from wishlist.",
            },
            status=status.HTTP_200_OK,
        )


class WishlistMoveToCartView(APIView):
    """
    POST: Move an item from the customer's wishlist to their shopping cart
    once it becomes available or in stock.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Move Wishlist Item to Cart",
        description="Transfers a product from wishlist to cart if stock is available.",
        request=MoveToCartSerializer,
        responses={
            200: OpenApiResponse(description="Moved to cart."),
            400: OpenApiResponse(description="Insufficient stock or unavailable."),
        },
    )
    def post(self, request, product_id):
        serializer = MoveToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data.get("quantity", 1)

        wishlist = get_object_or_404(Wishlist, user=request.user)
        wishlist_item = get_object_or_404(
            WishlistItem.objects.select_related("product"),
            wishlist=wishlist,
            product_id=product_id,
        )
        product = wishlist_item.product

        # Validate stock availability
        if not product.is_available:
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": 400,
                        "message": f"{product.name} is unavailable.",
                        "details": {"detail": f"{product.name} is unavailable."},
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if product.stock_quantity < quantity:
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": 400,
                        "message": (
                            f"{product.name}: {product.stock_quantity} left; {quantity} requested."
                        ),
                        "details": {
                            "detail": f"{product.name}: {product.stock_quantity} left; {quantity} requested."
                        },
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add / increment in Cart
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])

        # Remove from Wishlist
        wishlist_item.delete()

        return Response(
            {
                "success": True,
                "message": "Moved to cart.",
            },
            status=status.HTTP_200_OK,
        )
