from rest_framework.permissions import BasePermission
from .models import Role


class IsCustomer(BasePermission):
    """Allow authenticated customer accounts to use customer self-service APIs."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.CUSTOMER)


class IsAdminOrSuperAdmin(BasePermission):
    """Allow API access only to accounts with an admin role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in (Role.ADMIN, Role.SUPER_ADMIN)
        )


class IsSuperAdmin(BasePermission):
    """Allow access only to super-admin accounts."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.SUPER_ADMIN)


class IsOwnerOrAdmin(BasePermission):
    """Allow customers to access their own records and admins to manage records."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role in (Role.ADMIN, Role.SUPER_ADMIN):
            return True
        if user.role != Role.CUSTOMER:
            return False
        if obj == user:
            return True
        owner = getattr(obj, "user", None)
        if owner is None:
            owner = getattr(getattr(obj, "order", None), "user", None)
        return owner == user
