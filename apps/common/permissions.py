from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsAdminRole(BasePermission):
    """
    Allows access only to authenticated, active users whose role
    is `admin` or `super_admin`.
    """

    message = "Access to this action is not allowed."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in (Role.ADMIN, Role.SUPER_ADMIN)
        )
