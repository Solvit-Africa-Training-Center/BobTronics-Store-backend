from django.shortcuts import get_object_or_404
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsOwnerOrAdmin
from apps.orders.models import Order
from .models import Delivery
from .serializers import (
    DeliverySerializer,
    DeliveryStatusUpdateSerializer,
    DeliveryTrackingSerializer,
)


class DeliveryPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 50


class OrderDeliveryDetailView(APIView):
    """
    GET: Retrieve delivery tracking details for a specific Order.
    Customers may only view delivery for their own orders; Admins can view any.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        summary="Get Delivery Details for Order",
        description="Returns fulfillment and delivery tracking details for a specific order.",
        responses={
            200: DeliverySerializer,
            404: OpenApiResponse(description="Order or delivery not found"),
        },
        tags=["Deliveries"],
    )
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("user"), order_id=order_id
        )
        self.check_object_permissions(request, order)

        delivery = get_object_or_404(
            Delivery.objects.select_related("order__user"), order=order
        )
        serializer = DeliverySerializer(delivery)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class PublicTrackingView(APIView):
    """
    GET: Publicly track a package by tracking number.
    Does not require authentication so customers can track with SMS/Email links.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Public Package Tracking",
        description="Look up real-time delivery status using a unique tracking number.",
        responses={
            200: DeliveryTrackingSerializer,
            404: OpenApiResponse(description="Tracking number not found"),
        },
        tags=["Deliveries"],
    )
    def get(self, request, tracking_number):
        delivery = get_object_or_404(
            Delivery.objects.select_related("order"),
            tracking_number__iexact=tracking_number.strip(),
        )
        serializer = DeliveryTrackingSerializer(delivery)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class AdminDeliveryListView(generics.ListAPIView):
    """
    GET: List all shipments and deliveries across all orders for shop administrators.
    """

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = DeliverySerializer
    pagination_class = DeliveryPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "delivery_method"]
    search_fields = [
        "tracking_number",
        "order__order_id",
        "order__user__email",
        "order__user__first_name",
        "order__user__last_name",
        "delivery_address",
    ]
    ordering_fields = ["created_at", "shipped_at", "delivered_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Delivery.objects.select_related("order__user").all()

    @extend_schema(
        summary="Admin: List All Deliveries",
        description="Returns paginated list of deliveries with filters for status, method, and search.",
        tags=["Deliveries - Admin"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminDeliveryDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve full delivery information for an admin.
    """

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = DeliverySerializer
    lookup_field = "delivery_id"
    queryset = Delivery.objects.select_related("order__user").all()

    @extend_schema(
        summary="Admin: View Delivery Detail",
        description="Retrieve full shipment and order details for a delivery.",
        tags=["Deliveries - Admin"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Admin: Update Delivery Status / Assignment",
        description="Update delivery status or tracking number.",
        request=DeliveryStatusUpdateSerializer,
        responses={200: DeliverySerializer},
        tags=["Deliveries - Admin"],
    )
    def patch(self, request, *args, **kwargs):
        delivery_id = kwargs.get("delivery_id")
        return AdminDeliveryStatusUpdateView().patch(request, delivery_id=delivery_id)


class AdminDeliveryStatusUpdateView(APIView):
    """
    PATCH: Update shipment status and tracking number.
    """

    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(
        summary="Admin: Update Delivery Status",
        description="Transition shipment status (e.g., PENDING -> IN_TRANSIT -> DELIVERED) and optionally set tracking number.",
        request=DeliveryStatusUpdateSerializer,
        responses={
            200: DeliverySerializer,
            400: OpenApiResponse(description="Invalid status transition or validation error"),
            404: OpenApiResponse(description="Delivery not found"),
        },
        tags=["Deliveries - Admin"],
    )
    def patch(self, request, delivery_id):
        delivery = get_object_or_404(
            Delivery.objects.select_related("order__user"),
            delivery_id=delivery_id,
        )
        serializer = DeliveryStatusUpdateSerializer(
            data=request.data,
            context={"delivery": delivery, "request": request},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated_delivery = serializer.save()
        return Response(
            {
                "success": True,
                "message": f"Delivery status updated to '{updated_delivery.get_status_display()}'.",
                "data": DeliverySerializer(updated_delivery).data,
            },
            status=status.HTTP_200_OK,
        )


class DeliveryFeesView(APIView):
    """
    GET: Return available fulfillment options and standard delivery fee schedule.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get Delivery Fees",
        description="Returns standard shipping fees for delivery methods.",
        tags=["Deliveries"],
    )
    def get(self, request):
        return Response(
            {
                "success": True,
                "data": [
                    {
                        "method": "standard",
                        "name": "Standard Delivery",
                        "fee": "80.00",
                        "estimated_days": "2-3 business days",
                    },
                    {
                        "method": "express",
                        "name": "Express Delivery",
                        "fee": "150.00",
                        "estimated_days": "Same day / Next day",
                    },
                    {
                        "method": "store_pickup",
                        "name": "Store Pick-up",
                        "fee": "0.00",
                        "estimated_days": "Ready in 2 hours",
                    },
                ],
            },
            status=status.HTTP_200_OK,
        )


class AdminCouriersListView(APIView):
    """
    GET: Return available delivery agents / couriers for shipment assignment.
    """

    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(
        summary="Admin: List Couriers",
        description="Returns list of available couriers for assignment dropdown.",
        tags=["Deliveries - Admin"],
    )
    def get(self, request):
        from apps.accounts.models import Role, User

        couriers = (
            User.objects.filter(role__in=[Role.ADMIN, Role.SUPER_ADMIN], is_active=True)
            .values("user_id", "first_name", "last_name", "email", "phone")
        )
        data = [
            {
                "courier_id": c["user_id"],
                "name": f"{c['first_name']} {c['last_name']}".strip() or c["email"],
                "email": c["email"],
                "phone": c["phone"],
                "status": "available",
            }
            for c in couriers
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

