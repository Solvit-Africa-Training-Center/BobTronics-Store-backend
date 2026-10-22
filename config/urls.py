"""URL configuration for the BobTronics Store API."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
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

from apps.accounts.views import GoogleLoginView, LoginView


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


@extend_schema(exclude=True)
class DirectGoogleLoginView(GoogleLoginView):
    pass


@extend_schema(exclude=True)
class DirectLoginView(LoginView):
    pass


from apps.common.views import ContactFormView


@extend_schema(exclude=True)
class DirectContactFormView(ContactFormView):
    pass


urlpatterns = [
    # Convenient redirects to interactive API documentation
    path("", RedirectView.as_view(url="/api/v1/docs/", permanent=False), name="root-docs-redirect"),
    path("docs/", RedirectView.as_view(url="/api/v1/docs/", permanent=False), name="docs-redirect"),
    path("api/docs/", RedirectView.as_view(url="/api/v1/docs/", permanent=False), name="api-docs-redirect"),

    path("admin/", admin.site.urls),

    # Health check
    path("api/v1/health/", health_check, name="health-check"),

    # Authentication routes
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/google/", GoogleLoginView.as_view(), name="auth-google-login"),
    path(
        "api/v1/auth/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh",
    ),

    # Direct auth aliases (for frontend compatibility)
    path("auth/google/", DirectGoogleLoginView.as_view(), name="auth-google-login-direct"),
    path("auth/login/", DirectLoginView.as_view(), name="auth-login-direct"),
    path(
        "auth/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh-direct",
    ),

    # Accounts API
    path("api/v1/accounts/", include("apps.accounts.urls")),

    # Customer Profile & Address API
    path("api/v1/customers/", include("apps.accounts.customer_urls")),

    # Customer service requests and admin service management
    path("api/v1/services/", include("apps.services.urls")),

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

    # Promotional discounts & special offers API
    path("api/v1/promotions/", include("apps.promotions.urls")),

    # Contact Us & Customer Inquiries API
    path("api/v1/contact/", include("apps.common.urls")),
    path("contact/", DirectContactFormView.as_view(), name="contact-submit-direct"),

    # User Notifications API
    path("api/v1/notifications/", include("apps.common.notifications_urls")),
    path("notifications/", include("apps.common.notifications_urls")),

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
