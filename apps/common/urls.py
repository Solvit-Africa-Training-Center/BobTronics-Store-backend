from django.urls import path

from apps.common.views import (
    AdminContactMessageDetailView,
    AdminContactMessageListView,
    ContactFormView,
)

app_name = "common"

urlpatterns = [
    # Public contact submission: POST /api/v1/contact/
    path("", ContactFormView.as_view(), name="contact-submit"),

    # Admin management: GET/PATCH /api/v1/contact/admin/messages/
    path("admin/messages/", AdminContactMessageListView.as_view(), name="contact-admin-list"),
    path("admin/messages/<int:pk>/", AdminContactMessageDetailView.as_view(), name="contact-admin-detail"),
]
