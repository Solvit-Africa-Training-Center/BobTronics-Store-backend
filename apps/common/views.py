from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters, generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.common.models import ContactMessage, ContactStatus, Notification
from apps.common.permissions import IsAdminRole
from apps.common.serializers import (
    ContactMessageAdminSerializer,
    ContactMessageCreateSerializer,
    ContactMessageResponseSerializer,
    NotificationSerializer,
    NotificationUnreadCountSerializer,
)
from apps.common.services import send_contact_form_notifications


@extend_schema_view(
    post=extend_schema(
        operation_id="common_contact_form_submit",
        summary="Submit Contact Form Message",
        description=(
            "Accepts contact inquiries from customers or site visitors, notifies "
            "administrators via email (with attachments if uploaded), and sends an "
            "acknowledgment receipt to the sender. Supports both JSON and multipart form data."
        ),
        request=ContactMessageCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Message sent successfully.",
                response=ContactMessageResponseSerializer,
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
                    "how_can_we_help": "Product advice",
                    "message": "I'm looking for a laptop for design work. Can your team help me choose the right configuration?",
                    "agree_to_privacy_policy": True,
                },
            ),
        ],
        tags=["Contact"],
    )
)
class ContactFormView(generics.CreateAPIView):
    """
    Public endpoint for visitors and customers to send a message to store administrators.
    Accepts both JSON and Multipart Form data (for file attachments).
    """

    serializer_class = ContactMessageCreateSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user and request.user.is_authenticated else None
        contact_message = serializer.save(user=user)

        # Dispatch emails to admin and sender + record audit log + send in-app notification
        send_contact_form_notifications(contact_message, request=request)

        response_data = ContactMessageResponseSerializer(
            contact_message, context={"request": request}
        ).data
        return Response(
            {
                "success": True,
                "message": "Your message has been sent successfully. We will get back to you soon.",
                "data": response_data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="common_admin_contact_list",
        summary="List Contact Inquiries (Admin)",
        description="Allows staff and administrators to review contact messages submitted through the website.",
        responses={200: ContactMessageAdminSerializer(many=True)},
        tags=["Contact"],
    )
)
class AdminContactMessageListView(generics.ListAPIView):
    """Admin-only endpoint to list all received contact messages."""

    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "phone", "subject", "message"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = ContactMessage.objects.select_related("user").all()
        status_param = self.request.query_params.get("status")
        if status_param and status_param in ContactStatus.values:
            queryset = queryset.filter(status=status_param)
        return queryset


@extend_schema_view(
    get=extend_schema(
        operation_id="common_admin_contact_detail",
        summary="Get Contact Inquiry Detail (Admin)",
        tags=["Contact"],
    ),
    patch=extend_schema(
        operation_id="common_admin_contact_update",
        summary="Update Contact Inquiry Status/Notes (Admin)",
        tags=["Contact"],
    ),
    delete=extend_schema(
        operation_id="common_admin_contact_delete",
        summary="Delete Contact Inquiry (Admin)",
        tags=["Contact"],
    ),
)
class AdminContactMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only endpoint to view, update status, and manage contact messages."""

    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = ContactMessage.objects.select_related("user").all()

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        instance = serializer.instance
        if new_status == ContactStatus.REPLIED and not instance.replied_at:
            updated = serializer.save(replied_at=timezone.now())
        else:
            updated = serializer.save()

        if updated.user and new_status == ContactStatus.REPLIED:
            from apps.common.models import NotificationPriority, NotificationType
            from apps.common.services import create_user_notification

            create_user_notification(
                user=updated.user,
                title="Response to Your Inquiry",
                message=f"An administrator responded to your message: '{updated.subject}'.",
                notification_type=NotificationType.CONTACT,
                action_url="/contact",
                data={
                    "contact_id": updated.pk,
                    "subject": updated.subject,
                    "status": updated.status,
                    "admin_notes": updated.admin_notes,
                },
                priority=NotificationPriority.SUCCESS,
            )


# ============================================================================
# NOTIFICATIONS API
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
        # Auto mark as read on view
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
