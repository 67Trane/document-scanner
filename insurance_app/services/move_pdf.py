import os
import shutil


def move_pdf_to_customer_folder(pdf_path: str, customer) -> str:
    """
    Move a PDF file into a customer-specific folder.

    Returns the new absolute file path.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    base_dir = "media/customers"
    customer_dir = os.path.join(base_dir, f"customer_{customer.id}")

    os.makedirs(customer_dir, exist_ok=True)

    filename = os.path.basename(pdf_path)
    new_path = os.path.join(customer_dir, filename)

    shutil.move(pdf_path, new_path)

    return new_path
