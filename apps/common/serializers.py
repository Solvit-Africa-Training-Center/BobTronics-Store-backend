from rest_framework import serializers

from apps.common.models import ContactMessage, ContactStatus, Notification


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for visitors/customers submitting the contact form.
    Supports both traditional API fields and frontend form names (e.g. full_name, how_can_we_help).
    """

    # Primary fields
    name = serializers.CharField(
        max_length=255,
        required=False,
        trim_whitespace=True,
        help_text="Full name of the sender.",
    )
    email = serializers.EmailField(
        trim_whitespace=True,
        help_text="Email address for replies.",
    )
    phone = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
        help_text="Telephone contact number.",
    )
    subject = serializers.CharField(
        max_length=255,
        required=False,
        default="Product advice",
        trim_whitespace=True,
        help_text="Inquiry subject or topic.",
    )
    message = serializers.CharField(
        trim_whitespace=True,
        min_length=5,
        help_text="Message content (minimum 5 characters).",
    )
    attachment = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Optional file or screenshot attachment.",
    )

    # Frontend alias fields (read from request, mapped during validation)
    full_name = serializers.CharField(
        max_length=255,
        required=False,
        write_only=True,
        trim_whitespace=True,
        help_text="Alias for name.",
    )
    phone_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=True,
        help_text="Alias for phone.",
    )
    how_can_we_help = serializers.CharField(
        max_length=255,
        required=False,
        write_only=True,
        trim_whitespace=True,
        help_text="Alias for subject/dropdown topic.",
    )
    agree_to_privacy_policy = serializers.BooleanField(
        required=False,
        default=True,
        write_only=True,
        help_text="Checkbox indicating user consent to privacy policy.",
    )

    class Meta:
        model = ContactMessage
        fields = [
            "name",
            "full_name",
            "email",
            "phone",
            "phone_number",
            "subject",
            "how_can_we_help",
            "message",
            "attachment",
            "agree_to_privacy_policy",
            "agreed_to_privacy_policy",
        ]
        extra_kwargs = {
            "agreed_to_privacy_policy": {"required": False},
        }

    def validate(self, attrs):
        # Resolve full_name vs name
        name = attrs.get("name") or attrs.get("full_name")
        if not name:
            raise serializers.ValidationError({"name": "Full name is required."})
        attrs["name"] = name.strip()

        # Resolve phone vs phone_number
        phone = attrs.get("phone") or attrs.get("phone_number") or ""
        attrs["phone"] = phone.strip()

        # Resolve subject vs how_can_we_help
        subject = attrs.get("subject") or attrs.get("how_can_we_help") or "General Inquiry"
        attrs["subject"] = subject.strip()

        # Resolve privacy policy
        if "agree_to_privacy_policy" in attrs:
            attrs["agreed_to_privacy_policy"] = attrs["agree_to_privacy_policy"]

        # Validate message length
        msg = attrs.get("message", "").strip()
        if len(msg) < 5:
            raise serializers.ValidationError({"message": "Message must contain at least 5 characters."})
        attrs["message"] = msg

        # Clean up alias keys not present on model
        attrs.pop("full_name", None)
        attrs.pop("phone_number", None)
        attrs.pop("how_can_we_help", None)
        attrs.pop("agree_to_privacy_policy", None)

        return attrs


class ContactMessageResponseSerializer(serializers.ModelSerializer):
    """Response returned upon successful contact message submission."""

    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "attachment_url",
            "agreed_to_privacy_policy",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url
        return None


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    """Admin management serializer for reviewing and updating contact inquiries."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "user",
            "user_email",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "attachment_url",
            "agreed_to_privacy_policy",
            "status",
            "admin_notes",
            "replied_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_email",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "attachment_url",
            "agreed_to_privacy_policy",
            "created_at",
            "updated_at",
        ]

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url
        return None


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
