from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet,
    DocumentViewSet,
    DocumentImportView,
    DocumentFileView,
    PublicCustomerView,
    PublicDocumentFileView,
    CustomerShareLinkListCreateView, 
    CustomerShareLinkDeactivateView
    
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
    path("public/customer/<str:token>/", PublicCustomerView.as_view(), name="public-customer"),
    path("public/customer/<str:token>/document/<int:document_id>/file/", PublicDocumentFileView.as_view(), name="public-doc-file"),
    path("customers/<int:customer_id>/share-links/", CustomerShareLinkListCreateView.as_view(), name="customer-share-links"),
    path("customers/<int:customer_id>/share-links/<int:link_id>/deactivate/", CustomerShareLinkDeactivateView.as_view(), name="customer-share-link-deactivate"),
]
