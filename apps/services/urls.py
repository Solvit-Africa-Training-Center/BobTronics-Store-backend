from django.urls import path

from .views import (
    AdminServiceDetailView,
    AdminServiceListView,
    CustomerCancelServiceView,
    CustomerServiceDetailView,
    CustomerServiceListCreateView,
)

app_name = "services"

urlpatterns = [
    path("", CustomerServiceListCreateView.as_view(), name="customer-service-list-create"),
    path("admin/", AdminServiceListView.as_view(), name="admin-service-list"),
    path("admin/<int:service_id>/", AdminServiceDetailView.as_view(), name="admin-service-detail"),
    path("<int:service_id>/cancel/", CustomerCancelServiceView.as_view(), name="customer-service-cancel"),
    path("<int:service_id>/", CustomerServiceDetailView.as_view(), name="customer-service-detail"),
]
