from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.cart.models import CartItem
from apps.catalog.stock_service import (
    StockError,
    deduct_stock,
    restore_stock,
)
from .models import Order, OrderItem, OrderStatus
from .serializers import (
    AdminOrderStatusUpdateSerializer,
    OrderCheckoutSerializer,
    OrderListSerializer,
    OrderSerializer,
)


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class OrderCheckoutView(APIView):
    """
    POST: Place an order from the items currently in the authenticated user's cart.
    Atomically validates stock, decrements inventory, creates the order and line items,
    and clears the customer's cart.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Checkout Shopping Cart",
        description="Creates an order from current cart items, atomically reserves inventory, and clears the cart.",
        request=OrderCheckoutSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Empty cart, invalid address/phone, or insufficient stock"),
        },
    )
    def post(self, request):
        serializer = OrderCheckoutSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        shipping_address = serializer.validated_data["shipping_address"]
        phone = serializer.validated_data["phone"]

        with transaction.atomic():
            cart_items = list(
                CartItem.objects.filter(user=request.user)
                .select_related("product")
                .select_for_update()
            )

            if not cart_items:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "status_code": 400,
                            "message": "Your cart is empty. Add products before placing an order.",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 1. Prepare items for stock reservation
            items_to_deduct = [
                (item.product_id, item.quantity) for item in cart_items
            ]

            try:
                deduct_stock(items_to_deduct)
            except StockError as exc:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "status_code": 400,
                            "message": str(exc),
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 2. Calculate totals using product price snapshot
            total_amount = sum(
                (item.product.price * item.quantity for item in cart_items),
                Decimal("0.00"),
            )

            # 3. Create the Order record
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                phone=phone,
                total_amount=total_amount,
                status=OrderStatus.PENDING,
            )

            # 4. Create immutable line items snapshot
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    discount_amount=Decimal("0.00"),
                    subtotal=(item.product.price * item.quantity),
                )
                for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            # 5. Clear cart
            CartItem.objects.filter(user=request.user).delete()

        # Reload with prefetched relationships
        order = (
            Order.objects.prefetch_related("items__product__category")
            .select_related("user")
            .get(pk=order.pk)
        )

        return Response(
            {
                "success": True,
                "message": "Order placed successfully. Inventory has been updated.",
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(APIView):
    """
    GET: List all orders placed by the authenticated customer.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    @extend_schema(
        summary="List Customer Orders",
        description="Returns paginated list of all orders belonging to the authenticated customer.",
        responses={200: OrderListSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .select_related("user")
            .order_by("-order_date")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class OrderDetailView(APIView):
    """
    GET: View full details of a specific order.
    Customers may only view their own orders; Admins can view any order.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="View Order Details",
        description="Returns full information and line items for a specific order.",
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(description="Order not found"),
        },
    )
    def get(self, request, order_id):
        order_qs = (
            Order.objects.prefetch_related("items__product__category")
            .select_related("user")
        )

        # Allow access if owner or admin
        if request.user.role in ["admin", "super_admin"] or request.user.is_staff:
            order = get_object_or_404(order_qs, order_id=order_id)
        else:
            order = get_object_or_404(order_qs, order_id=order_id, user=request.user)

        return Response(
            {
                "success": True,
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )


class OrderCancelView(APIView):
    """
    POST: Cancel an order that is still in PENDING or CONFIRMED status.
    Atomically restores inventory for all items in the order.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel Order",
        description="Cancels an order if eligible and restores inventory back to the catalog.",
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Order cannot be cancelled in current status"),
        },
    )
    def post(self, request, order_id):
        order_qs = Order.objects.prefetch_related("items")
        if request.user.role in ["admin", "super_admin"] or request.user.is_staff:
            order = get_object_or_404(order_qs, order_id=order_id)
        else:
            order = get_object_or_404(order_qs, order_id=order_id, user=request.user)

        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            return Response(
                {
                    "success": False,
                    "error": {
                        "status_code": 400,
                        "message": f"Order #{order_id} cannot be cancelled because it is already '{order.get_status_display()}'.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # 1. Restore stock
            items_to_restore = [
                (item.product_id, item.quantity) for item in order.items.all()
            ]
            restore_stock(items_to_restore)

            # 2. Update status
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": f"Order #{order_id} has been cancelled and stock has been restored.",
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Admin Order Views
# ---------------------------------------------------------------------------


class AdminOrderListView(APIView):
    """
    GET: Admin list of all orders across the store with optional status filtering.
    """

    permission_classes = [IsAdminOrSuperAdmin]
    pagination_class = OrderPagination

    @extend_schema(
        summary="Admin List All Orders",
        description="Admin endpoint to list all orders with optional ?status= filtering.",
        responses={200: OrderListSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            Order.objects.prefetch_related("items")
            .select_related("user")
            .order_by("-order_date")
        )

        # Status filter
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.lower())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminOrderStatusUpdateView(APIView):
    """
    PATCH: Admin endpoint to transition order status (e.g. processing -> shipped -> delivered).
    """

    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(
        summary="Admin Update Order Status",
        description="Admin endpoint to update the status of an order.",
        request=AdminOrderStatusUpdateSerializer,
        responses={200: OrderSerializer},
    )
    def patch(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__product__category").select_related("user"),
            order_id=order_id,
        )
        serializer = AdminOrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]

        # If transitioning to CANCELLED from non-cancelled status, restore stock
        if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
            with transaction.atomic():
                items_to_restore = [
                    (item.product_id, item.quantity) for item in order.items.all()
                ]
                restore_stock(items_to_restore)
                order.status = OrderStatus.CANCELLED
                order.save(update_fields=["status", "updated_at"])
        else:
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": f"Order #{order_id} status updated to '{order.get_status_display()}'.",
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )
