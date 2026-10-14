from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, status
from rest_framework.response import Response
from django.db import transaction

from apps.audit.services import log_audit_event
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsCustomer
from apps.catalog.pagination import StandardPagination

from .models import Service
from .serializers import (
    AdminServiceUpdateSerializer,
    ServiceCreateSerializer,
    ServiceSerializer,
)


class CustomerServiceListCreateView(generics.ListCreateAPIView):
    """Customers may create service requests and see only their own requests."""

    permission_classes = [IsCustomer]
    pagination_class = StandardPagination
    serializer_class = ServiceSerializer
    queryset = Service.objects.none()

    def get_queryset(self):
        return (
            Service.objects.filter(user=self.request.user)
            .select_related("user")
            .order_by("-requested_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ServiceCreateSerializer
        return ServiceSerializer

    @extend_schema(
        summary="List my service requests",
        responses={200: ServiceSerializer(many=True)},
        tags=["Service Requests"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Request a BobTronics service",
        description=(
            "Submit a repair, troubleshooting, networking, consultancy, "
            "project management, or other electronic service request. "
            "The request is created with status 'new'."
        ),
        request=ServiceCreateSerializer,
        responses={
            201: ServiceSerializer,
            400: OpenApiResponse(description="Invalid service request details"),
        },
        tags=["Service Requests"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            service = serializer.save(user=request.user)
            log_audit_event(
                action="service_request.created",
                entry_type="Service",
                entity_id=service.service_id,
                user=request.user,
                description="Customer submitted a service request.",
                request=request,
            )
        return Response(
            ServiceSerializer(service).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerServiceDetailView(generics.RetrieveAPIView):
    """A customer can retrieve only a service request they own."""

    permission_classes = [IsCustomer]
    serializer_class = ServiceSerializer
    lookup_field = "service_id"
    lookup_url_kwarg = "service_id"

    def get_queryset(self):
        return Service.objects.filter(user=self.request.user).select_related("user")

    @extend_schema(
        summary="View one of my service requests",
        responses={
            200: ServiceSerializer,
            404: OpenApiResponse(description="Service request not found"),
        },
        tags=["Service Requests"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminServiceListView(generics.ListAPIView):
    """Admins can browse and filter all customer service requests."""

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = ServiceSerializer
    pagination_class = StandardPagination
    queryset = Service.objects.select_related("user").all()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "service_type"]
    search_fields = ["name", "description", "user__email"]
    ordering_fields = ["requested_at", "created_at", "status", "service_type"]
    ordering = ["-requested_at"]

    @extend_schema(
        summary="Admin list of service requests",
        description="Filter by status or service_type; search by request details or customer email.",
        responses={200: ServiceSerializer(many=True)},
        tags=["Service Requests (Admin)"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminServiceDetailView(generics.RetrieveUpdateAPIView):
    """Admins may inspect a request and patch its status and quoted costs."""

    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Service.objects.select_related("user").all()
    lookup_field = "service_id"
    lookup_url_kwarg = "service_id"
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AdminServiceUpdateSerializer
        return ServiceSerializer

    @extend_schema(
        summary="Admin view of a service request",
        responses={
            200: ServiceSerializer,
            404: OpenApiResponse(description="Service request not found"),
        },
        tags=["Service Requests (Admin)"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update service request status or costs",
        description=(
            "Only admins may update status and estimated/final costs. "
            "Status transitions are validated; completing a request records completed_at."
        ),
        request=AdminServiceUpdateSerializer,
        responses={
            200: ServiceSerializer,
            400: OpenApiResponse(description="Invalid cost or status transition"),
            404: OpenApiResponse(description="Service request not found"),
        },
        tags=["Service Requests (Admin)"],
    )
    def patch(self, request, *args, **kwargs):
        service = self.get_object()
        serializer = AdminServiceUpdateSerializer(
            service, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        previous_status = service.status
        previous_estimated_cost = service.estimated_cost
        previous_final_cost = service.final_cost
        with transaction.atomic():
            service = serializer.save()
            if previous_status != service.status:
                log_audit_event(
                    action="service_request.status_changed",
                    entry_type="Service",
                    entity_id=service.service_id,
                    user=request.user,
                    description=f"Service request status changed from {previous_status} to {service.status}.",
                    request=request,
                )
            changed_costs = []
            if previous_estimated_cost != service.estimated_cost:
                changed_costs.append("estimated cost")
            if previous_final_cost != service.final_cost:
                changed_costs.append("final cost")
            if changed_costs:
                log_audit_event(
                    action="service_request.costs_changed",
                    entry_type="Service",
                    entity_id=service.service_id,
                    user=request.user,
                    description=f"Updated: {', '.join(changed_costs)}.",
                    request=request,
                )
        return Response(ServiceSerializer(service).data, status=status.HTTP_200_OK)
