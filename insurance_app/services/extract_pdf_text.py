from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

import pdfplumber


# -------------------------
# Regex constants (compiled)
# -------------------------

RE_MULTI_SPACE = re.compile(r"[ \t]+")
RE_MULTI_NEWLINES = re.compile(r"\n{2,}")
RE_JOIN_SALUTATION_LINEBREAK = re.compile(r"(Herr|Frau)\s*\n\s*([A-ZÄÖÜ])")

# Keep newlines, keep common punctuation, strip weird OCR artifacts
RE_OCR_GARBAGE = re.compile(r"[^0-9A-Za-zÄÖÜäöüß.,:/()\-\n ]")

# Address block:
#   Herr/Frau <Name>
#   <Street>
#   <ZIP> <City>
RE_ADDRESS_BLOCK = re.compile(
    r"(?m)^(Herr|Frau)\s+([^\n]+)\n"  # salutation + name
    r"([A-ZÄÖÜ][^\n]+)\n"  # street
    r"(\d{5})\s+([A-Za-zÄÖÜäöüß ]+)\s*$"  # zip + city
)

# Fallback greeting (less reliable; last name only often)
RE_GREETING_FALLBACK = re.compile(r"Sehr geehrter\s+(Herr|Frau)\s+([A-ZÄÖÜ][^\s,]+)")

# Policy number example: "K 177-332804/1"
RE_POLICY_NUMBER = re.compile(r"\bK\s*\d{3}-\d{6}/\d+\b")

# License plate example: "N-AB 1234" (basic DE pattern-ish)
RE_LICENSE_PLATE = re.compile(r"\b[A-Z]{1,3}-[A-Z]{1,2}\s*\d{1,4}\b")


# -------------------------
# Output structure
# -------------------------


@dataclass(frozen=True)
class ExtractedPDFData:
    raw_text: str
    normalized_text: str

    # Customer related
    salutation: str = ""
    first_name: str = ""
    last_name: str = ""
    date_of_birth: Optional[str] = None
    email: str = ""
    phone: str = ""
    street: str = ""
    zip_code: str = ""
    city: str = ""
    country: str = "Germany"

    # Contract / vehicle
    policy_numbers: Optional[str] = None
    license_plates: List[str] = None
    contract_typ: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        # Ensure list default is not None
        if data["license_plates"] is None:
            data["license_plates"] = []
        return data


# -------------------------
# Public API
# -------------------------


def extract_pdf_text(pdf_file: str) -> dict:
    """Extract structured data from a PDF and return a dict payload."""
    raw_text = _read_pdf_text(pdf_file)
    normalized = normalize_text(raw_text)

    address = _extract_address_block(normalized)
    first_name, last_name = _split_name(address.name) if address else ("", "")

    policy_numbers = extract_policy_numbers(normalized)
    license_plate = extract_license_plate(normalized)
    contract_type = extract_contract_type(normalized)

    result = ExtractedPDFData(
        raw_text=raw_text,
        normalized_text=normalized,
        salutation=address.salutation if address else "",
        first_name=first_name,
        last_name=last_name,
        street=address.street if address else "",
        zip_code=address.zip_code if address else "",
        city=address.city if address else "",
        policy_numbers=policy_numbers,
        license_plates=[license_plate] if license_plate else [],
        contract_typ=contract_type,
    )
    return result.to_dict()


# -------------------------
# Reading / normalization
# -------------------------


def _read_pdf_text(pdf_file: str) -> str:
    with pdfplumber.open(pdf_file) as pdf:
        pages = [(page.extract_text() or "") for page in pdf.pages]
    return "\n".join(pages)


def normalize_text(text: str) -> str:
    """Normalize OCR text for downstream parsing."""
    text = text.replace("\r", "")
    text = RE_MULTI_SPACE.sub(" ", text)
    text = RE_MULTI_NEWLINES.sub("\n", text)
    text = RE_JOIN_SALUTATION_LINEBREAK.sub(r"\1 \2", text)
    text = RE_OCR_GARBAGE.sub("", text)
    return text.strip()


# -------------------------
# Address parsing
# -------------------------


@dataclass(frozen=True)
class AddressBlock:
    salutation: str
    name: str
    street: str
    zip_code: str
    city: str


def _extract_address_block(text: str) -> Optional[AddressBlock]:
    m = RE_ADDRESS_BLOCK.search(text)
    if m:
        return AddressBlock(
            salutation=m.group(1).strip(),
            name=m.group(2).strip(),
            street=m.group(3).strip(),
            zip_code=m.group(4).strip(),
            city=m.group(5).strip(),
        )

    # Fallback: only gets salutation + a single name token (often last name)
    m2 = RE_GREETING_FALLBACK.search(text)
    if m2:
        return AddressBlock(
            salutation=m2.group(1).strip(),
            name=m2.group(2).strip(),
            street="",
            zip_code="",
            city="",
        )

    return None


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.split()
    if not parts:
        return "", ""
    first = parts[0]
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first, last


# -------------------------
# Other extractors
# -------------------------


def extract_policy_numbers(text: str) -> Optional[str]:
    """Return the first matching policy number, if any."""
    m = RE_POLICY_NUMBER.search(text)
    return m.group(0) if m else None


def extract_license_plate(text: str) -> Optional[str]:
    """Return the first matching license plate, if any."""
    m = RE_LICENSE_PLATE.search(text)
    return m.group(0) if m else None


# -------------------------
# Contract type detection
# -------------------------

CONTRACT_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    # Returned values should match your Django CONTRACT_TYPES keys (or whatever you want)
    (
        "kfz",
        [
            re.compile(r"\bkfz\b", re.I),
            re.compile(r"kfz[-\s]?versicherung", re.I),
            re.compile(r"\bkennzeichen\b", re.I),
            re.compile(r"\bteilkasko\b", re.I),
        ],
    ),
    (
        "hausrat",
        [
            re.compile(r"\bhausrat\b", re.I),
            re.compile(r"hausratversicherung", re.I),
        ],
    ),
    (
        "haftpflicht",
        [
            re.compile(r"privathaftpflicht", re.I),
            re.compile(r"\bhaftpflicht\b", re.I),
        ],
    ),
    (
        "rechtsschutz",
        [
            re.compile(r"rechtsschutz|rechtschutz", re.I),
        ],
    ),
    (
        "wohngebaeude",
        [
            re.compile(r"wohngebäude|wohngebaeude", re.I),
        ],
    ),
    (
        "unfall",
        [
            re.compile(r"unfallversicherung|gliedertaxe", re.I),
        ],
    ),
    (
        "berufsunfaehigkeit",
        [
            re.compile(r"berufsunfähigkeit|berufsunfaehigkeit|bu-rente", re.I),
        ],
    ),
    (
        "krankenversicherung",
        [
            re.compile(
                r"private krankenversicherung|krankenvollversicherung|\bpkv\b", re.I
            ),
        ],
    ),
]


def extract_contract_type(text: str) -> Optional[str]:
    """Return the first matching contract type key, if any."""
    for contract_key, patterns in CONTRACT_RULES:
        if any(p.search(text) for p in patterns):
            return contract_key
    return None
