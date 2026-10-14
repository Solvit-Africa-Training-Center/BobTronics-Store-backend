from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import (
    CategoryAdminViewSet,
    ProductAdminViewSet,
    ProductImageAdminViewSet,
)
from .views import CategoryViewSet, ProductViewSet

router = DefaultRouter()

# Public, read-only
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

# Admin only
router.register("admin/categories", CategoryAdminViewSet, basename="admin-category")
router.register("admin/products", ProductAdminViewSet, basename="admin-product")
router.register("admin/images", ProductImageAdminViewSet, basename="admin-image")

urlpatterns = [
    path("", include(router.urls)),
    path("", include("apps.promotions.urls")),
]
