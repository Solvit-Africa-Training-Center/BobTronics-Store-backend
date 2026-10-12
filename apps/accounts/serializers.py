from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps.accounts.models import User
from apps.accounts.services import (
    activate_account,
    blacklist_refresh_token,
    complete_password_reset,
    register_user,
    request_password_reset,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "user_id", "first_name", "last_name", "email", "phone", "residence",
            "role", "created_at", "updated_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    residence = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        user = User(email=attrs["email"], first_name=attrs["first_name"], last_name=attrs["last_name"])
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return register_user(**validated_data)


class ActivationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def save(self, **kwargs):
        if not activate_account(self.validated_data["uid"], self.validated_data["token"]):
            raise serializers.ValidationError("This activation link is invalid or expired.")
        return True


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        request_password_reset(self.validated_data["email"])
        return {"message": "If an active account matches that email, password reset instructions have been sent."}


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})

    def validate(self, attrs):
        if attrs["new_password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            validate_password(attrs["new_password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs

    def save(self, **kwargs):
        if not complete_password_reset(
            self.validated_data["uid"], self.validated_data["token"], self.validated_data["new_password"]
        ):
            raise serializers.ValidationError({"token": "This password reset link is invalid or expired."})
        return {"message": "Password has been reset successfully."}


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=False)

    def save(self, **kwargs):
        try:
            blacklist_refresh_token(self.validated_data["refresh"])
        except ValueError as exc:
            raise serializers.ValidationError({"refresh": "Invalid or expired refresh token."}) from exc
        return {"message": "Logout successful."}


class RefreshRequestSerializer(TokenRefreshSerializer):
    """Schema alias for Simple JWT's refresh serializer."""


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class RegistrationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()
