"""Loads a sample business profile and demo tender PDFs into storage.

Run from the project folder:  backend/.venv/bin/python scripts/load_demo_data.py
Any PDF you put in data/tenders/ is loaded too (titled from data/tenders/titles.json, or its file name).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config, db  # noqa: E402
from app.demo import load_demo  # noqa: E402


def main():
    storage = config.storage_dir()
    conn = db.connect(str(storage / "tendersathi.db"))
    company_id, tender_ids = load_demo(conn, storage, ROOT / "data")
    print(f"Business profile loaded (id {company_id}); {len(tender_ids)} tenders in the inbox.")
    print(f"Open http://localhost:5173/?company={company_id} once so the website uses this profile.")


if __name__ == "__main__":
    main()
