"""URL configuration for the BobTronics Store API."""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import LoginView


@extend_schema(
    operation_id="health_check",
    summary="Health check",
    description="Confirms that the API is responding.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "example": "ok",
                }
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),

    # Health check
    path("api/v1/health/", health_check, name="health-check"),

    # Authentication routes
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path(
        "api/v1/auth/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh",
    ),

    # Accounts API (Member A — registration, logout, current-user etc.)
    path("api/v1/accounts/", include("apps.accounts.urls")),

    # Customer Profile & Address API (Member C — Day 2)
    path("api/v1/customers/", include("apps.accounts.customer_urls")),

    # Admin dashboard, reporting, and store configuration APIs
    path("api/v1/", include("apps.common.urls")),

    # Customer orders and admin order management
    path("api/v1/orders/", include("apps.orders.urls")),

    # Customer delivery tracking and admin fulfillment management
    path("api/v1/deliveries/", include("apps.deliveries.urls")),

    # Customer saved products
    path("api/v1/wishlist/", include("apps.wishlist.urls")),

    # Customer service requests and admin workflow
    path("api/v1/services/", include("apps.services.urls")),

    # Product discounts and admin promo management
    path("api/v1/promotions/", include("apps.promotions.urls")),

    # Customer cart promo validation
    path("api/v1/cart/", include("apps.cart.urls")),

    # Catalog API (public read-only + admin management)
    path("api/v1/catalog/", include("apps.catalog.urls")),

    # Customer reviews and admin moderation
    path("api/v1/reviews/", include("apps.reviews.urls")),

    # OpenAPI Schema & Interactive Documentation
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
        ),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
