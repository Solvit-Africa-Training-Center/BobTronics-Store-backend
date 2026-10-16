from rest_framework import serializers

from apps.orders.models import OrderStatus

from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Feedback
        fields = ["feedback_id", "user", "product", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["feedback_id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        product = attrs.get("product")
        if user is None or product is None:
            return attrs
        if Feedback.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError({"product": "You already reviewed this product."})
        if not user.orders.filter(status=OrderStatus.DELIVERED, items__product=product).exists():
            raise serializers.ValidationError({"product": "Review this product after delivery."})
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
