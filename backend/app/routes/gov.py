"""Buyer dashboards (government and private owners): fairness check, and who a tender shuts out.

A private owner sees only their own requests and drafts; government sees portal tenders and government drafts.
"""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app import auth, db, participation, pdf_reader
from app.agents import fairness as fairness_agent
from app.routes.deps import get_conn, get_mem, get_storage
from app.routes.tenders import _save_pdf, _tender_or_404

router = APIRouter(prefix="/gov", tags=["government"])


def _owned_by_private(conn, tender: dict) -> bool:
    owner = db.get_user(conn, tender["owner_user_id"]) if tender.get("owner_user_id") else None
    return bool(owner and owner["role"] == "private")


def _visible(conn, user: dict, tender: dict) -> bool:
    if user["role"] == "private":
        return tender.get("owner_user_id") == user["id"]
    if user["role"] == "government":
        return tender.get("kind") in ("portal", "draft") and not _owned_by_private(conn, tender)
    return True   # platform


def _tender_for(conn, tender_id: int, user: dict) -> dict:
    tender = _tender_or_404(conn, tender_id)
    if not _visible(conn, user, tender):
        raise HTTPException(404, "Tender not found")
    return tender


@router.get("/tenders")
def gov_tenders(conn=Depends(get_conn), user=Depends(auth.buyer_user)):
    """The buyer's tenders, with their fairness score and screening totals."""
    out = []
    for t in db.list_tenders(conn, kinds=("portal", "draft", "private")):
        if not _visible(conn, user, t):
            continue
        report = db.get_report(conn, t["id"], "fairness")
        screening = participation.insights(conn, t["id"]) if db.get_screenings(conn, t["id"]) else None
        out.append({**t, "fairness_score": report["score"] if report else None,
                    "concerns": report["concerns"] if report else None,
                    "screened": screening["screened"] if screening else None,
                    "qualified": screening["qualified"] if screening else None})
    return out


@router.post("/drafts")
def upload_draft(file: UploadFile = File(...), title: str | None = Form(None),
                 conn=Depends(get_conn), storage=Depends(get_storage), user=Depends(auth.buyer_user)):
    """A tender the buyer has not published yet: checked here, never shown to businesses."""
    path = _save_pdf(file, storage)
    title = title or Path(file.filename or "draft.pdf").stem
    return {"id": db.create_tender(conn, str(path), title, kind="draft", owner_user_id=user["id"]), "title": title}


@router.post("/tenders/{tender_id}/fairness")
def run_fairness(tender_id: int, conn=Depends(get_conn), mem=Depends(get_mem), user=Depends(auth.buyer_user)):
    tender = _tender_for(conn, tender_id, user)
    clauses = pdf_reader.pages_to_clauses(pdf_reader.pdf_to_pages(tender["pdf_path"]))
    mem.add_clauses(tender_id, clauses)
    try:
        report = fairness_agent.check_fairness(lambda query: mem.search_clauses(tender_id, query, k=3))
    except Exception as e:
        raise HTTPException(502, f"The fairness check could not finish: {e}")
    db.save_report(conn, tender_id, "fairness", report)
    return report


@router.get("/tenders/{tender_id}")
def gov_tender(tender_id: int, conn=Depends(get_conn), user=Depends(auth.buyer_user)):
    tender = _tender_for(conn, tender_id, user)
    keys = ("id", "title", "status", "kind", "portal", "buyer", "published", "deadline", "emd", "source_id",
            "advance_percent")
    return {"tender": {k: tender.get(k) for k in keys},
            "fairness": db.get_report(conn, tender_id, "fairness"),
            "insights": participation.insights(conn, tender_id)}


@router.post("/tenders/{tender_id}/screen")
def screen(tender_id: int, background: BackgroundTasks, conn=Depends(get_conn), mem=Depends(get_mem),
           user=Depends(auth.buyer_user)):
    """Screen every registered business against this tender, in the background."""
    _tender_for(conn, tender_id, user)
    if not participation.claim(tender_id):
        raise HTTPException(409, "Screening is already running")
    background.add_task(participation.screen, conn, mem, tender_id)
    return {"running": True}
