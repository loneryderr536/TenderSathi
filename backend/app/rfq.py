"""Turns a private owner's request-for-quotation form into a tender PDF, so every agent can read it."""
import textwrap
from pathlib import Path

import pymupdf

MIN_ADVANCE, MAX_ADVANCE = 25, 50   # every private owner pays 25-50% of the order value in advance

PAGE_W, PAGE_H, MARGIN, LINE_H, WRAP, PER_PAGE = 595, 842, 56, 15, 92, 46


def rfq_lines(buyer: str, title: str, scope: str, requirements: list[str], documents: list[str],
              deadline: str, delivery_days: int, advance_percent: int) -> list[str]:
    """Numbered clauses in the same layout as a government tender, so the Reader finds rules and pages."""
    lines = [buyer, f"Request for Quotation: {title}", "1. Scope of work", scope,
             "3. Important dates", f"Last date and time for quotations: {deadline}.", "4. Eligibility criteria"]
    lines += [f"4.{i} {r.rstrip('.')}. Mandatory." for i, r in enumerate(requirements, 1)] or ["4.1 None."]
    lines += ["5. Documents to be submitted", "; ".join(documents) + "." if documents else "None.",
              "6. Earnest money deposit (EMD)", "No EMD is required for this request for quotation.",
              "7. Payment terms",
              f"An advance of {advance_percent}% of the order value will be paid when the order is placed. "
              "The balance will be paid within 30 days of delivery and acceptance.",
              "8. Delivery", f"Delivery within {delivery_days} days of the order."]
    return lines


def write_rfq_pdf(path: Path, lines: list[str]) -> None:
    body = []
    for line in lines:
        body += textwrap.wrap(line, WRAP) or [""]
        body.append("")
    doc = pymupdf.open()
    for start in range(0, len(body), PER_PAGE):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        page.insert_text((MARGIN, MARGIN - 20), "Request for Quotation - posted on TenderSathi by a private owner",
                         fontsize=8, color=(0.2, 0.3, 0.6))
        y = MARGIN
        for text in body[start:start + PER_PAGE]:
            page.insert_text((MARGIN, y), text, fontsize=10)
            y += LINE_H
        page.insert_text((PAGE_W / 2 - 20, PAGE_H - 30), f"Page {page.number + 1}", fontsize=8)
    doc.save(str(path))
