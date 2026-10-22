from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response

from apps.common.models import ContactMessage, Notification
from apps.common.permissions import IsAdminRole
from apps.common.serializers import (
    ContactMessageAdminSerializer,
    ContactMessageSerializer,
    NotificationSerializer,
    NotificationUnreadCountSerializer,
)
from apps.common.services import send_contact_form_notifications


# ============================================================================
# CONTACT MESSAGES API (CUSTOMER)
# ============================================================================

@extend_schema_view(
    get=extend_schema(
        operation_id="contact_customer_list",
        summary="List Customer Messages",
        description="Retrieves messages sent by the authenticated customer.",
        responses={200: ContactMessageSerializer(many=True)},
        tags=["Contact"],
    ),
    post=extend_schema(
        operation_id="contact_customer_create",
        summary="Send Contact Message",
        description="Allows an authenticated customer to send a message to store administrators.",
        request=ContactMessageSerializer,
        responses={
            201: OpenApiResponse(
                description="Message sent successfully.",
                response=ContactMessageSerializer,
            ),
            400: OpenApiResponse(description="Validation error."),
        },
        examples=[
            OpenApiExample(
                "Contact submission request",
                request_only=True,
                value={
                    "full_name": "David Shema",
                    "email": "david.shema@example.com",
                    "phone_number": "+250 78 555 0184",
                    "message": "I'm looking for a laptop for design work. Can your team help me choose the right configuration?",
                    "agree_to_privacy_policy": True,
                },
            ),
        ],
        tags=["Contact"],
    ),
)
class ContactMessageListCreateView(generics.ListCreateAPIView):
    """
    Authenticated customer endpoint to view their previous messages and send a new message.
    """

    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContactMessage.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)

        # Auto-fill full_name and email from user profile if not provided
        if not data.get("full_name"):
            user_fullname = f"{request.user.first_name} {request.user.last_name}".strip()
            data["full_name"] = user_fullname or request.user.username
        if not data.get("email"):
            data["email"] = request.user.email

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        contact_message = serializer.save(user=request.user)

        # Notify administrator via email and record audit event
        send_contact_form_notifications(contact_message, request=request)

        return Response(
            {
                "success": True,
                "message": "Your message has been sent successfully. We will get back to you soon.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="contact_customer_detail",
        summary="Get Customer Message Detail",
        tags=["Contact"],
    ),
    patch=extend_schema(
        operation_id="contact_customer_update",
        summary="Edit Customer Message",
        description="Allows customer to edit their message.",
        tags=["Contact"],
    ),
    put=extend_schema(
        operation_id="contact_customer_replace",
        summary="Replace Customer Message",
        tags=["Contact"],
    ),
    delete=extend_schema(
        operation_id="contact_customer_delete",
        summary="Delete Customer Message",
        description="Allows customer to delete their message.",
        tags=["Contact"],
    ),
)
class ContactMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Customer endpoint allowing the sender to view, edit, and delete their own contact message.
    """

    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContactMessage.objects.filter(user=self.request.user)


# ============================================================================
# CONTACT MESSAGES API (ADMIN DASHBOARD)
# ============================================================================

@extend_schema_view(
    get=extend_schema(
        operation_id="contact_admin_list",
        summary="List All Contact Messages (Admin Dashboard)",
        description="Admin dashboard endpoint to view all customer messages. Supports search and is_read filtering.",
        responses={200: ContactMessageAdminSerializer(many=True)},
        tags=["Contact (Admin)"],
    ),
)
class AdminContactMessageListView(generics.ListAPIView):
    """
    Admin dashboard endpoint to list all customer messages.
    """

    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "phone_number", "message", "user__email"]
    ordering_fields = ["created_at", "is_read"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = ContactMessage.objects.select_related("user").all()
        is_read_param = self.request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                queryset = queryset.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                queryset = queryset.filter(is_read=False)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unread_count = ContactMessage.objects.filter(is_read=False).count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["success"] = True
            response.data["unread_count"] = unread_count
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "unread_count": unread_count,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="contact_admin_detail",
        summary="Read Contact Message Detail (Admin Dashboard)",
        description="Admin reads customer message. Automatically marks message as read. Admin cannot edit the message content.",
        responses={200: ContactMessageAdminSerializer},
        tags=["Contact (Admin)"],
    ),
    delete=extend_schema(
        operation_id="contact_admin_delete",
        summary="Delete Contact Message (Admin)",
        description="Allows admin to remove a message from dashboard.",
        tags=["Contact (Admin)"],
    ),
)
class AdminContactMessageDetailView(generics.RetrieveDestroyAPIView):
    """
    Admin endpoint to read customer message.
    Cannot edit (no PUT/PATCH allowed) to guarantee customer message integrity.
    Automatically marks the message as read upon opening.
    """

    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = ContactMessage.objects.select_related("user").all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# NOTIFICATIONS API (CUSTOMER ACTIVITIES & DETAIL VIEWS)
# ============================================================================

@extend_schema_view(
    get=extend_schema(
        operation_id="notifications_list",
        summary="List User Notifications",
        description="Retrieves a list of notifications for the authenticated user. Filter with ?is_read=false for unread only.",
        responses={200: NotificationSerializer(many=True)},
        tags=["Notifications"],
    )
)
class NotificationListView(generics.ListAPIView):
    """Lists notifications for the currently authenticated user."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        is_read_param = self.request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                queryset = queryset.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                queryset = queryset.filter(is_read=False)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["success"] = True
            response.data["unread_count"] = unread_count
            response.data["notifications"] = response.data["results"]
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "unread_count": unread_count,
                "notifications": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="notifications_detail",
        summary="Get Notification Detail",
        description="Returns full notification details including deep link action_url and metadata payload. Automatically marks notification as read.",
        responses={200: NotificationSerializer},
        tags=["Notifications"],
    ),
    delete=extend_schema(
        operation_id="notifications_delete",
        summary="Delete Notification",
        description="Deletes a notification from the user's inbox.",
        tags=["Notifications"],
    ),
)
class NotificationDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieves full notification details. Automatically marks the notification
    as read when clicked/opened.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "notification": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    patch=extend_schema(
        operation_id="notifications_mark_read",
        summary="Mark Notification as Read",
        description="Marks a specific notification as read.",
        responses={200: NotificationSerializer},
        tags=["Notifications"],
    )
)
class NotificationMarkReadView(generics.GenericAPIView):
    """Marks a single notification as read."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, pk, *args, **kwargs):
        notification = generics.get_object_or_404(self.get_queryset(), pk=pk)
        notification.mark_as_read()
        return Response(
            {
                "success": True,
                "message": "Notification marked as read.",
                "notification": NotificationSerializer(notification).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="notifications_mark_all_read",
        summary="Mark All Notifications as Read",
        description="Marks all unread notifications for the authenticated user as read.",
        responses={
            200: OpenApiResponse(description="All notifications marked as read.")
        },
        tags=["Notifications"],
    )
)
class NotificationMarkAllReadView(generics.GenericAPIView):
    """Marks all unread notifications for the user as read."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        now = timezone.now()
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=now
        )
        return Response(
            {
                "success": True,
                "message": f"Marked {updated_count} notification(s) as read.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="notifications_unread_count",
        summary="Get Unread Notifications Count",
        description="Returns the total count of unread notifications for the user's navbar bell badge.",
        responses={200: NotificationUnreadCountSerializer},
        tags=["Notifications"],
    )
)
class NotificationUnreadCountView(generics.GenericAPIView):
    """Quick count endpoint for top navbar badge."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationUnreadCountSerializer

    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response(
            {
                "success": True,
                "unread_count": unread_count,
            },
            status=status.HTTP_200_OK,
        )
