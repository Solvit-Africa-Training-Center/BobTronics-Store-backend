from django.urls import path
from .views import (
    AdminDeliveryDetailView,
    AdminDeliveryListView,
    AdminDeliveryStatusUpdateView,
    OrderDeliveryDetailView,
    PublicTrackingView,
)

app_name = "deliveries"

urlpatterns = [
    # Customer / Public tracking routes
    path("orders/<int:order_id>/", OrderDeliveryDetailView.as_view(), name="order-delivery"),
    path("track/<str:tracking_number>/", PublicTrackingView.as_view(), name="public-tracking"),

    # Admin routes
    path("admin/all/", AdminDeliveryListView.as_view(), name="admin-delivery-list"),
    path("admin/<int:delivery_id>/", AdminDeliveryDetailView.as_view(), name="admin-delivery-detail"),
    path("admin/<int:delivery_id>/status/", AdminDeliveryStatusUpdateView.as_view(), name="admin-delivery-status-update"),
]
