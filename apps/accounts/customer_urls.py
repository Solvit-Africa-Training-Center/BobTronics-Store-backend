from django.urls import path

from .customer_views import (
    AdminCustomerDetailView,
    AdminCustomerListView,
    CustomerAddressView,
    CustomerProfileView,
)

app_name = "customers"

urlpatterns = [
    # Customer Self-Service APIs
    path("profile/", CustomerProfileView.as_view(), name="customer-profile"),
    path("address/", CustomerAddressView.as_view(), name="customer-address"),

    # Administrative Customer Management APIs
    path("", AdminCustomerListView.as_view(), name="customer-list"),
    path("<int:user_id>/", AdminCustomerDetailView.as_view(), name="customer-detail"),
]
