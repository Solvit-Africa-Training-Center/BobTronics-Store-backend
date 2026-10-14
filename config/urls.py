"""URL configuration for the BobTronics Store API."""

from django.contrib import admin
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

    # Accounts API
    path("api/v1/accounts/", include("apps.accounts.urls")),

    # Customer Profile & Address API
    path("api/v1/customers/", include("apps.accounts.customer_urls")),

    # Catalog API (public read-only + admin management)
    path("api/v1/catalog/", include("apps.catalog.urls")),

    # Shopping Cart API
    path("api/v1/cart/", include("apps.cart.urls")),

    # Wishlist API
    path("api/v1/wishlist/", include("apps.wishlist.urls")),

    # Orders & Checkout API
    path("api/v1/orders/", include("apps.orders.urls")),

    # Deliveries & Shipment Tracking API
    path("api/v1/deliveries/", include("apps.deliveries.urls")),

    # Product feedback (verified delivered purchases)
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
