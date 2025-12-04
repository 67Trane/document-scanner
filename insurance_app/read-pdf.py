import pdfplumber
import re


def extract_pdf_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


pdf_path = "C:/Users/67Trane/epson-test/test_run.pdf"
text = extract_pdf_text(pdf_path)
print(text)


def search_in_text(text: str, query: str, context_chars: int = 40):
    """
    Simple text search with small context around each hit.
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []

    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        snippet = text[start:end].replace("\n", " ")

        results.append({
            "match": match.group(),
            "start": match.start(),
            "end": match.end(),
            "snippet": snippet,
        })

    return results


gesucht = search_in_text(text, "k 177")
print("HIIIIIIIER", gesucht)
