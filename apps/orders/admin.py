from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "discount_amount", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "order_date", "status", "total_amount", "phone")
    list_filter = ("status", "order_date")
    search_fields = ("order_id", "user__email", "phone", "shipping_address")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order_item_id", "order", "product", "quantity", "unit_price", "discount_amount", "subtotal")
    search_fields = ("order__order_id", "product__name")
