from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.common.permissions import IsAdminRole
from apps.accounts.permissions import IsCustomer

from .models import Feedback, ReviewStatus
from .serializers import (
    AdminReviewSerializer,
    ReviewCreateSerializer,
    ReviewModerationSerializer,
    ReviewReadSerializer,
)


class ReviewListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def get_queryset(self):
        return (
            Feedback.objects.filter(status=ReviewStatus.APPROVED)
            .select_related("user", "product")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewReadSerializer

    def get_permissions(self):
        permission = IsCustomer if self.request.method == "POST" else AllowAny
        return [permission()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=ReviewStatus.PENDING)


class ReviewDetailView(generics.RetrieveAPIView):
    serializer_class = ReviewReadSerializer
    permission_classes = [AllowAny]
    lookup_field = "feedback_id"

    def get_queryset(self):
        return Feedback.objects.filter(status=ReviewStatus.APPROVED).select_related(
            "user", "product"
        )


class AdminReviewListView(generics.ListAPIView):
    serializer_class = AdminReviewSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "product", "rating"]
    queryset = Feedback.objects.select_related("user", "product").order_by(
        "-created_at"
    )


class AdminReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminRole]
    lookup_field = "feedback_id"
    queryset = Feedback.objects.select_related("user", "product")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ReviewModerationSerializer
        return AdminReviewSerializer
