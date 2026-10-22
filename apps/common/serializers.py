from rest_framework import serializers

from apps.common.models import ContactMessage, Notification


class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for contact messages.
    Allows authenticated customers to create, view, update, and manage their contact messages.
    """

    full_name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        help_text="Full name of the sender.",
    )
    email = serializers.EmailField(
        trim_whitespace=True,
        help_text="Email address of the sender.",
    )
    phone_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
        help_text="Phone number of the sender.",
    )
    message = serializers.CharField(
        trim_whitespace=True,
        min_length=5,
        help_text="Message text (minimum 5 characters).",
    )
    agree_to_privacy_policy = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Indicates whether the customer agrees to the privacy policy.",
    )

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "message",
            "agree_to_privacy_policy",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]

    def validate_message(self, value):
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError("Message must contain at least 5 characters.")
        return cleaned


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    """
    Admin serializer for viewing contact messages in the admin dashboard.
    Strictly read-only so administrators cannot alter customer messages.
    """

    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "user",
            "user_email",
            "full_name",
            "email",
            "phone_number",
            "message",
            "agree_to_privacy_policy",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for user notifications."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "priority",
            "is_read",
            "read_at",
            "action_url",
            "data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "priority",
            "read_at",
            "action_url",
            "data",
            "created_at",
            "updated_at",
        ]


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
