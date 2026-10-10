"""PyMuPDF helpers: PDF to page text, page text to clause chunks."""
import re

import pymupdf

from app.schemas import Clause

# "4.1 Turnover", "1. Scope", "4.1: Turnover", "4.1 - Turnover", "Clause 4.1 Turnover", "2. योग्यता"
HEADING = re.compile(
    r"^\s*(?P<kw>clause\s+)?(?P<num>\d{1,2}(?:\.\d{1,2}){0,3})\s*(?P<sep>[.):\-\u2013]?)\s*(?P<rest>.*)$",
    re.IGNORECASE)

# Wrapped lines like "50 Lakhs in the last...", "31 March 2026", "3 years from..." are not headings.
NOT_HEADING_WORDS = {
    "lakh", "lakhs", "crore", "crores", "rs", "inr", "rupees", "percent", "year", "years", "month", "months",
    "week", "weeks", "day", "days", "hrs", "hours", "nos", "no", "numbers", "units", "pcs", "kg", "km",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}


def heading_number(line: str) -> str | None:
    """The clause number if this line starts a numbered clause, else None."""
    m = HEADING.match(line)
    if not m:
        return None
    rest = m.group("rest")
    if not rest or not (rest[0] == "(" or rest[0].isalpha()):
        return None
    # A bare "1 LED Tube Light" (BOQ row) is not a heading; "1. Scope" or "4.1 Scope" is.
    if "." not in m.group("num") and not m.group("sep") and not m.group("kw"):
        return None
    if rest.split()[0].strip(".,:;").lower() in NOT_HEADING_WORDS:
        return None
    return m.group("num")


class ScannedPDFError(ValueError):
    def __init__(self):
        super().__init__("This looks like a scanned PDF; please use a text PDF")


def pdf_to_pages(path: str) -> list[str]:
    """Text of each page, in order. Raises ScannedPDFError when there is no text at all."""
    with pymupdf.open(path) as doc:
        if not doc.is_pdf:   # PyMuPDF also opens text, XPS and image files
            raise ValueError("Please upload a PDF file")
        pages = [page.get_text() for page in doc]
    if not any(p.strip() for p in pages):
        raise ScannedPDFError()
    return pages


def pages_to_clauses(pages: list[str]) -> list[Clause]:
    """Split on numbered headings; a clause keeps the page it starts on and runs across pages."""
    clauses: list[dict] = []
    for page_no, text in enumerate(pages, 1):
        for line in text.splitlines():
            number = heading_number(line)
            if number is not None or not clauses:
                clauses.append({"clause": number or "", "page": page_no, "lines": []})
            clauses[-1]["lines"].append(line.strip())
    return [
        Clause(text=text, clause=c["clause"], page=c["page"])
        for c in clauses
        if (text := "\n".join(l for l in c["lines"] if l))
    ]
