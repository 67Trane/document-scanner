# customers/services.py
from __future__ import annotations

import time
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from .models import Customer


# Entweder absoluter Pfad, oder aus settings laden:
CUSTOMER_DOCUMENT_ROOT = Path(
    getattr(settings, "CUSTOMER_DOCUMENT_ROOT", "/Kunden/Dokumente"))


def build_customer_folder_name(customer: Customer) -> str:
    """
    Build a stable and filesystem-safe folder name for a customer.
    Example: "mustermann_max_2025-000123"
    """
    base = f"{customer.last_name}_{customer.first_name}".strip()

    customer_number = getattr(customer, "customer_number", None)
    if customer_number:
        base = f"{base}_{customer_number}"

    # slugify removes spaces and special characters
    slug = slugify(base)  # -> "mustermann_max_2025-000123"
    if not slug:
        # Fallback if names are missing for some reason
        slug = f"customer_{customer.pk}"

    return slug


def move_pdf_to_customer_folder(pdf_path_str: str, customer: Customer) -> str:
    """
    Move the given PDF file into the customer's folder
    and return the new absolute file path as string.
    """
    pdf_path = Path(pdf_path_str)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")

    # Determine target folder
    folder_name = build_customer_folder_name(customer)
    customer_folder = CUSTOMER_DOCUMENT_ROOT / folder_name
    customer_folder.mkdir(parents=True, exist_ok=True)

    # Determine target file path
    target_path = customer_folder / pdf_path.name

    # Avoid overwriting existing files
    if target_path.exists():
        timestamp = int(time.time())
        target_path = customer_folder / \
            f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"

    # Atomic move on same filesystem
    pdf_path.rename(target_path)

    return str(target_path)
