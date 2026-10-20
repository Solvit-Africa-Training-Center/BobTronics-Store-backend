from django.urls import path

from .api import (
    AdminDeliveryDetailView,
    AdminDeliveryListView,
    CustomerDeliveryDetailView,
    CustomerDeliveryListView,
)

app_name = "deliveries"

urlpatterns = [
    path("", CustomerDeliveryListView.as_view(), name="customer-delivery-list"),
    path("admin/", AdminDeliveryListView.as_view(), name="admin-delivery-list"),
    path(
        "admin/<int:delivery_id>/",
        AdminDeliveryDetailView.as_view(),
        name="admin-delivery-detail",
    ),
    path("<int:delivery_id>/", CustomerDeliveryDetailView.as_view(), name="customer-delivery-detail"),
]
