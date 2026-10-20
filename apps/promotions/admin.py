from django.contrib import admin
from .models import Discount, PromoCode


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("discount_id", "product", "discount_type", "discount_value", "start_date", "end_date", "is_active")
    list_filter = ("discount_type", "is_active", "start_date", "end_date")
    search_fields = ("product__name",)
    list_editable = ("is_active",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "start_date",
        "end_date",
        "usage_count",
        "usage_limit",
        "is_active",
    )
    list_filter = ("discount_type", "is_active", "start_date", "end_date")
    search_fields = ("code",)
    list_editable = ("is_active",)
