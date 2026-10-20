from django.db import transaction
from django.utils import timezone
from rest_framework import generics, serializers

from apps.accounts.permissions import IsCustomer
from apps.common.permissions import IsAdminRole
from apps.orders.models import OrderStatus

from .models import Delivery, DeliveryStatus
from .serializers import (
    AdminDeliveryReadSerializer,
    DeliveryReadSerializer,
    DeliveryUpdateSerializer,
)


class CustomerDeliveryListView(generics.ListAPIView):
    serializer_class = DeliveryReadSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return (
            Delivery.objects.filter(order__user=self.request.user)
            .select_related("order")
            .order_by("-created_at")
        )


class CustomerDeliveryDetailView(generics.RetrieveAPIView):
    serializer_class = DeliveryReadSerializer
    permission_classes = [IsCustomer]
    lookup_field = "delivery_id"

    def get_queryset(self):
        return Delivery.objects.filter(order__user=self.request.user).select_related(
            "order"
        )


class AdminDeliveryListView(generics.ListAPIView):
    serializer_class = AdminDeliveryReadSerializer
    permission_classes = [IsAdminRole]
    queryset = Delivery.objects.select_related("order", "order__user").order_by(
        "-created_at"
    )
    filterset_fields = ("status", "delivery_method", "order")


class AdminDeliveryDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminRole]
    lookup_field = "delivery_id"
    queryset = Delivery.objects.select_related("order", "order__user")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return DeliveryUpdateSerializer
        return AdminDeliveryReadSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        delivery = serializer.instance
        if delivery.order.status == OrderStatus.CANCELLED:
            raise serializers.ValidationError(
                {"status": "A cancelled order cannot be shipped."}
            )

        new_status = serializer.validated_data.get("status", delivery.status)
        update_fields = {}
        if new_status == DeliveryStatus.IN_TRANSIT and not delivery.shipped_at:
            update_fields["shipped_at"] = timezone.now()
        if new_status == DeliveryStatus.DELIVERED and not delivery.delivered_at:
            update_fields["delivered_at"] = timezone.now()
        delivery = serializer.save(**update_fields)

        order_status_by_delivery_status = {
            DeliveryStatus.IN_TRANSIT: OrderStatus.SHIPPED,
            DeliveryStatus.OUT_FOR_DELIVERY: OrderStatus.SHIPPED,
            DeliveryStatus.DELIVERED: OrderStatus.DELIVERED,
            DeliveryStatus.FAILED: OrderStatus.FAILED,
            DeliveryStatus.RETURNED: OrderStatus.RETURNED,
        }
        order_status = order_status_by_delivery_status.get(new_status)
        if order_status:
            delivery.order.status = order_status
            delivery.order.save(update_fields=("status", "updated_at"))
