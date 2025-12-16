from django.db import transaction, IntegrityError
from ..models import Customer
from ..api.serializers import CustomerSerializer


class AmbiguousCustomerError(Exception):
    def __init__(self, candidates):
        self.candidates = candidates


def find_or_create_customer(customer_data: dict):
    first_name = (customer_data.get("first_name") or "").strip()
    last_name = (customer_data.get("last_name") or "").strip()
    zip_code = (customer_data.get("zip_code") or "").strip()
    street = (customer_data.get("street") or "").strip()

    # 1) Address-based candidates (OCR-robust)
    candidates = Customer.objects.filter(
        street__iexact=street,
        zip_code=zip_code,
    )

    if candidates.count() == 1:
        return candidates.first(), False

    if candidates.count() > 1:
        raise AmbiguousCustomerError(candidates)

    # 2) Exact lookup
    lookup = {
        "first_name": first_name,
        "last_name": last_name,
        "zip_code": zip_code,
        "street": street,
    }
    lookup = {k: v for k, v in lookup.items() if v}

    customer = Customer.objects.filter(**lookup).first()
    if customer:
        return customer, False

    # 3) Create (race-safe)
    try:
        with transaction.atomic():
            serializer = CustomerSerializer(data=customer_data)
            serializer.is_valid(raise_exception=True)
            return serializer.save(), True
    except IntegrityError:
        return Customer.objects.get(**lookup), False
