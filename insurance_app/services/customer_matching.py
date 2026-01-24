from django.db import transaction, IntegrityError
from ..models import Customer
from ..api.serializers import CustomerSerializer


class AmbiguousCustomerError(Exception):
    def __init__(self, candidates):
        self.candidates = candidates


class UnresolvedCustomerError(Exception):
    pass


def find_or_create_customer(customer_data: dict, broker):
    """Find a customer by OCR-derived data or create one if none exists."""
    first_name = (customer_data.get("first_name") or "").strip()
    last_name = (customer_data.get("last_name") or "").strip()
    zip_code = (customer_data.get("zip_code") or "").strip()
    street = (customer_data.get("street") or "").strip()

    has_name = bool(first_name and last_name)
    has_address = bool(street and zip_code)

    # IMPORTANT: If we have neither reliable name nor address, do not guess.
    if not has_name and not has_address:
        raise UnresolvedCustomerError(
            "Not enough OCR data to resolve customer.")

    # 1) Address-based candidates (OCR-robust) - only if address exists
    if has_address:
        candidates = Customer.objects.filter(
            broker=broker,  # NEW
            street__iexact=street,
            zip_code=zip_code,
        )

        if candidates.count() == 1:
            return candidates.first(), False

        if candidates.count() > 1:
            raise AmbiguousCustomerError(candidates)

    # 2) Exact lookup (only with non-empty fields)
    lookup = {
        "broker": broker,
        "first_name": first_name,
        "last_name": last_name,
        "zip_code": zip_code,
        "street": street,
    }
    lookup = {k: v for k, v in lookup.items() if v}

    if not lookup:
        raise UnresolvedCustomerError("Lookup is empty after normalization.")

    customer = Customer.objects.filter(**lookup).first()
    if customer:
        return customer, False

    # 3) Create (race-safe)
    try:
        with transaction.atomic():
            serializer = CustomerSerializer(data=customer_data)
            serializer.is_valid(raise_exception=True)
            return serializer.save(broker=broker), True
    except IntegrityError:
        return Customer.objects.get(**lookup), False
