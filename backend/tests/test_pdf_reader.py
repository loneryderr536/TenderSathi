import pytest

from app.pdf_reader import ScannedPDFError, pages_to_clauses, pdf_to_pages
from tests.pdfs import make_pdf


def test_pages_extracted_in_order(tmp_path):
    path = make_pdf(tmp_path, ["Page one text", "Page two text"])
    pages = pdf_to_pages(path)
    assert len(pages) == 2 and "Page one" in pages[0] and "Page two" in pages[1]


def test_scanned_pdf_rejected(tmp_path):
    path = make_pdf(tmp_path, ["", ""])
    with pytest.raises(ScannedPDFError, match="This looks like a scanned PDF; please use a text PDF"):
        pdf_to_pages(path)


def test_clauses_split_on_numbered_headings():
    pages = ["Notice inviting tender\n1. Scope\nSupply 200 desks.\n4.1 Turnover of Rs 1 crore\n",
             "continued on page two\n4.2 ISO 9001 certificate\n"]
    clauses = pages_to_clauses(pages)
    assert [(c.clause, c.page) for c in clauses] == [("", 1), ("1", 1), ("4.1", 1), ("4.2", 2)]
    assert "continued on page two" in clauses[2].text
    assert "Supply 200 desks." in clauses[1].text


def test_numbers_that_are_not_headings():
    clauses = pages_to_clauses(["1. Scope\n2026 onwards the rate applies\n50,000 rupees EMD\n"])
    assert len(clauses) == 1


@pytest.mark.parametrize("line", [
    "50 Lakhs in the last three financial years",
    "31 March 2026 by 15:00 hrs",
    "3 years from date of supply",
    "1 LED Tube Light 20W",
    "10 Nos of desks",
])
def test_wrapped_lines_are_not_headings(line):
    clauses = pages_to_clauses([f"4.1 Turnover of Rs.\n{line}\n"])
    assert [c.clause for c in clauses] == ["4.1"]


@pytest.mark.parametrize("line,number", [
    ("4.1: Turnover", "4.1"), ("4.1 - Turnover", "4.1"), ("4.1.Turnover", "4.1"),
    ("Clause 4.1 Turnover", "4.1"), ("2. योग्यता", "2"),
])
def test_heading_variants(line, number):
    assert [c.clause for c in pages_to_clauses([line])] == [number]
