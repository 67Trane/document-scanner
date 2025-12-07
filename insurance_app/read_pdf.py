import pdfplumber
import re
from typing import Optional, Tuple


def extract_pdf_text(pdf_file: str) -> dict:
    with pdfplumber.open(pdf_file) as pdf:
        pages_text = []
        for page in pdf.pages:
            # page.extract_text() can return None
            pages_text.append(page.extract_text() or "")

    raw_text = "\n".join(pages_text)
    new_text = normalize_text(raw_text)

    # Extract name
    full_name = extract_name(new_text)
    first_name = ""
    last_name = ""

    if full_name:
        parts = full_name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Extract address parts (salutation, street, zip, city)
    salutation, street, zip_code, city = extract_address_parts(new_text)

    policy_number = extract_policy_number(new_text)
    license_plate = extract_license_plate(new_text)
    contract_type = extract_contract_type(new_text)

    return {
        "raw_text": raw_text,
        "normalized_text": new_text,

        # customer related
        "salutation": salutation,
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": None,
        "email": "",
        "phone": "",
        "street": street,
        "zip_code": zip_code,
        "city": city,
        "country": "Germany",

        # contract / vehicle
        "policy_number": policy_number,
        "license_plates": [license_plate] if license_plate else [],
        "contract_typ": contract_type,
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


def extract_name(text: str) -> Optional[str]:
    """
    Extract the full name from the address block:

        Herr/Frau <FirstName> <LastName>
        <Street>
        <ZIP> <City>
    """
    pattern = re.compile(
        r"(Herr|Frau)\s+([^\n]+)\n"          # salutation + name
        r"[A-ZÄÖÜ][^\n]+\n"                 # street
        r"\d{5}\s+[A-Za-zÄÖÜäöüß ]+"        # zip + city
    )

    match = pattern.search(text)
    if match:
        full_name = match.group(2).strip()
        return full_name

    # Fallback: "Sehr geehrter Herr Deliaci,"
    fallback = re.compile(r"Sehr geehrter\s+(Herr|Frau)\s+([A-ZÄÖÜ][^\s,]+)")
    m2 = fallback.search(text)
    if m2:
        return m2.group(2).strip()

    return None


def extract_address_parts(text: str) -> Tuple[str, str, str, str]:
    """
    Find:
        Herr/Frau <Name>
        <Street>
        <ZIP> <City>

    Returns (salutation, street, zip_code, city).
    If not found, returns empty strings.
    """
    pattern = re.compile(
        r"(Herr|Frau)\s+[^\n]+\n"          # salutation + name line
        r"([A-ZÄÖÜ][^\n]+)\n"             # street line
        r"(\d{5})\s+([A-Za-zÄÖÜäöüß ]+)"  # zip + city line
    )

    m = pattern.search(text)
    if not m:
        return "", "", "", ""

    salutation = m.group(1).strip()
    street = m.group(2).strip()
    zip_code = m.group(3).strip()
    city = m.group(4).strip()
    return salutation, street, zip_code, city


def extract_policy_number(text: str) -> Optional[str]:
    # e.g. "K 177-332804/1"
    pattern = re.compile(r"K\s*\d{3}-\d{6}/\d+")
    m = pattern.search(text)
    return m.group() if m else None


def extract_license_plate(text: str) -> Optional[str]:
    # e.g. "N-AB 1234"
    match = re.search(r"[A-Z]{1,3}-[A-Z]{1,2}\s*\d{1,4}", text)
    return match.group() if match else None


def extract_contract_type(text: str) -> Optional[str]:
    """
    Versucht, den Vertragstyp aus dem Text zu erkennen.
    Gibt einen der Keys aus deinem Django-CONTRACT_TYPES zurück
    (z.B. 'kfz', 'hausrat', 'haftpflicht', ...).
    """

    text_lower = text.lower()

    # Kfz-Versicherung: verschiedene Schreibweisen abdecken
    if (
        "kfz-versicherung" in text_lower
        or "kfz versicherung" in text_lower
        or "kfz" in text_lower and "versicherung" in text_lower
        or "kennzeichen" in text_lower
        or "teilkasko" in text_lower
        or "haftpflicht" in text_lower and "kfz" in text_lower
    ):
        return "Kfz-Versicherung"

    # Hausrat
    if re.search(r"\bhausrat\b", text_lower) or "hausratversicherung" in text_lower:
        return "hausrat"

    # Privat-Haftpflicht
    if "privathaftpflicht" in text_lower or re.search(r"\bhaftpflicht\b", text_lower):
        return "haftpflicht"

    # Rechtsschutz
    if "rechtsschutz" in text_lower or "rechtschutz" in text_lower:
        return "rechtschutz"

    # Wohngebäude
    if "wohngebäude" in text_lower or "wohngebaeude" in text_lower:
        return "wohngebaeude"

    # Unfall
    if "unfallversicherung" in text_lower or "gliedertaxe" in text_lower:
        return "unfall"

    # BU
    if "berufsunfähigkeit" in text_lower or "berufsunfaehigkeit" in text_lower or "bu-rente" in text_lower:
        return "berufsunfaehigkeit"

    # PKV
    if "private krankenversicherung" in text_lower or "krankenvollversicherung" in text_lower or "pkv" in text_lower:
        return "krankenversicherung"

    return None
