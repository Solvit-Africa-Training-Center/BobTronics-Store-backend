from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer
from apps.catalog.stock_service import StockError, deduct_stock, restore_stock
from apps.common.permissions import IsAdminRole
from apps.common.models import StoreSettings
from apps.cart.models import CartItem
from apps.deliveries.models import Delivery, DeliveryMethod
from apps.promotions.models import DiscountType, PromoCode

from .models import Order, OrderItem, OrderStatus
from .serializers import (
    AdminOrderReadSerializer,
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusUpdateSerializer,
)


class CustomerOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("user", "delivery")
            .prefetch_related("items__product")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderReadSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = data["items"]
        line_amounts = [
            line["product"].price * line["quantity"] for line in items
        ]
        subtotal = sum(line_amounts, Decimal("0.00")).quantize(Decimal("0.01"))
        promo = None
        promo_discount = Decimal("0.00")
        promo_code = data.get("promo_code", "")
        if promo_code:
            promo = PromoCode.objects.select_for_update().filter(code=promo_code).first()
            today = timezone.localdate()
            if (
                promo is None
                or not promo.is_active
                or today < promo.start_date
                or today > promo.end_date
                or (promo.usage_limit is not None and promo.usage_count >= promo.usage_limit)
            ):
                raise serializers.ValidationError(
                    {"promo_code": "This promo code is not available."}
                )
            if subtotal < promo.minimum_order_amount:
                raise serializers.ValidationError(
                    {"promo_code": "Your order does not meet this promo's minimum spend."}
                )
            if promo.discount_type == DiscountType.PERCENTAGE:
                if promo.discount_value > 100:
                    raise serializers.ValidationError(
                        {"promo_code": "This promo code is configured incorrectly."}
                    )
                promo_discount = subtotal * promo.discount_value / Decimal("100")
            else:
                promo_discount = promo.discount_value
            promo_discount = min(promo_discount, subtotal).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        stock_items = [(line["product"].pk, line["quantity"]) for line in items]
        try:
            deduct_stock(stock_items)
        except StockError as exc:
            raise serializers.ValidationError({"items": str(exc)}) from exc

        store_settings, _ = StoreSettings.objects.get_or_create(pk=1)
        if data["delivery_method"] == DeliveryMethod.EXPRESS:
            shipping_fee = store_settings.express_delivery_fee
        elif data["delivery_method"] == DeliveryMethod.STANDARD:
            shipping_fee = store_settings.standard_delivery_fee
        else:
            shipping_fee = Decimal("0.00")

        order = Order.objects.create(
            user=request.user,
            status=OrderStatus.PENDING,
            total_amount=subtotal - promo_discount + shipping_fee,
            promo_code=promo.code if promo else "",
            promo_discount_amount=promo_discount,
            shipping_address=data["shipping_address"],
            phone=data["phone"],
        )
        remaining_discount = promo_discount
        order_items = []
        for index, (line, gross_amount) in enumerate(zip(items, line_amounts)):
            if not promo or not promo_discount:
                line_discount = Decimal("0.00")
            elif index == len(items) - 1:
                line_discount = remaining_discount
            else:
                line_discount = min(
                    remaining_discount,
                    (promo_discount * gross_amount / subtotal).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                )
            remaining_discount -= line_discount
            order_items.append(
                OrderItem(
                    order=order,
                    product=line["product"],
                    quantity=line["quantity"],
                    unit_price=line["product"].price,
                    discount_amount=line_discount,
                    subtotal=gross_amount - line_discount,
                )
            )
        OrderItem.objects.bulk_create(
            order_items
        )
        Delivery.objects.create(
            order=order,
            delivery_address=data["shipping_address"],
            delivery_method=data["delivery_method"],
            shipping_fee=shipping_fee,
        )
        if promo:
            promo.usage_count += 1
            promo.save(update_fields=("usage_count", "updated_at"))
        CartItem.objects.filter(
            user=request.user,
            product_id__in=[line["product"].pk for line in items],
        ).delete()
        return Response(OrderReadSerializer(order).data, status=201)


class CustomerOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderReadSerializer
    permission_classes = [IsCustomer]
    lookup_field = "order_id"

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("delivery")
            .prefetch_related("items__product")
        )


class CustomerCancelOrderView(APIView):
    permission_classes = [IsCustomer]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_for_update().prefetch_related("items"),
            order_id=order_id,
            user=request.user,
        )
        if order.status != OrderStatus.PENDING:
            raise serializers.ValidationError(
                {"status": "Only pending orders can be cancelled."}
            )
        restore_stock(
            [(item.product_id, item.quantity) for item in order.items.all()]
        )
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=("status", "updated_at"))
        return Response({"message": "Order cancelled."})


class AdminOrderListView(generics.ListAPIView):
    serializer_class = AdminOrderReadSerializer
    permission_classes = [IsAdminRole]
    queryset = (
        Order.objects.select_related("user", "delivery")
        .prefetch_related("items__product")
        .order_by("-order_date")
    )
    filterset_fields = ("status", "user")


class AdminOrderDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminRole]
    lookup_field = "order_id"
    queryset = Order.objects.select_related("user", "delivery").prefetch_related(
        "items__product"
    )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return OrderStatusUpdateSerializer
        return AdminOrderReadSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        order = Order.objects.select_for_update().get(pk=serializer.instance.pk)
        new_status = serializer.validated_data["status"]
        if order.status == OrderStatus.CANCELLED and new_status != OrderStatus.CANCELLED:
            raise serializers.ValidationError(
                {"status": "Cancelled orders cannot be reopened."}
            )
        if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
            restore_stock(
                [(item.product_id, item.quantity) for item in order.items.all()]
            )
        serializer.save()
