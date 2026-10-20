from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActiveDiscountListView, AdminDiscountViewSet, AdminPromoCodeViewSet

router = DefaultRouter()
router.register("admin/discounts", AdminDiscountViewSet, basename="admin-discount")
router.register("admin/codes", AdminPromoCodeViewSet, basename="admin-promo-code")

app_name = "promotions"

urlpatterns = [
    path("", ActiveDiscountListView.as_view(), name="active-discounts"),
    path("", include(router.urls)),
]
