from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny

from apps.common.permissions import IsAdminRole

from .models import Discount, PromoCode
from .serializers import DiscountSerializer, PromoCodeSerializer


class ActiveDiscountListView(generics.ListAPIView):
    serializer_class = DiscountSerializer
    permission_classes = [AllowAny]
    filterset_fields = ("product",)

    def get_queryset(self):
        today = timezone.localdate()
        return (
            Discount.objects.filter(
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related("product")
            .order_by("-start_date")
        )


class AdminDiscountViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminRole]
    queryset = Discount.objects.select_related("product").order_by("-start_date")
    filterset_fields = ("product", "discount_type", "is_active")


class AdminPromoCodeViewSet(viewsets.ModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdminRole]
    queryset = PromoCode.objects.order_by("-start_date")
    filterset_fields = ("discount_type", "is_active")
