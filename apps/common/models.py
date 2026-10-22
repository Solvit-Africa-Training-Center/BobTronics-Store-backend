from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    `created_at` and `updated_at` fields with database indexing.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ContactMessage(TimeStampedModel):
    """
    Contact form submissions sent by authenticated customers to store administrators.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contact_messages",
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=50, blank=True, default="")
    message = models.TextField()
    agree_to_privacy_policy = models.BooleanField(
        default=True,
        help_text="Indicates whether the customer agreed to the privacy policy.",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contact_messages"
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_contact_user_created"),
            models.Index(fields=["is_read", "created_at"], name="idx_contact_read_created"),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{status}] {self.full_name} ({self.email})"

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationType(models.TextChoices):
    ORDER = "order", "Order Update"
    DELIVERY = "delivery", "Delivery Update"
    SERVICE = "service", "Service Request"
    PROMOTION = "promotion", "Promotion & Offers"
    CONTACT = "contact", "Contact & Support"
    SYSTEM = "system", "System Notice"


class NotificationPriority(models.TextChoices):
    INFO = "info", "Information"
    SUCCESS = "success", "Success"
    WARNING = "warning", "Warning"
    ALERT = "alert", "Alert"


class Notification(TimeStampedModel):
    """
    User notifications tracking activities and updates on orders, deliveries,
    services, support messages, and promotions.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.INFO,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Target URL or frontend route to open when notification is clicked.",
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary metadata and complete payload details for frontend rendering.",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"], name="idx_notif_user_read_time"),
            models.Index(fields=["user", "notification_type"], name="idx_notif_user_type"),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{status}] {self.user.email} - {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
