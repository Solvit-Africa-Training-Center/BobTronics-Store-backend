from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Service, ServiceStatus, ServiceType


class ServiceCreateSerializer(serializers.ModelSerializer):
    """Fields a customer may provide when requesting a service."""

    class Meta:
        model = Service
        fields = ["name", "description", "service_type"]


class ServiceSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    service_type_display = serializers.CharField(
        source="get_service_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Service
        fields = [
            "service_id",
            "user_id",
            "customer_email",
            "name",
            "description",
            "service_type",
            "service_type_display",
            "status",
            "status_display",
            "estimated_cost",
            "final_cost",
            "requested_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminServiceUpdateSerializer(serializers.ModelSerializer):
    """Admin-only fields for managing a service request."""

    status = serializers.ChoiceField(choices=ServiceStatus.choices, required=False)
    estimated_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    final_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Service
        fields = ["status", "estimated_cost", "final_cost"]

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide a status or cost to update.")

        current = self.instance.status
        new_status = attrs.get("status", current)
        allowed_transitions = {
            ServiceStatus.NEW: {ServiceStatus.IN_PROGRESS, ServiceStatus.CANCELLED},
            ServiceStatus.IN_PROGRESS: {
                ServiceStatus.COMPLETED,
                ServiceStatus.CANCELLED,
            },
            ServiceStatus.COMPLETED: set(),
            ServiceStatus.CANCELLED: set(),
        }
        if new_status != current and new_status not in allowed_transitions[current]:
            raise serializers.ValidationError(
                {
                    "status": (
                        f"A service request cannot move from '{current}' to "
                        f"'{new_status}'."
                    )
                }
            )

        final_cost = attrs.get("final_cost")
        if final_cost is not None and new_status != ServiceStatus.COMPLETED:
            raise serializers.ValidationError(
                {"final_cost": "Final cost can only be set when the request is completed."}
            )
        return attrs

    def update(self, instance, validated_data):
        if (
            validated_data.get("status") == ServiceStatus.COMPLETED
            and instance.status != ServiceStatus.COMPLETED
        ):
            validated_data["completed_at"] = timezone.now()
        return super().update(instance, validated_data)
