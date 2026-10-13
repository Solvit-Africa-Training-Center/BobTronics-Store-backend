from django.urls import path
from .views import (
    WishlistItemAddView,
    WishlistItemDetailView,
    WishlistMoveToCartView,
    WishlistView,
)

app_name = "wishlist"

urlpatterns = [
    path("", WishlistView.as_view(), name="wishlist-detail"),
    path("items/", WishlistItemAddView.as_view(), name="wishlist-add-item"),
    path("items/<int:product_id>/", WishlistItemDetailView.as_view(), name="wishlist-remove-item"),
    path("items/<int:product_id>/move-to-cart/", WishlistMoveToCartView.as_view(), name="wishlist-move-to-cart"),
]
