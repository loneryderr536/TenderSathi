"""Builds small text PDFs for tests."""
import pymupdf


def make_pdf(tmp_path, pages, name="tender.pdf"):
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    path = str(tmp_path / name)
    doc.save(path)
    return path
