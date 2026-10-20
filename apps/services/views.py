from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer
from apps.common.permissions import IsAdminRole

from .models import Service, ServiceStatus
from .serializers import (
    AdminServiceReadSerializer,
    ServiceCreateSerializer,
    ServiceReadSerializer,
    ServiceUpdateSerializer,
)


class CustomerServiceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return Service.objects.filter(user=self.request.user).order_by("-requested_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ServiceCreateSerializer
        return ServiceReadSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CustomerServiceDetailView(generics.RetrieveAPIView):
    serializer_class = ServiceReadSerializer
    permission_classes = [IsCustomer]
    lookup_field = "service_id"

    def get_queryset(self):
        return Service.objects.filter(user=self.request.user)


class CustomerCancelServiceView(APIView):
    permission_classes = [IsCustomer]

    @transaction.atomic
    def post(self, request, service_id):
        service = get_object_or_404(
            Service.objects.select_for_update(),
            service_id=service_id,
            user=request.user,
        )
        if service.status != ServiceStatus.NEW:
            raise serializers.ValidationError(
                {"status": "Only new service requests can be cancelled."}
            )
        service.status = ServiceStatus.CANCELLED
        service.save(update_fields=("status", "updated_at"))
        return Response({"message": "Service request cancelled."})


class AdminServiceListView(generics.ListAPIView):
    serializer_class = AdminServiceReadSerializer
    permission_classes = [IsAdminRole]
    queryset = Service.objects.select_related("user").order_by("-requested_at")
    filterset_fields = ("status", "service_type", "user")


class AdminServiceDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminRole]
    lookup_field = "service_id"
    queryset = Service.objects.select_related("user")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ServiceUpdateSerializer
        return AdminServiceReadSerializer

    def perform_update(self, serializer):
        completed_at = None
        if (
            serializer.instance.status != ServiceStatus.COMPLETED
            and serializer.validated_data.get("status") == ServiceStatus.COMPLETED
        ):
            completed_at = timezone.now()
        if completed_at:
            serializer.save(completed_at=completed_at)
        else:
            serializer.save()
