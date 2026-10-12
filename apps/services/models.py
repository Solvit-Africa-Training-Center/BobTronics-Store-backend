from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ServiceType(models.TextChoices):
    HARDWARE_MAINTENANCE = "hardware_maintenance", "Hardware Repair & Maintenance"
    SOFTWARE_TROUBLESHOOTING = "software_troubleshooting", "Software Troubleshooting"
    NETWORK_INFRASTRUCTURE = "network_infrastructure", "Network Setup & Infrastructure"
    IT_CONSULTANCY = "it_consultancy", "IT Consultancy & Strategic Advice"
    PROJECT_MANAGEMENT = "project_management", "IT Project Management"
    OTHER = "other", "Other Electronic Service"


class ServiceStatus(models.TextChoices):
    NEW = "new", "New"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class Service(models.Model):
    """
    IT Consultancy and hardware/software service requests.
    """

    service_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="services",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    service_type = models.CharField(
        max_length=50,
        choices=ServiceType.choices,
        default=ServiceType.IT_CONSULTANCY,
    )
    status = models.CharField(
        max_length=30,
        choices=ServiceStatus.choices,
        default=ServiceStatus.NEW,
        db_index=True,
    )
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    final_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services"
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["status", "service_type"], name="idx_service_status_type"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()}) - {self.get_status_display()}"
