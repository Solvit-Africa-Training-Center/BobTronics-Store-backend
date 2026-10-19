from django.urls import path
from .views import (
    AdminCouriersListView,
    AdminDeliveryDetailView,
    AdminDeliveryListView,
    AdminDeliveryStatusUpdateView,
    DeliveryFeesView,
    OrderDeliveryDetailView,
    PublicTrackingView,
)

app_name = "deliveries"

urlpatterns = [
    # Customer / Public tracking routes
    path("fees/", DeliveryFeesView.as_view(), name="delivery-fees"),
    path("orders/<int:order_id>/", OrderDeliveryDetailView.as_view(), name="order-delivery"),
    path("track/<str:tracking_number>/", PublicTrackingView.as_view(), name="public-tracking"),

    # Admin routes
    path("admin/", AdminDeliveryListView.as_view(), name="admin-delivery-list-root"),
    path("admin/all/", AdminDeliveryListView.as_view(), name="admin-delivery-list"),
    path("admin/couriers/", AdminCouriersListView.as_view(), name="admin-couriers-list"),
    path("admin/<int:delivery_id>/", AdminDeliveryDetailView.as_view(), name="admin-delivery-detail"),
    path("admin/<int:delivery_id>/status/", AdminDeliveryStatusUpdateView.as_view(), name="admin-delivery-status-update"),
]
