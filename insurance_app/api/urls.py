from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, import_customer_from_pdf
from django.urls import path

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customers')
# router.register(r'documents', Documents, basename='documents')


urlpatterns = router.urls + [
    path("import-customer-from-pdf/", import_customer_from_pdf, name="import-customer-from-pdf"),
]