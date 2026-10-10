"""Loads the sample business profiles into storage. Safe to run twice.

Tenders are not loaded here: the Scout agent brings them in from the portal feed (data/feed/portal_feed.json).
"""
import json
from pathlib import Path

from app import db


def _company_id(conn, company: dict) -> int:
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (company["name"],)).fetchone()
    return row["id"] if row else db.create_company(conn, **company)


def load_demo(conn, data_dir: Path) -> tuple[int, list[int]]:
    """Returns (the demo business's id, the other sample businesses' ids). Existing names are reused."""
    company_id = _company_id(conn, json.loads((data_dir / "company" / "demo_company.json").read_text()))
    more_file = data_dir / "company" / "more_companies.json"
    others = [_company_id(conn, c) for c in json.loads(more_file.read_text())] if more_file.exists() else []
    return company_id, others
