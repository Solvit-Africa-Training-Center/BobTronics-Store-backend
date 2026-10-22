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


class ContactStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READ = "read", "Read"
    REPLIED = "replied", "Replied"
    ARCHIVED = "archived", "Archived"


class ContactMessage(TimeStampedModel):
    """
    Contact form submissions sent by visitors and customers to the store admin.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, default="")
    subject = models.CharField(max_length=255, default="General Inquiry")
    message = models.TextField()
    attachment = models.FileField(
        upload_to="contact_attachments/",
        null=True,
        blank=True,
        help_text="Optional document or screenshot attachment.",
    )
    agreed_to_privacy_policy = models.BooleanField(
        default=True,
        help_text="Indicates whether sender consented to privacy policy.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
    )
    status = models.CharField(
        max_length=20,
        choices=ContactStatus.choices,
        default=ContactStatus.PENDING,
        db_index=True,
    )
    admin_notes = models.TextField(blank=True, default="")
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contact_messages"
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_contact_status_created"),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name} - {self.subject}"


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


