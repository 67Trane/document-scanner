from rest_framework.permissions import BasePermission
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class IsInWhitelistGroup(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and u.groups.filter(name="whitelist").exists()
        )


class HasImportToken(BasePermission):
    def has_permission(self, request, view):
        token = request.headers.get("X-Import-Token", "")
        if not (bool(settings.DOCUMENT_IMPORT_TOKEN) and token == settings.DOCUMENT_IMPORT_TOKEN):
            return False

        broker_id = request.headers.get("X-Broker-Id", "")
        if not broker_id.isdigit():
            return False

        return User.objects.filter(id=int(broker_id), is_active=True).exists()
