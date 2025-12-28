from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet,
    DocumentViewSet,
    DocumentImportView,
    DocumentFileView,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "import-document-from-pdf/",
        DocumentImportView.as_view(),
        name="import_document_from_pdf",
    ),
    path("documents/<int:pk>/file/", DocumentFileView.as_view(), name="document_file"),
]
