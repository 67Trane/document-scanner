import pdfplumber
import re
from typing import Optional, Tuple


def extract_pdf_text(pdf_file: str) -> dict:
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    new_text = normalize_text(text)

    # Extract name
    full_name = extract_name(new_text)
    first_name = ""
    last_name = ""

    if full_name:
        parts = full_name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Extract address parts (street, zip, city)
    salutation, street, zip_code, city = extract_address_parts(new_text)

    policy_number = extract_policy_number(new_text)
    license_plate = extract_license_plate(new_text)


    return {
        "salutation": salutation,
        "first_name": first_name,
        "last_name": last_name,
        "policy_number": policy_number,
        "date_of_birth": None,
        "email": "",
        "phone": "",
        "street": street,
        "zip_code": zip_code,
        "city": city,
        "country": "Germany",
        "license_plates": [license_plate],
    }


def normalize_text(text: str) -> str:
    text = text.replace("\r", "")

    # Remove multiple spaces / tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove double empty lines
    text = re.sub(r"\n{2,}", "\n", text)

    # Join "Herr\n Isa" -> "Herr Isa"
    text = re.sub(r"(Herr|Frau)\s*\n\s*([A-ZÄÖÜ])", r"\1 \2", text)

    # Filter out OCR garbage
    text = re.sub(r"[^0-9A-Za-zÄÖÜäöüß.,:/()\-\n ]", "", text)

    return text


def extract_name(text: str) -> str | None:
    """
    Holt den Namen aus dem Adressblock:

        Herr/Frau <Vorname> <Nachname>
        <Straße>
        <PLZ> <Ort>
    """
    pattern = re.compile(
        r"(Herr|Frau)\s+([^\n]+)\n"          # Anrede + Name
        r"[A-ZÄÖÜ][^\n]+\n"                 # Straße
        r"\d{5}\s+[A-Za-zÄÖÜäöüß ]+"        # PLZ + Ort
    )

    match = pattern.search(text)
    if match:
        full_name = match.group(2).strip()
        return full_name

    # Fallback: falls aus irgendeinem Grund der Block nicht gefunden wird,
    # nimm die Anrede-Zeile ("Sehr geehrter Herr Deliaci,") – aber nur den Namen
    fallback = re.compile(r"Sehr geehrter\s+(Herr|Frau)\s+([A-ZÄÖÜ][^\s,]+)")
    m2 = fallback.search(text)
    if m2:
        return m2.group(2).strip()

    return None


def extract_address_parts(text: str) -> Tuple[str, str, str]:
    """
    Find:
        Herr/Frau <Name>
        <Street>
        <ZIP> <City>

    Returns (street, zip_code, city).
    If not found, returns empty strings.
    """
    pattern = re.compile(
        r"(Herr|Frau)\s+[^\n]+\n"          # salutation + name line
        r"([A-ZÄÖÜ][^\n]+)\n"             # street line
        r"(\d{5})\s+([A-Za-zÄÖÜäöüß ]+)"  # zip + city line
    )

    m = pattern.search(text)
    if not m:
        return "", "", ""

    salutation = m.group(1).strip()
    street = m.group(2).strip()
    zip_code = m.group(3).strip()
    city = m.group(4).strip()
    return salutation ,street, zip_code, city


def extract_policy_number(text: str) -> Optional[str]:
    pattern = re.compile(r"K\s*\d{3}-\d{6}/\d+")
    m = pattern.search(text)
    return m.group() if m else None


def extract_license_plate(text: str) -> Optional[str]:
    match = re.search(r"[A-Z]{1,3}-[A-Z]{1,2}\s*\d{1,4}", text)
    return match.group() if match else None
