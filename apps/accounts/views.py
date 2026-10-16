from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.serializers import (
    ActivationSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    MessageSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshRequestSerializer,
    RegisterSerializer,
    RegistrationResponseSerializer,
    UserSerializer,
    UserProfileSerializer,
)
from apps.accounts.services import ACTIVATION_MESSAGE, PASSWORD_RESET_MESSAGE

ERROR_RESPONSE = OpenApiResponse(description="Validation or token error returned in the standard API error envelope.")


class LoginRateThrottle(AnonRateThrottle):
    """Limit unauthenticated login attempts by client IP."""

    scope = "auth_login"


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        summary="User Login",
        description="Authenticates active user credentials and returns JWT access/refresh tokens. Rejects unactivated accounts.",
        request=LoginSerializer,
        responses={200: LoginResponseSerializer, 400: OpenApiResponse(description="Invalid email/password or account not activated")},
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({
            "message": "Logged in.",
            "user": UserProfileSerializer(user).data,
            "tokens": serializer.validated_data["tokens"],
        }, status=status.HTTP_200_OK)


@extend_schema_view(post=extend_schema(
    operation_id="accounts_register",
    summary="Register a customer account",
    request=RegisterSerializer,
    responses={201: RegistrationResponseSerializer, 400: ERROR_RESPONSE},
    examples=[
        OpenApiExample("Registration request", request_only=True, value={
            "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
            "password": "A-strong-password-45!", "password_confirm": "A-strong-password-45!",
            "phone": "+250780000000", "residence": "Kigali",
        }),
        OpenApiExample("Registration response", response_only=True, status_codes=[201], value={
            "message": ACTIVATION_MESSAGE,
            "user": {"user_id": 12, "first_name": "Aline", "last_name": "Uwase",
                     "email": "aline@example.com", "phone": "+250780000000", "residence": "Kigali",
                     "role": "customer", "created_at": "2026-10-13T09:00:00Z", "updated_at": "2026-10-13T09:00:00Z"},
        }),
    ],
))
class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"message": ACTIVATION_MESSAGE, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@extend_schema_view(post=extend_schema(
    operation_id="accounts_activate",
    summary="Validate and activate an account",
    request=ActivationSerializer,
    responses={200: MessageSerializer, 400: ERROR_RESPONSE},
    examples=[
        OpenApiExample("Activation request", request_only=True, value={"uid": "MTI", "token": "token-from-email"}),
        OpenApiExample("Activation response", response_only=True, status_codes=[200], value={"message": "Account activated."}),
    ],
))
class ActivateView(generics.GenericAPIView):
    serializer_class = ActivationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Account activated."})


@extend_schema_view(get=extend_schema(
    operation_id="accounts_current_user",
    summary="Get the authenticated user's profile",
    responses={200: UserSerializer},
    examples=[OpenApiExample("Current user response", response_only=True, status_codes=[200], value={
        "user_id": 12, "first_name": "Aline", "last_name": "Uwase", "email": "aline@example.com",
        "phone": "+250780000000", "residence": "Kigali", "role": "customer",
        "created_at": "2026-10-13T09:00:00Z", "updated_at": "2026-10-13T09:00:00Z",
    })],
))
class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema_view(post=extend_schema(
    operation_id="accounts_password_reset_request",
    summary="Request a password reset",
    request=PasswordResetRequestSerializer,
    responses={200: MessageSerializer},
    examples=[
        OpenApiExample("Password reset request", request_only=True, value={"email": "aline@example.com"}),
        OpenApiExample("Password reset response", response_only=True, status_codes=[200], value={"message": PASSWORD_RESET_MESSAGE}),
    ],
))
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


@extend_schema_view(post=extend_schema(
    operation_id="accounts_password_reset_confirm",
    summary="Set a new password using a reset token",
    request=PasswordResetConfirmSerializer,
    responses={200: MessageSerializer, 400: ERROR_RESPONSE},
    examples=[
        OpenApiExample("Password reset confirmation", request_only=True, value={
            "uid": "MTI", "token": "token-from-email", "new_password": "A-new-strong-password-57!",
            "password_confirm": "A-new-strong-password-57!",
        }),
        OpenApiExample("Password reset response", response_only=True, status_codes=[200], value={"message": "Password reset successfully."}),
    ],
))
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


@extend_schema_view(post=extend_schema(
    operation_id="accounts_logout",
    summary="Blacklist a refresh token",
    request=LogoutSerializer,
    responses={200: MessageSerializer, 400: ERROR_RESPONSE},
    examples=[
        OpenApiExample("Logout request", request_only=True, value={"refresh": "refresh-token"}),
        OpenApiExample("Logout response", response_only=True, status_codes=[200], value={"message": "Logged out."}),
    ],
))
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


@extend_schema_view(post=extend_schema(
    operation_id="accounts_token_refresh",
    summary="Refresh access and rotating refresh tokens",
    request=RefreshRequestSerializer,
    responses={200: RefreshRequestSerializer, 401: ERROR_RESPONSE},
    examples=[
        OpenApiExample("Refresh request", request_only=True, value={"refresh": "refresh-token"}),
        OpenApiExample("Refresh response", response_only=True, status_codes=[200], value={
            "access": "new-access-token", "refresh": "new-refresh-token",
        }),
    ],
))
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
