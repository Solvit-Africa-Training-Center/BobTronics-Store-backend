from django.urls import path

from .views import CartItemDetailView, CartView, PromoValidationView

app_name = "cart"

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/<int:cart_item_id>/", CartItemDetailView.as_view(), name="cart-item"),
    path("apply-promo/", PromoValidationView.as_view(), name="apply-promo"),
    # Backwards-compatible alias for the path also probed by the frontend.
    path("promo/", PromoValidationView.as_view(), name="promo"),
]
