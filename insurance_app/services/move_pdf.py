import os
import shutil
from django.conf import settings


def move_pdf_to_customer_folder(pdf_path: str, customer) -> str:
    # IMPORTANT: store files under configured root (env-based)
    base_dir = getattr(settings, "CUSTOMER_DOCUMENT_ROOT", None)
    if not base_dir:
        raise ValueError("CUSTOMER_DOCUMENT_ROOT is not configured in Django settings.")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    customer_dir = os.path.join(
        base_dir, f"{customer.customer_number}_{customer.last_name}"
    )
    os.makedirs(customer_dir, exist_ok=True)

    filename = os.path.basename(pdf_path)
    new_path = os.path.join(customer_dir, filename)

    shutil.move(pdf_path, new_path)

    return new_path
