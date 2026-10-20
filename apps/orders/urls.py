from django.urls import path

from .api import (
    AdminOrderDetailView,
    AdminOrderListView,
    CustomerCancelOrderView,
    CustomerOrderDetailView,
    CustomerOrderListCreateView,
)

app_name = "orders"

urlpatterns = [
    path("", CustomerOrderListCreateView.as_view(), name="customer-order-list-create"),
    path("admin/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("admin/<int:order_id>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("<int:order_id>/cancel/", CustomerCancelOrderView.as_view(), name="customer-order-cancel"),
    path("<int:order_id>/", CustomerOrderDetailView.as_view(), name="customer-order-detail"),
]
