from django.urls import path

from .views import WishlistRemoveView, WishlistView

app_name = "wishlist"

urlpatterns = [
    path("", WishlistView.as_view(), name="wishlist"),
    path("<int:product_id>/", WishlistRemoveView.as_view(), name="wishlist-remove"),
]
