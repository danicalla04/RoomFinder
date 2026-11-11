from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and (request.user.role == "admin" or request.user.is_superuser)
        )


def admin(user):
    return user.is_authenticated and (user.role == "admin" or user.is_superuser)


def manages(user, hotel):
    return admin(user) or (
        user.is_authenticated and user.role == "owner" and hotel.owner_id == user.id
    )
