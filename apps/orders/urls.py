from django.urls import path
from .views import (
    AdminOrderListView,
    AdminOrderStatusUpdateView,
    OrderCancelView,
    OrderCheckoutView,
    OrderDetailView,
    OrderListView,
)

app_name = "orders"

urlpatterns = [
    # Customer routes
    path("", OrderListView.as_view(), name="order-list"),
    path("checkout/", OrderCheckoutView.as_view(), name="order-checkout"),
    path("<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:order_id>/cancel/", OrderCancelView.as_view(), name="order-cancel"),

    # Admin routes
    path("admin/all/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("admin/<int:order_id>/status/", AdminOrderStatusUpdateView.as_view(), name="admin-order-status-update"),
]
