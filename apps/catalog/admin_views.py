import logging

from django.db import transaction
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsAdminRole

from .filters import ProductFilter
from .models import Category, Product, ProductImage, StockMovementType
from .pagination import StandardPagination
from .serializers import (
    MAX_STOCK_QUANTITY,
    CategorySerializer,
    ProductImageSerializer,
    ProductSerializer,
)
from .stock_serializers import LowStockQuerySerializer, StockAdjustmentSerializer
from .stock_service import StockError, deduct_stock, low_stock_products, restore_stock

logger = logging.getLogger(__name__)


class ProtectedDeleteMixin:
    """
    Return a clear 409 instead of a server error when an object cannot be
    deleted because other records depend on it (for example a product that
    already appears in an order).
    """

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            message = "This item is in use and can't be deleted. Deactivate it instead."
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": message,
                        "details": {"detail": message},
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )


class CategoryAdminViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    Admin CRUD for categories.

    GET    /api/v1/catalog/admin/categories/
    POST   /api/v1/catalog/admin/categories/
    GET    /api/v1/catalog/admin/categories/{id}/
    PUT    /api/v1/catalog/admin/categories/{id}/
    PATCH  /api/v1/catalog/admin/categories/{id}/
    DELETE /api/v1/catalog/admin/categories/{id}/
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]


class ProductAdminViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    Admin CRUD for products. Unlike the public API, this also returns
    products where is_available=False so admins can manage hidden items.

    GET    /api/v1/catalog/admin/products/
    POST   /api/v1/catalog/admin/products/
    GET    /api/v1/catalog/admin/products/{id}/
    PUT    /api/v1/catalog/admin/products/{id}/
    PATCH  /api/v1/catalog/admin/products/{id}/
    DELETE /api/v1/catalog/admin/products/{id}/
    POST   /api/v1/catalog/admin/products/{id}/adjust-stock/
    GET    /api/v1/catalog/admin/products/low-stock/?threshold=N
    """

    queryset = (
        Product.objects.all()
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")
    )
    serializer_class = ProductSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "description", "category__name"]
    ordering_fields = ["price", "name", "stock_quantity", "created_at"]

    @extend_schema(
        parameters=[LowStockQuerySerializer],
        responses=ProductSerializer(many=True),
        description=(
            "List all products, including unavailable products, whose stock "
            "is at or below the required non-negative threshold."
        ),
    )
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        serializer = LowStockQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        products = low_stock_products(serializer.validated_data["threshold"])
        page = self.paginate_queryset(products)
        if page is not None:
            return self.get_paginated_response(ProductSerializer(page, many=True).data)
        return Response(ProductSerializer(products, many=True).data)

    @extend_schema(
        request=StockAdjustmentSerializer,
        responses=ProductSerializer,
        description=(
            "Add (positive delta) or remove (negative delta) units from stock. "
            "Works on hidden products too, so damaged or lost items can be "
            "written off."
        ),
    )
    @action(detail=True, methods=["post"], url_path="adjust-stock")
    def adjust_stock(self, request, pk=None):
        product = self.get_object()

        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delta = serializer.validated_data["delta"]
        reason = serializer.validated_data.get("reason", "")

        if delta > 0 and product.stock_quantity + delta > MAX_STOCK_QUANTITY:
            raise serializers.ValidationError(
                {
                    "delta": (
                        f"Stock cannot exceed {MAX_STOCK_QUANTITY} units."
                    )
                }
            )

        try:
            if delta > 0:
                restore_stock(
                    [(product.pk, delta)],
                    source="inventory_adjustment",
                    reason=reason or "Manual stock increase",
                    actor=request.user,
                    movement_type=StockMovementType.ADJUSTMENT,
                )
            else:
                deduct_stock(
                    [(product.pk, -delta)],
                    require_available=False,
                    source="inventory_adjustment",
                    reason=reason or "Manual stock decrease",
                    actor=request.user,
                    movement_type=StockMovementType.ADJUSTMENT,
                )
        except StockError as exc:
            message = str(exc)
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": message,
                        "details": {"detail": message},
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        logger.info(
            "Stock adjusted: product=%s delta=%s by user=%s reason=%r",
            product.pk,
            delta,
            request.user.pk,
            reason,
        )

        product = self.get_object()  # fresh copy with the new stock level
        return Response(ProductSerializer(product).data)


class ProductImageAdminViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    Admin CRUD for product images.

    Only one image per product can be primary: marking an image as primary
    automatically unmarks the product's other images.

    GET    /api/v1/catalog/admin/images/?product=5
    POST   /api/v1/catalog/admin/images/
    GET    /api/v1/catalog/admin/images/{id}/
    PUT    /api/v1/catalog/admin/images/{id}/
    PATCH  /api/v1/catalog/admin/images/{id}/
    DELETE /api/v1/catalog/admin/images/{id}/
    """

    queryset = ProductImage.objects.select_related("product").order_by("-created_at")
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "is_primary"]

    @transaction.atomic
    def perform_create(self, serializer):
        image = serializer.save()
        self._keep_single_primary(image)

    @transaction.atomic
    def perform_update(self, serializer):
        image = serializer.save()
        self._keep_single_primary(image)

    @staticmethod
    def _keep_single_primary(image):
        if image.is_primary:
            ProductImage.objects.filter(product=image.product).exclude(
                pk=image.pk
            ).update(is_primary=False)
