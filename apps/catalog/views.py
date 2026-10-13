from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from .filters import ProductFilter
from .models import Category, Product
from .pagination import StandardPagination
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductSerializer,
)


def public_products():
    """Only products customers are allowed to see, with queries optimised."""
    return (
        Product.objects.filter(is_available=True)
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")
    )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/catalog/categories/
    GET /api/catalog/categories/{id}/
    GET /api/catalog/categories/{id}/products/
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None  # the category list is small, return it all
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    @action(
        detail=True,
        methods=["get"],
        pagination_class=StandardPagination,  # but products inside are paginated
    )
    def products(self, request, pk=None):
        category = self.get_object()
        queryset = public_products().filter(category=category)

        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/catalog/products/        (list, with search/filter/sort/pages)
    GET /api/catalog/products/{id}/   (full detail with images)
    """

    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "description", "category__name"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return public_products()

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductSerializer