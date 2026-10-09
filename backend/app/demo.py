"""Loads the demo business profile and the tender PDFs in data/ into storage. Safe to run twice."""
import json
import shutil
from pathlib import Path

from app import db


def load_demo(conn, storage_dir: Path, data_dir: Path) -> tuple[int, list[int]]:
    """Returns (company_id, tender_ids). Existing rows with the same name/title are reused."""
    company = json.loads((data_dir / "company" / "demo_company.json").read_text())
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (company["name"],)).fetchone()
    company_id = row["id"] if row else db.create_company(conn, **company)

    tenders_dir = data_dir / "tenders"
    titles_file = tenders_dir / "titles.json"
    titles = json.loads(titles_file.read_text()) if titles_file.exists() else {}
    target = Path(storage_dir) / "tenders"
    target.mkdir(parents=True, exist_ok=True)

    tender_ids = []
    for pdf in sorted(tenders_dir.glob("*.pdf")):
        title = titles.get(pdf.name, pdf.stem.replace("_", " "))
        row = conn.execute("SELECT id FROM tenders WHERE title = ?", (title,)).fetchone()
        if row:
            tender_ids.append(row["id"])
            continue
        copy = target / f"demo-{pdf.name}"
        shutil.copyfile(pdf, copy)
        tender_ids.append(db.create_tender(conn, str(copy), title))
    return company_id, tender_ids
