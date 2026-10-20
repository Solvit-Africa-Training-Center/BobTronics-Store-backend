from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer

from .models import Wishlist, WishlistItem
from .serializers import WishlistAddSerializer, WishlistItemSerializer


class WishlistView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        items = (
            WishlistItem.objects.filter(wishlist__user=request.user)
            .select_related("product", "product__category")
            .prefetch_related("product__images")
        )
        data = WishlistItemSerializer(
            items, many=True, context={"request": request}
        ).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        serializer = WishlistAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=serializer.validated_data["product"],
        )
        data = WishlistItemSerializer(item, context={"request": request}).data
        return Response(
            {
                "message": "Product saved." if created else "Product is already saved.",
                "item": data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class WishlistRemoveView(APIView):
    permission_classes = [IsCustomer]

    def delete(self, request, product_id):
        wishlist = get_object_or_404(Wishlist, user=request.user)
        item = get_object_or_404(
            WishlistItem,
            wishlist=wishlist,
            product_id=product_id,
        )
        item.delete()
        return Response({"message": "Product removed from your saved list."})
