from django.contrib import admin

from apps.common.models import ContactMessage, Notification


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email",
        "phone_number",
        "user",
        "is_read",
        "agree_to_privacy_policy",
        "created_at",
    )
    list_filter = ("is_read", "agree_to_privacy_policy", "created_at")
    search_fields = ("full_name", "email", "phone_number", "message", "user__email")
    readonly_fields = (
        "id",
        "user",
        "full_name",
        "email",
        "phone_number",
        "message",
        "agree_to_privacy_policy",
        "is_read",
        "read_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_change_permission(self, request, obj=None):
        # Admin can view/read all messages, but cannot modify customer message content
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "notification_type",
        "priority",
        "is_read",
        "read_at",
        "created_at",
    )
    list_filter = ("notification_type", "priority", "is_read", "created_at")
    search_fields = ("title", "message", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at", "read_at")
    ordering = ("-created_at",)
