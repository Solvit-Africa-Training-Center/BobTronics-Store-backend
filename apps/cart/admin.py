from django.contrib import admin
from .models import CartItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart_item_id", "user", "product", "quantity", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__email", "product__name")
