from rest_framework import serializers

from .models import Feedback, ReviewStatus


class ReviewReadSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "feedback_id",
            "product",
            "author",
            "rating",
            "comment",
            "created_at",
        )
        read_only_fields = fields


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("product", "rating", "comment")


class AdminReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "feedback_id",
            "user",
            "user_email",
            "product",
            "product_name",
            "rating",
            "comment",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReviewModerationSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=(
            (ReviewStatus.APPROVED, "Approved"),
            (ReviewStatus.HIDDEN, "Hidden"),
        )
    )

    class Meta:
        model = Feedback
        fields = ("status",)
