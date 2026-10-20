from django.urls import path

from .views import (
    AdminReviewDetailView,
    AdminReviewListView,
    ReviewDetailView,
    ReviewListCreateView,
)

app_name = "reviews"

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="review-list"),
    path("admin/", AdminReviewListView.as_view(), name="admin-review-list"),
    path("admin/<int:feedback_id>/", AdminReviewDetailView.as_view(), name="admin-review-detail"),
    path("<int:feedback_id>/", ReviewDetailView.as_view(), name="review-detail"),
]
