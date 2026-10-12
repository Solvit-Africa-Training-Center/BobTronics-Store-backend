from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "order", "amount", "payment_method", "transaction_reference", "status", "payment_date")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("transaction_reference", "order__order_id", "order__user__email")
    readonly_fields = ("created_at", "updated_at")
