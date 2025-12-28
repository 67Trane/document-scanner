from django.contrib import admin
from .models import Customer, Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "contract_typ", "contract_status", "created_at")
    list_filter = ("contract_typ", "contract_status")
    search_fields = (
        "customer__first_name",
        "customer__last_name",
        "customer__customer_number",
        "policy_numbers",
    )



@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "customer_number",
        "first_name",
        "last_name",
        "email",
        "city",
        "active_status",
    )
