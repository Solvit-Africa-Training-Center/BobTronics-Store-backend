from django.urls import path

from .admin_api import (
    AdminNotificationsView,
    AdminReportExportView,
    AdminReportSummaryView,
    AdminStoreSettingsView,
)

app_name = "common"

urlpatterns = [
    path("notifications/admin/", AdminNotificationsView.as_view(), name="admin-notifications"),
    path("reports/summary/", AdminReportSummaryView.as_view(), name="admin-report-summary"),
    path("reports/export/", AdminReportExportView.as_view(), name="admin-report-export"),
    path("settings/", AdminStoreSettingsView.as_view(), name="admin-store-settings"),
]
