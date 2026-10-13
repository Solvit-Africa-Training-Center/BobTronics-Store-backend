from rest_framework.permissions import BasePermission
from .models import Role


class IsAdminOrSuperAdmin(BasePermission):
    """
    Allows access only to authenticated users who have ADMIN or SUPER_ADMIN role,
    or is_staff=True.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.role in [Role.ADMIN, Role.SUPER_ADMIN]
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission allowing users to access only their own objects,
    unless they have administrative privileges.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if (
            request.user.role in [Role.ADMIN, Role.SUPER_ADMIN]
            or request.user.is_staff
            or request.user.is_superuser
        ):
            return True
        return hasattr(obj, "user") and obj.user == request.user or obj == request.user
