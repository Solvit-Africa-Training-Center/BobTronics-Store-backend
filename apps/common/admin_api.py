import csv
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.reviews.models import Feedback, ReviewStatus

from .models import StoreSettings


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = (
            "store_name",
            "contact_email",
            "contact_phone",
            "currency",
            "standard_delivery_fee",
            "express_delivery_fee",
            "low_stock_threshold",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class ReportDateFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        start = attrs.get("date_from")
        end = attrs.get("date_to")
        if start and end and start > end:
            raise serializers.ValidationError(
                {"date_to": "End date must be on or after the start date."}
            )
        return attrs


class AdminNotificationSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    resource_id = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class AdminNotificationsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = AdminNotificationSerializer(many=True)


class ReportOrderStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class ReportTopProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    quantity_sold = serializers.IntegerField()
    order_count = serializers.IntegerField()


class ReportSummarySerializer(serializers.Serializer):
    filters = ReportDateFilterSerializer()
    order_count = serializers.IntegerField()
    order_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    order_status_counts = ReportOrderStatusSerializer(many=True)
    top_products = ReportTopProductSerializer(many=True)
    currency = serializers.CharField()


def _filtered_orders(params):
    query = Order.objects.select_related("user").exclude(
        status=OrderStatus.CANCELLED
    )
    if params.get("date_from"):
        query = query.filter(order_date__date__gte=params["date_from"])
    if params.get("date_to"):
        query = query.filter(order_date__date__lte=params["date_to"])
    return query


def _validated_date_filters(request):
    serializer = ReportDateFilterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class AdminNotificationsView(generics.GenericAPIView):
    """Return current operational alerts assembled from existing store records."""

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminNotificationsResponseSerializer

    def get(self, request, *args, **kwargs):
        settings, _ = StoreSettings.objects.get_or_create(pk=1)
        alerts = []

        pending_orders = (
            Order.objects.filter(status=OrderStatus.PENDING)
            .select_related("user")
            .order_by("-order_date")[:50]
        )
        for order in pending_orders:
            alerts.append(
                {
                    "type": "pending_order",
                    "title": "Order needs review",
                    "message": f"Order #{order.order_id} is awaiting confirmation.",
                    "resource_id": order.order_id,
                    "created_at": order.order_date,
                }
            )

        pending_reviews = (
            Feedback.objects.filter(status=ReviewStatus.PENDING)
            .select_related("product")
            .order_by("-created_at")[:50]
        )
        for review in pending_reviews:
            alerts.append(
                {
                    "type": "pending_review",
                    "title": "Review needs moderation",
                    "message": f"A review for {review.product.name} is awaiting approval.",
                    "resource_id": review.feedback_id,
                    "created_at": review.created_at,
                }
            )

        low_stock = Product.objects.filter(
            is_available=True,
            stock_quantity__lte=settings.low_stock_threshold,
        ).order_by("stock_quantity", "name")[:50]
        for product in low_stock:
            alerts.append(
                {
                    "type": "low_stock",
                    "title": "Product stock is low",
                    "message": f"{product.name} has {product.stock_quantity} left.",
                    "resource_id": product.product_id,
                    "created_at": product.updated_at,
                }
            )

        alerts.sort(key=lambda item: item["created_at"], reverse=True)
        for alert in alerts:
            alert["created_at"] = alert["created_at"].isoformat()
        return Response({"count": len(alerts), "results": alerts})


class AdminReportSummaryView(generics.GenericAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = ReportSummarySerializer

    @extend_schema(parameters=[ReportDateFilterSerializer])
    def get(self, request, *args, **kwargs):
        params = _validated_date_filters(request)
        orders = _filtered_orders(params)
        totals = orders.aggregate(revenue=Sum("total_amount"))
        order_items = OrderItem.objects.filter(order__in=orders)
        top_products = (
            order_items.values("product_id")
            .annotate(product_name=F("product__name"))
            .annotate(quantity_sold=Sum("quantity"), order_count=Count("order_id", distinct=True))
            .order_by("-quantity_sold", "product_name")[:5]
        )
        store_settings, _ = StoreSettings.objects.get_or_create(pk=1)
        return Response(
            {
                "filters": {
                    key: value.isoformat()
                    for key, value in params.items()
                },
                "order_count": orders.count(),
                "order_value": str(totals["revenue"] or Decimal("0.00")),
                "order_status_counts": list(
                    orders.values("status").annotate(count=Count("order_id")).order_by("status")
                ),
                "top_products": list(top_products),
                "currency": store_settings.currency,
            }
        )


class AdminReportExportView(generics.GenericAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = ReportDateFilterSerializer

    @extend_schema(
        parameters=[ReportDateFilterSerializer],
        responses={
            (200, "text/csv"): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="CSV export of non-cancelled orders.",
            )
        },
    )
    def get(self, request, *args, **kwargs):
        params = _validated_date_filters(request)
        orders = _filtered_orders(params).order_by("order_date", "order_id")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="orders-report.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ("order_id", "order_date", "status", "customer_email", "order_value")
        )
        for order in orders:
            writer.writerow(
                (
                    order.order_id,
                    order.order_date.isoformat(),
                    order.status,
                    order.user.email,
                    order.total_amount,
                )
            )
        return response


class AdminStoreSettingsView(generics.GenericAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        settings, _ = StoreSettings.objects.get_or_create(pk=1)
        return settings

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
