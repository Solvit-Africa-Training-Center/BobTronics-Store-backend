from django.contrib import admin
from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("delivery_id", "order", "delivery_method", "tracking_number", "status", "shipping_fee", "shipped_at", "delivered_at")
    list_filter = ("status", "delivery_method", "created_at")
    search_fields = ("tracking_number", "order__order_id", "delivery_address")
