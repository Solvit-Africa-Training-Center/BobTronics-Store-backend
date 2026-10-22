from django.urls import path

from apps.common.views import (
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    # List notifications: GET /api/v1/notifications/ (?is_read=false)
    path("", NotificationListView.as_view(), name="notification-list"),

    # Badge unread count: GET /api/v1/notifications/unread-count/
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),

    # Mark all as read: POST /api/v1/notifications/mark-all-read/
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),

    # Single notification detail (auto marks as read): GET /api/v1/notifications/<id>/
    path("<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),

    # Mark single notification as read: PATCH /api/v1/notifications/<id>/read/
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
]
