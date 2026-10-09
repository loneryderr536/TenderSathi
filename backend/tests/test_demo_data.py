"""The committed demo tenders parse cleanly, and the loader puts them into storage."""
import json
from pathlib import Path

import pytest

from app import db, demo
from app.pdf_reader import pages_to_clauses, pdf_to_pages

DATA = Path(__file__).resolve().parents[2] / "data"
TENDERS = {
    "school_desks.pdf": ["4.1", "4.2", "4.3", "4.4"],
    "hospital_beds.pdf": ["4.1", "4.2", "4.3"],
    "office_workstations.pdf": ["4.1", "4.2", "4.3"],
}


@pytest.mark.parametrize("name,rules", TENDERS.items())
def test_demo_tender_clauses(name, rules):
    pages = pdf_to_pages(str(DATA / "tenders" / name))
    assert len(pages) >= 2
    clauses = pages_to_clauses(pages)
    numbers = [c.clause for c in clauses]
    assert all(r in numbers for r in rules)
    assert len(numbers) == len(set(numbers)), f"duplicate or bogus clause numbers: {numbers}"
    assert "SAMPLE TENDER" in pages[0]


def test_demo_company_profile_is_valid():
    company = json.loads((DATA / "company" / "demo_company.json").read_text())
    assert company["name"] and company["documents"] and company["past_orders"]


def test_load_demo_is_idempotent(tmp_path):
    conn = db.connect(":memory:")
    company_id, tender_ids = demo.load_demo(conn, tmp_path, DATA)
    assert db.get_company(conn, company_id)["name"] == "Ernakulam Woodworks"
    assert len(tender_ids) == 3
    assert {t["title"] for t in db.list_tenders(conn)} == {
        "Supply of 200 dual school desks", "Supply of 150 semi-fowler hospital beds",
        "Supply and installation of 40 office workstations"}
    assert all(Path(db.get_tender(conn, t)["pdf_path"]).parent == tmp_path / "tenders" for t in tender_ids)

    again_company, again_tenders = demo.load_demo(conn, tmp_path, DATA)
    assert (again_company, sorted(again_tenders)) == (company_id, sorted(tender_ids))
    assert len(db.list_tenders(conn)) == 3
    assert conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 1
