import pdfplumber
import re


def extract_pdf_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    new_text = normalize_text(text)
    name = extract_name(new_text)
    address = extract_address(new_text)
    policy_number = extract_policy_number(new_text)
    license_plate = extract_license_plate(new_text)
    return {
        "text": new_text,
        "name": name,
        "policy_number": policy_number,
        "address": address,
        "license_plate": license_plate
    }


def normalize_text(text: str) -> str:
    text = text.replace("\r", "")

    # Mehrfache Leerzeichen entfernen
    text = re.sub(r"[ \t]+", " ", text)

    # Doppelte Zeilenumbrüche entfernen
    text = re.sub(r"\n{2,}", "\n", text)

    # "Herr\nIsa Deliaci" -> "Herr Isa Deliaci"
    text = re.sub(r"(Herr|Frau)\s*\n\s*([A-ZÄÖÜ])", r"\1 \2", text)

    # OCR-Müll rausfiltern
    text = re.sub(r"[^0-9A-Za-zÄÖÜäöüß.,:/()\-\n ]", "", text)

    return text


def extract_name(text: str) -> str | None:
    pattern = re.compile(
        r"(Herr|Frau) [A-ZÄÖÜ][a-zäöüß]+(?: [A-ZÄÖÜ][a-zäöüß]+){1,2}"
    )
    match = pattern.search(text)
    return match.group() if match else None


def extract_address(text: str) -> str | None:
    """
    Sucht die Adresse direkt im Block nach 'Herr/Frau <Name>'.
    Gibt z.B. 'Nördliche Ringstr. 23, 91781 Weißenburg' zurück.
    """
    # Suche: Herr/Frau Name \n <Straße> \n <PLZ Ort>
    m = re.search(
        r"(Herr|Frau) [^\n]+\n([A-ZÄÖÜ][^\n]+)\n(\d{5}\s+[A-Za-zÄÖÜäöüß ]+)",
        text
    )
    if m:
        street = m.group(2).strip()
        city = m.group(3).strip()
        return f"{street}, {city}"

    # Fallback: erste PLZ + Ort, falls das Muster oben nicht greift
    m = re.search(r"\d{5}\s+[A-Za-zÄÖÜäöüß ]+", text)
    return m.group().strip() if m else None


def extract_policy_number(text: str) -> str | None:
    pattern = re.compile(r"K\s*\d{3}-\d{6}/\d+")
    m = pattern.search(text)
    return m.group() if m else None


def extract_license_plate(text):
    match = re.search(r"[A-Z]{1,3}-[A-Z]{1,2}\s*\d{1,4}", text)
    return match.group() if match else None


pdf_path = "C:/Users/67Trane/epson-test/test_run.pdf"
text = extract_pdf_text(pdf_path)
print(text)


# def search_in_text(text: str, query: str, context_chars: int = 40):
#     """
#     Simple text search with small context around each hit.
#     """
#     pattern = re.compile(re.escape(query), re.IGNORECASE)
#     results = []

#     for match in pattern.finditer(text):
#         start = max(0, match.start() - context_chars)
#         end = min(len(text), match.end() + context_chars)
#         snippet = text[start:end].replace("\n", " ")

#         results.append({
#             "match": match.group(),
#             "start": match.start(),
#             "end": match.end(),
#             "snippet": snippet,
#         })

#     return results


# gesucht = search_in_text(text, "k 177")
# print("HIIIIIIIER", gesucht)
