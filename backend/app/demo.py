"""Loads the sample business profiles into storage. Safe to run twice.

Tenders are not loaded here: the Scout agent brings them in from the portal feed (data/feed/portal_feed.json).
"""
import json
from pathlib import Path

from app import auth, db


def _company_id(conn, company: dict) -> int:
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (company["name"],)).fetchone()
    return row["id"] if row else db.create_company(conn, **company)


def load_demo(conn, data_dir: Path, storage_dir: Path | None = None) -> tuple[int, list[int]]:
    """Returns (the demo business's id, the other sample businesses' ids). Existing names are reused.

    With storage_dir, the sample requests for quotation from private owners are posted too."""
    company_id = _company_id(conn, json.loads((data_dir / "company" / "demo_company.json").read_text()))
    more_file = data_dir / "company" / "more_companies.json"
    others = [_company_id(conn, c) for c in json.loads(more_file.read_text())] if more_file.exists() else []
    load_accounts(conn, data_dir)
    if storage_dir is not None:
        load_rfqs(conn, data_dir, Path(storage_dir))
    return company_id, others


def load_rfqs(conn, data_dir: Path, storage_dir: Path) -> list[int]:
    """The sample requests in data/demo_rfqs.json; a title already posted is left as it is."""
    from app.routes.rfq import RfqIn, post_rfq

    file = data_dir / "demo_rfqs.json"
    if not file.exists():
        return []
    ids = []
    for item in json.loads(file.read_text())["rfqs"]:
        row = conn.execute("SELECT id FROM tenders WHERE title = ? AND kind = 'private'", (item["title"],)).fetchone()
        owner = db.user_by_email(conn, item["owner"])
        if row:
            ids.append(row["id"])
        elif owner:
            fields = {k: v for k, v in item.items() if k != "owner"}
            ids.append(post_rfq(conn, storage_dir, owner, RfqIn(**fields)))
    return ids


def load_accounts(conn, data_dir: Path) -> list[str]:
    """The demo logins in data/demo_accounts.json; existing emails are left as they are."""
    file = data_dir / "demo_accounts.json"
    if not file.exists():
        return []
    emails = []
    for a in json.loads(file.read_text())["accounts"]:
        emails.append(a["email"])
        if db.user_by_email(conn, a["email"]):
            continue
        company = conn.execute("SELECT id FROM companies WHERE name = ?", (a["company"],)).fetchone() \
            if a.get("company") else None
        db.create_user(conn, a["email"], a["name"], a["role"], auth.hash_password(a["password"]),
                       company_id=company["id"] if company else None, department=a.get("department"))
    return emails
