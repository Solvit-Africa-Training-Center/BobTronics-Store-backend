from rest_framework.routers import DefaultRouter

from .api_views import DiscountAdminViewSet

router = DefaultRouter()
router.register("admin/discounts", DiscountAdminViewSet, basename="admin-discount")
urlpatterns = router.urls
