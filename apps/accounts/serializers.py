from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Public profile representation of the authenticated user.
    """

    class Meta:
        model = User
        fields = (
            "user_id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "residence",
            "created_at",
        )
        read_only_fields = fields


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    user = UserProfileSerializer()
    tokens = TokenResponseSerializer()


class LoginSerializer(serializers.Serializer):
    """
    Serializer to authenticate active users and generate JWT access/refresh tokens.
    Enforces account activation check (is_active) and protects against enumeration.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        # 1. Lookup user
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Generic error to prevent email enumeration
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        # 2. Verify password hash
        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        # 3. Check account activation
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Account is not activated. Please verify your email before logging in."}
            )

        # 4. Generate SimpleJWT tokens
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        return {
            "user": user,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }
