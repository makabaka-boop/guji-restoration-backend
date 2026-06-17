from rest_framework.permissions import BasePermission
from .models import ROLE_ADMIN, ROLE_RESTORER, ROLE_REVIEWER


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == ROLE_ADMIN


class IsRestorer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == ROLE_RESTORER


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == ROLE_REVIEWER


class IsAdminOrRestorer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [ROLE_ADMIN, ROLE_RESTORER]


class IsAdminOrReviewer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [ROLE_ADMIN, ROLE_REVIEWER]


class IsAdminOrSelfRestorer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == ROLE_ADMIN or request.user.role == ROLE_RESTORER
        )
