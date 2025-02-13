from rest_framework import permissions


class is_moderator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class is_authenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated


class is_guest(permissions.BasePermission):
    def has_permission(self, request, view):
        return not request.user.is_authenticated


class is_admin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
