from django.urls import path

from apps.common.views import (
    AdminContactMessageDetailView,
    AdminContactMessageListView,
    ContactMessageDetailView,
    ContactMessageListCreateView,
)

app_name = "common"

urlpatterns = [
    # Customer endpoints: List past messages, send new message
    path("", ContactMessageListCreateView.as_view(), name="contact-list-create"),
    # Customer endpoints: View detail, edit, delete own message
    path("<int:pk>/", ContactMessageDetailView.as_view(), name="contact-detail"),

    # Admin dashboard endpoints: View all messages, read message detail
    path("admin/messages/", AdminContactMessageListView.as_view(), name="contact-admin-list"),
    path("admin/messages/<int:pk>/", AdminContactMessageDetailView.as_view(), name="contact-admin-detail"),
]
