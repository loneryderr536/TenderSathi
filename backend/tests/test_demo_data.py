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
    "classroom_furniture.pdf": ["4.1", "4.2", "4.3"],
    "steel_almirahs.pdf": ["4.1", "4.2", "4.3"],
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


def test_load_demo_is_idempotent():
    conn = db.connect(":memory:")
    company_id, others = demo.load_demo(conn, DATA)
    assert db.get_company(conn, company_id)["name"] == "Ernakulam Woodworks"
    assert len(others) == 6 and company_id not in others
    assert db.list_tenders(conn) == []   # tenders come from the Scout, not the loader

    assert demo.load_demo(conn, DATA) == (company_id, others)
    assert conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 7


def test_portal_feed_lists_every_demo_tender_once():
    from app.agents.scout import read_feed
    items = read_feed(DATA / "feed" / "portal_feed.json")
    assert len({i["source_id"] for i in items}) == len(items) == 5
    assert all(i["pdf"].exists() and i["portal"] and i["buyer"] for i in items)
    assert not any("corrigend" in str(i["pdf"]) for i in items)


def test_demo_corrigendum_parses():
    pages = pdf_to_pages(str(DATA / "tenders" / "corrigenda" / "school_desks_corrigendum.pdf"))
    text = "\n".join(pages)
    assert "6 November 2026" in text and "Rs. 75,000" in text and "4.5" in text
