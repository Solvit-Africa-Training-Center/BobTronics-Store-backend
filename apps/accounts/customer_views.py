from decimal import Decimal
from django.db.models import Count, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, status
from rest_framework.response import Response
from apps.orders.models import Order

from apps.accounts.models import Role, User
from .customer_serializers import (
    AdminCustomerDetailSerializer,
    AdminCustomerListSerializer,
    CustomerAddressSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
)
from .permissions import IsAdminOrSuperAdmin, IsCustomer


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/customers/profile/
    Retrieve authenticated user's profile with lifetime order analytics.

    PUT / PATCH /api/v1/customers/profile/
    Update personal information (first_name, last_name, phone, residence).
    Email and role are protected from modification.
    """

    permission_classes = [IsCustomer]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return CustomerProfileUpdateSerializer
        return CustomerProfileSerializer

    def get_object(self):
        # Fetch authenticated user with aggregated metrics in one optimized query
        user = (
            User.objects.filter(pk=self.request.user.pk)
            .annotate(
                total_orders_count=Count("orders"),
                total_spent_amount=Coalesce(
                    Sum("orders__total_amount", filter=~Q(orders__status="cancelled")),
                    Value(Decimal("0.00")),
                ),
            )
            .first()
        )
        return user or self.request.user

    @extend_schema(
        summary="Get Customer Profile",
        description="Returns the profile of the currently authenticated customer, including order summary metrics.",
        responses={200: CustomerProfileSerializer},
        tags=["Customer Profile"],
    )
    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = CustomerProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update Customer Profile",
        description="Updates personal profile fields (first_name, last_name, phone, residence). Email and role are immutable.",
        request=CustomerProfileUpdateSerializer,
        responses={200: CustomerProfileSerializer},
        tags=["Customer Profile"],
    )
    def put(self, request, *args, **kwargs):
        return self._perform_update(request, partial=False)

    @extend_schema(
        summary="Partially Update Customer Profile",
        description="Partially updates customer profile fields.",
        request=CustomerProfileUpdateSerializer,
        responses={200: CustomerProfileSerializer},
        tags=["Customer Profile"],
    )
    def patch(self, request, *args, **kwargs):
        return self._perform_update(request, partial=True)

    def _perform_update(self, request, partial=False):
        user = self.get_object()
        serializer = CustomerProfileUpdateSerializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Re-serialize with full profile representation
        refreshed_user = self.get_object()
        response_serializer = CustomerProfileSerializer(refreshed_user)
        return Response(
            {
                "message": "Profile updated successfully.",
                "user": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CustomerAddressView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/customers/address/
    Quick lookup for current delivery residence and contact phone.

    PUT / PATCH /api/v1/customers/address/
    Update shipping residence address and phone for checkout convenience.
    """

    permission_classes = [IsCustomer]
    serializer_class = CustomerAddressSerializer

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Get Saved Shipping Address",
        description="Returns the saved delivery residence and contact phone for the authenticated customer.",
        responses={200: CustomerAddressSerializer},
        tags=["Customer Profile"],
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update Shipping Address",
        description="Updates the customer's delivery residence address and contact phone number.",
        request=CustomerAddressSerializer,
        responses={200: CustomerAddressSerializer},
        tags=["Customer Profile"],
    )
    def put(self, request, *args, **kwargs):
        return self._update_address(request, partial=False)

    @extend_schema(
        summary="Partially Update Shipping Address",
        description="Partially updates the delivery residence address.",
        request=CustomerAddressSerializer,
        responses={200: CustomerAddressSerializer},
        tags=["Customer Profile"],
    )
    def patch(self, request, *args, **kwargs):
        return self._update_address(request, partial=True)

    def _update_address(self, request, partial=False):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Delivery address updated successfully.",
                "address": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AdminCustomerListView(generics.ListAPIView):
    """
    GET /api/v1/customers/
    Administrative endpoint to browse all registered customers with pagination,
    filtering, and search (Section 6 of Project Roadmap).
    """

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminCustomerListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["first_name", "last_name", "email", "phone", "residence"]
    ordering_fields = ["created_at", "first_name", "last_name", "total_orders"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Memory-optimized query: selects only required fields and aggregates order counts in database
        return (
            User.objects.filter(role=Role.CUSTOMER)
            .only(
                "user_id",
                "first_name",
                "last_name",
                "email",
                "phone",
                "residence",
                "role",
                "is_active",
                "created_at",
            )
            .annotate(total_orders=Count("orders"))
        )

    @extend_schema(
        summary="Admin: List Customers",
        description="Returns a paginated list of registered customers with lifetime order counts.",
        responses={200: AdminCustomerListSerializer(many=True)},
        tags=["Admin Customers"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminCustomerDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/customers/<int:user_id>/
    Administrative endpoint to view a specific customer's profile and their
    recent order history.
    """

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminCustomerDetailSerializer
    lookup_field = "user_id"

    def get_queryset(self):
        """
        Single optimized query:
        - Annotates total_orders_count and total_spent_amount at DB level.
        - Prefetches all orders once (sliced to 10 in serializer) to avoid N+1.
        """
        return (
            User.objects.filter(role=Role.CUSTOMER)
            .annotate(
                total_orders_count=Count("orders"),
                total_spent_amount=Coalesce(
                    Sum(
                        "orders__total_amount",
                        filter=~Q(orders__status="cancelled"),
                    ),
                    Value(Decimal("0.00")),
                ),
            )
            .prefetch_related(
                Prefetch(
                    "orders",
                    queryset=Order.objects.order_by("-order_date"),
                    to_attr="prefetched_orders",
                )
            )
        )

    @extend_schema(
        summary="Admin: Customer Detail",
        description="Returns complete details for a customer, including recent order transactions.",
        responses={
            200: AdminCustomerDetailSerializer,
            404: OpenApiResponse(description="Customer not found"),
        },
        tags=["Admin Customers"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
