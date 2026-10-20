from rest_framework import serializers

from .models import Service, ServiceStatus


class ServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("name", "description", "service_type")


class ServiceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "service_id",
            "name",
            "description",
            "service_type",
            "status",
            "estimated_cost",
            "final_cost",
            "requested_at",
            "completed_at",
        )
        read_only_fields = fields


class AdminServiceReadSerializer(ServiceReadSerializer):
    customer_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(ServiceReadSerializer.Meta):
        fields = ("customer_email",) + ServiceReadSerializer.Meta.fields


class ServiceUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=ServiceStatus.choices, required=False)

    class Meta:
        model = Service
        fields = ("status", "estimated_cost", "final_cost")

    def validate_status(self, value):
        current = self.instance.status
        allowed = {
            ServiceStatus.NEW: {ServiceStatus.IN_PROGRESS, ServiceStatus.CANCELLED},
            ServiceStatus.IN_PROGRESS: {ServiceStatus.COMPLETED, ServiceStatus.CANCELLED},
            ServiceStatus.COMPLETED: set(),
            ServiceStatus.CANCELLED: set(),
        }
        if value != current and value not in allowed[current]:
            raise serializers.ValidationError(
                f"A service request cannot move from {current} to {value}."
            )
        return value
