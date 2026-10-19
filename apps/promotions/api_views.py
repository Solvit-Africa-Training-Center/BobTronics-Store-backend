from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import filters, generics, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.common.permissions import IsAdminRole
from rest_framework.pagination import PageNumberPagination
from .models import Discount
from .serializers import (
    ActivePromotionSerializer,
    DiscountSerializer,
    ProductDiscountDetailSerializer,
)
from .services import calculate_discount, calculate_discounted_price


class PromotionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Promotions - Admin"])
class DiscountAdminViewSet(viewsets.ModelViewSet):
    """
    Administrative management of promotional discounts.
    Allows Admins to create, update, list, and toggle product discounts.
    """

    queryset = Discount.objects.select_related("product__category").all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminRole]
    pagination_class = PromotionPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["product", "discount_type", "is_active"]
    search_fields = ["product__name", "product__brand"]
    ordering_fields = ["start_date", "end_date", "discount_value", "created_at"]
    ordering = ["-start_date"]


@extend_schema(
    tags=["Promotions - Public"],
    summary="List active promotional deals",
    description="Returns all currently active product discounts for special offers and sales banners.",
    responses={200: ActivePromotionSerializer(many=True)},
)
class ActivePromotionsListView(generics.ListAPIView):
    """
    Public listing of currently active promotional deals.
    Only discounts where is_active=True and today is within start/end dates are returned.
    """

    serializer_class = ActivePromotionSerializer
    permission_classes = [AllowAny]
    pagination_class = PromotionPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product__name", "product__brand", "product__category__name"]
    ordering_fields = ["discount_value", "end_date", "created_at"]
    ordering = ["-discount_value"]

    def get_queryset(self):
        today = timezone.localdate()
        return (
            Discount.objects.filter(
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
                product__is_available=True,
            )
            .select_related("product__category")
            .prefetch_related("product__images")
        )


@extend_schema(
    tags=["Promotions - Public"],
    summary="Get product discount status",
    description="Check active discount, savings, and final price for a given product ID.",
    responses={
        200: ProductDiscountDetailSerializer,
        404: OpenApiResponse(description="Product not found"),
    },
)
class ProductDiscountView(APIView):
    """
    Public verification endpoint to inspect active discount for a single product.
    """

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        today = timezone.localdate()
        best_savings = calculate_discount(product, on_date=today)
        discounted_price = calculate_discounted_price(product, on_date=today)

        active_discount = (
            Discount.objects.filter(
                product=product,
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .order_by("-discount_value")
            .first()
        )

        data = {
            "has_discount": best_savings > Decimal("0.00"),
            "product_id": product.product_id,
            "product_name": product.name,
            "original_price": product.price,
            "discount_type": active_discount.discount_type if active_discount else None,
            "discount_value": active_discount.discount_value if active_discount else None,
            "savings_amount": best_savings,
            "discounted_price": discounted_price,
            "start_date": active_discount.start_date if active_discount else None,
            "end_date": active_discount.end_date if active_discount else None,
        }
        serializer = ProductDiscountDetailSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
