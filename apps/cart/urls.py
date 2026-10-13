from django.urls import path
from .views import CartClearView, CartItemAddView, CartItemDetailView, CartView

app_name = "cart"

urlpatterns = [
    path("", CartView.as_view(), name="cart-summary"),
    path("items/", CartItemAddView.as_view(), name="cart-add-item"),
    path("items/<int:cart_item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("clear/", CartClearView.as_view(), name="cart-clear"),
]
