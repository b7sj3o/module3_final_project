from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdminOrReadOnly(BasePermission):
    """Everyone can read; only staff can create, change or delete."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_staff)
