from rest_framework.permissions import BasePermission
from django.conf import settings

class IsInWhitelistGroup(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.groups.filter(name="whitelist").exists())

class HasImportToken(BasePermission):
    def has_permission(self, request, view):
        token = request.headers.get("X-Import-Token", "")
        return bool(settings.DOCUMENT_IMPORT_TOKEN) and token == settings.DOCUMENT_IMPORT_TOKEN

