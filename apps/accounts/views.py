from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginResponseSerializer, LoginSerializer, UserProfileSerializer


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticate an active customer or admin using email and password.
    Returns JWT access and refresh tokens along with user profile details.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Login",
        description="Authenticates active user credentials and returns JWT access/refresh tokens. Rejects unactivated accounts.",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description="Invalid email/password or account not activated"),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = serializer.validated_data["tokens"]
        user_data = UserProfileSerializer(user).data

        return Response(
            {
                "message": "Login successful.",
                "user": user_data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )
