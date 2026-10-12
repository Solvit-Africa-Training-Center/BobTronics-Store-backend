from django.contrib import admin
from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 1


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("wishlist_id", "user", "created_at", "updated_at")
    search_fields = ("user__email",)
    inlines = [WishlistItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("wishlist_item_id", "wishlist", "product", "added_at")
    search_fields = ("wishlist__user__email", "product__name")
