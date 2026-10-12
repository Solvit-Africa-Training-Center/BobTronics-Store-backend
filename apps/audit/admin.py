from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("audit_log_id", "user", "action", "entity_type", "entity_id", "ip_address", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("user__email", "action", "entity_type", "description", "ip_address")
    readonly_fields = ("user", "action", "entity_type", "entity_id", "description", "ip_address", "created_at")
