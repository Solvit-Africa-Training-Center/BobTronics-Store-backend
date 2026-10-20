from django.contrib import admin
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("feedback_id", "user", "product", "rating", "status", "created_at")
    list_filter = ("status", "rating", "created_at")
    search_fields = ("user__email", "product__name", "comment")
    ordering = ("-created_at",)
