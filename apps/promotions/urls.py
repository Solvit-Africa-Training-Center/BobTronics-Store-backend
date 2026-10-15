from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    ActivePromotionsListView,
    DiscountAdminViewSet,
    ProductDiscountView,
)

router = DefaultRouter()
router.register("admin/discounts", DiscountAdminViewSet, basename="admin-discount")

urlpatterns = [
    path("active/", ActivePromotionsListView.as_view(), name="promotions-active"),
    path(
        "products/<int:product_id>/",
        ProductDiscountView.as_view(),
        name="promotions-product-discount",
    ),
] + router.urls
