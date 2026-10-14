from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.common.permissions import IsAdminRole

from .models import Discount
from .serializers import DiscountSerializer


class DiscountAdminViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.select_related("product").all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["product", "discount_type", "is_active"]
    search_fields = ["product__name", "product__brand"]
    ordering_fields = ["start_date", "end_date", "discount_value", "created_at"]
    ordering = ["-start_date"]
