from django.contrib import admin
from .models import Payment
from apps.audit.services import log_audit_event


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "order", "amount", "payment_method", "transaction_reference", "status", "payment_date")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("transaction_reference", "order__order_id", "order__user__email")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = Payment.objects.filter(pk=obj.pk).values_list("status", flat=True).first()

        super().save_model(request, obj, form, change)

        if previous_status is None:
            log_audit_event(
                action="payment.created",
                entry_type="Payment",
                entity_id=obj.payment_id,
                user=request.user,
                description=f"Payment record created with status {obj.status}.",
                request=request,
            )
        elif previous_status != obj.status:
            log_audit_event(
                action="payment.status_changed",
                entry_type="Payment",
                entity_id=obj.payment_id,
                user=request.user,
                description=f"Payment status changed from {previous_status} to {obj.status}.",
                request=request,
            )
