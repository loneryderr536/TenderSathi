"""Loads the sample business profiles into storage.

Run from the project folder:  backend/.venv/bin/python scripts/load_demo_data.py
Tenders are brought in by the Scout agent from the portal feed (data/feed/portal_feed.json):
press "Find new tenders" in the website, or set SCOUT_INTERVAL_SECONDS in .env.
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
    company_id, others = load_demo(conn, ROOT / "data")
    print(f"Business profile loaded (id {company_id}), plus {len(others)} other sample businesses.")
    print(f"Open http://localhost:5173/?company={company_id} once so the website uses this profile.")


if __name__ == "__main__":
    main()
