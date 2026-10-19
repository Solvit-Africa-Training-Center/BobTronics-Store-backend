from decimal import Decimal
from django.db.models import Sum
from rest_framework import serializers

from apps.accounts.models import User
from apps.orders.models import Order


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Detailed profile serializer for authenticated customer.
    Computes lifetime statistics (total_orders, total_spent) via database aggregations.
    """

    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "residence",
            "role",
            "total_orders",
            "total_spent",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user_id",
            "email",
            "role",
            "total_orders",
            "total_spent",
            "created_at",
            "updated_at",
        )

    def get_total_orders(self, obj) -> int:
        if hasattr(obj, "total_orders_count"):
            return obj.total_orders_count
        return obj.orders.count()

    def get_total_spent(self, obj) -> str:
        if hasattr(obj, "total_spent_amount") and obj.total_spent_amount is not None:
            return f"{obj.total_spent_amount:.2f}"
        total = obj.orders.exclude(status="cancelled").aggregate(total=Sum("total_amount"))["total"]
        if total is None:
            return "0.00"
        return f"{total:.2f}"


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer to safely update customer personal info and address.
    Strictly forbids altering security-critical fields (email, role, is_active).
    """

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    residence = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "residence")

    def validate_first_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("First name cannot be blank.")
        return stripped

    def validate_last_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Last name cannot be blank.")
        return stripped

    def validate_phone(self, value):
        return value.strip()

    def validate_residence(self, value):
        return value.strip()


class CustomerAddressSerializer(serializers.ModelSerializer):
    """
    Lightweight address serializer for checking and updating primary delivery location.
    """

    residence = serializers.CharField(max_length=255, required=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("residence", "phone")

    def validate_residence(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Residence address cannot be blank.")
        return stripped


class CustomerRecentOrderSerializer(serializers.ModelSerializer):
    """
    Lightweight order snapshot embedded inside admin customer detail view.
    """

    class Meta:
        model = Order
        fields = ("order_id", "order_date", "status", "total_amount", "created_at")


class AdminCustomerListSerializer(serializers.ModelSerializer):
    """
    Memory-efficient serializer for administrative customer directory.
    Uses annotated total_orders from queryset to prevent N+1 queries.
    """

    total_orders = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "residence",
            "role",
            "is_active",
            "last_login",
            "total_orders",
            "created_at",
        )


class AdminCustomerDetailSerializer(serializers.ModelSerializer):
    """
    Detailed administrative view of customer with order summary and recent orders.
    """

    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    recent_orders = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "residence",
            "role",
            "is_active",
            "last_login",
            "total_orders",
            "total_spent",
            "recent_orders",
            "created_at",
            "updated_at",
        )

    def get_total_orders(self, obj) -> int:
        """Uses annotated count from queryset to avoid extra DB query."""
        if hasattr(obj, "total_orders_count"):
            return obj.total_orders_count
        return obj.orders.count()

    def get_total_spent(self, obj) -> str:
        """Uses annotated sum from queryset to avoid extra DB query."""
        if hasattr(obj, "total_spent_amount") and obj.total_spent_amount is not None:
            return f"{obj.total_spent_amount:.2f}"
        total = obj.orders.exclude(status="cancelled").aggregate(total=Sum("total_amount"))["total"]
        return f"{total:.2f}" if total is not None else "0.00"

    def get_recent_orders(self, obj):
        """Uses prefetched orders (set by view) to avoid extra DB query."""
        if hasattr(obj, "prefetched_orders"):
            recent = obj.prefetched_orders[:10]
        else:
            recent = obj.orders.order_by("-order_date")[:10]
        return CustomerRecentOrderSerializer(recent, many=True).data
