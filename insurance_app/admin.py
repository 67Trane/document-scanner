from django.contrib import admin
from .models import Customer, InsuranceCompany, InsuranceType, Policy, Document

admin.site.register(Customer)
admin.site.register(InsuranceCompany)
admin.site.register(InsuranceType)
admin.site.register(Policy)
admin.site.register(Document)
