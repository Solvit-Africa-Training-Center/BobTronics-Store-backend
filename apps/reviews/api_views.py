from rest_framework import mixins, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticatedOrReadOnly

from apps.accounts.models import Role

from .models import Feedback
from .serializers import FeedbackSerializer


class IsCustomerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.role == Role.CUSTOMER)


class FeedbackViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsCustomerOrReadOnly]

    def get_queryset(self):
        queryset = Feedback.objects.select_related("user", "product").all()
        product_id = self.request.query_params.get("product")
        return queryset.filter(product_id=product_id) if product_id else queryset
