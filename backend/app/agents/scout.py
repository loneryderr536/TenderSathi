"""Scout agent: watches the tender portals and brings every newly published tender into TenderSathi.

The portals are read through a feed (data/feed/portal_feed.json stands in for GeM, CPPP and Kerala e-tender
listing pages). New tenders are added to the inbox; the ones that fit the business are queued for the full
agent pipeline without anyone pressing a button.
"""
import json
import shutil
from pathlib import Path

from app import db, pdf_reader, relevance


def read_feed(feed_path: Path) -> list[dict]:
    """The published tenders listed in the feed, each with an absolute PDF path."""
    feed = json.loads(Path(feed_path).read_text())
    folder = Path(feed_path).parent
    tenders_dir = folder.parent / "tenders"
    titles_file = tenders_dir / "titles.json"
    titles = json.loads(titles_file.read_text()) if titles_file.exists() else {}
    items = []
    for item in feed["tenders"]:
        pdf = Path(item["pdf"])
        pdf = pdf if pdf.is_absolute() else (folder / pdf if (folder / pdf).exists() else tenders_dir / pdf)
        items.append({**item, "pdf": pdf, "title": item.get("title") or titles.get(pdf.name, pdf.stem.replace("_", " "))})
    return items


def ingest(conn, storage_dir: Path, feed_path: Path) -> tuple[int, list[int]]:
    """Add the feed's new tenders (by portal reference) to the inbox. Returns (found, new tender ids)."""
    items = read_feed(feed_path)
    target = Path(storage_dir) / "tenders"
    target.mkdir(parents=True, exist_ok=True)
    added = []
    for item in items:
        if db.tender_by_source(conn, item["source_id"]):
            continue
        try:
            pdf_reader.pdf_to_pages(str(item["pdf"]))   # skip broken or scanned PDFs instead of failing the sweep
        except Exception:
            continue
        copy = target / f"portal-{item['pdf'].name}"
        shutil.copyfile(item["pdf"], copy)
        added.append(db.create_tender(conn, str(copy), item["title"], kind="portal", source_id=item["source_id"],
                                      portal=item["portal"], buyer=item["buyer"], published=item.get("published")))
    return len(items), added


def worth_running(conn, company: dict, tender_ids: list[int]) -> list[int]:
    """The new tenders that fit what the business makes: only these get the full (token-costly) pipeline."""
    out = []
    for tid in tender_ids:
        tender = db.get_tender(conn, tid)
        if relevance.match_tender(company, tender["pdf_path"], tender["title"])["fits"]:
            out.append(tid)
    return out
