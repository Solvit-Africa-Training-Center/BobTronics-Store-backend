from django.contrib import admin

from apps.common.models import ContactMessage, Notification


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "subject",
        "status",
        "attachment",
        "agreed_to_privacy_policy",
        "user",
        "created_at",
    )
    list_filter = ("status", "agreed_to_privacy_policy", "created_at")
    search_fields = ("name", "email", "subject", "message", "phone")
    readonly_fields = (
        "name",
        "email",
        "phone",
        "subject",
        "message",
        "attachment",
        "agreed_to_privacy_policy",
        "user",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    fieldsets = (
        ("Inquiry Details", {
            "fields": (
                "name",
                "email",
                "phone",
                "subject",
                "message",
                "attachment",
                "agreed_to_privacy_policy",
                "user",
            )
        }),
        ("Admin Review", {
            "fields": ("status", "admin_notes", "replied_at")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


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
