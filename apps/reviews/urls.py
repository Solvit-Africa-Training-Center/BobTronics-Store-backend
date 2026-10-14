from rest_framework.routers import DefaultRouter

from .api_views import FeedbackViewSet

router = DefaultRouter()
router.register("", FeedbackViewSet, basename="feedback")
urlpatterns = router.urls
