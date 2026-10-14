from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("audit_log_id", "user", "action", "entry_type", "entity_id", "ip_address", "created_at")
    list_filter = ("action", "entry_type", "created_at")
    search_fields = ("user__email", "action", "entry_type", "description", "ip_address")
    readonly_fields = ("user", "action", "entry_type", "entity_id", "description", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
