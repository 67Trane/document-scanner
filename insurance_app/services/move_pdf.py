# move_pdf.py
import os
import shutil
from datetime import datetime
from django.conf import settings


def _safe_folder_name(value: str) -> str:
    # Keep folder names simple & filesystem-safe
    value = (value or "").strip()
    value = value.replace("/", "-").replace("\\", "-")
    return value or "unknown"


def move_pdf_to_customer_folder(pdf_path: str, customer, filename_hint: str | None = None) -> str:
    """Move a PDF into the customer folder and return the new path."""
    # IMPORTANT: store files under configured root (env-based)
    base_dir = getattr(settings, "CUSTOMER_DOCUMENT_ROOT", None)
    if not base_dir:
        raise ValueError(
            "CUSTOMER_DOCUMENT_ROOT is not configured in Django settings.")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    # --- Broker folder (isolation) ---
    broker_dir = os.path.join(str(base_dir), f"broker_{customer.broker_id}")

    # --- Customer folder ---
    customer_no = _safe_folder_name(customer.customer_number)
    last_name = _safe_folder_name(customer.last_name)
    customer_dir = os.path.join(broker_dir, f"{customer_no}_{last_name}")

    os.makedirs(customer_dir, exist_ok=True)

    # --- Filename ---
    original_name = os.path.basename(pdf_path)
    ext = os.path.splitext(original_name)[1].lower() or ".pdf"

    if filename_hint:
        stem = _safe_folder_name(filename_hint)
    else:
        # Keep traceable, avoid collisions
        stem = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    new_path = os.path.join(customer_dir, f"{stem}{ext}")

    # If file exists, add suffix
    counter = 1
    while os.path.exists(new_path):
        new_path = os.path.join(customer_dir, f"{stem}_{counter}{ext}")
        counter += 1

    shutil.move(pdf_path, new_path)
    return new_path


def move_pdf_to_unassigned_folder(pdf_path: str) -> str:
    # IMPORTANT: store unassigned files in a dedicated inbox folder
    base_dir = getattr(settings, "UNASSIGNED_DOCUMENT_ROOT", None)
    if not base_dir:
        raise ValueError(
            "UNASSIGNED_DOCUMENT_ROOT is not configured in Django settings.")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    os.makedirs(base_dir, exist_ok=True)

    filename = os.path.basename(pdf_path)
    new_path = os.path.join(base_dir, filename)

    shutil.move(pdf_path, new_path)
    return new_path
