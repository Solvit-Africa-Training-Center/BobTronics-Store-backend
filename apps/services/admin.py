from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("service_id", "name", "user", "service_type", "status", "estimated_cost", "final_cost", "requested_at")
    list_filter = ("status", "service_type", "requested_at")
    search_fields = ("name", "user__email", "description")
    ordering = ("-requested_at",)
