"""Government dashboard: fairness check before publishing, and who a published tender shuts out."""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app import auth, db, participation, pdf_reader
from app.agents import fairness as fairness_agent
from app.routes.deps import get_conn, get_mem, get_storage
from app.routes.tenders import _save_pdf, _tender_or_404

router = APIRouter(prefix="/gov", tags=["government"], dependencies=[Depends(auth.government_user)])


@router.get("/tenders")
def gov_tenders(conn=Depends(get_conn)):
    """Published portal tenders and the officer's drafts, with their fairness score and screening totals."""
    out = []
    for t in db.list_tenders(conn, kinds=("portal", "draft")):
        report = db.get_report(conn, t["id"], "fairness")
        screening = participation.insights(conn, t["id"]) if db.get_screenings(conn, t["id"]) else None
        out.append({**t, "fairness_score": report["score"] if report else None,
                    "concerns": report["concerns"] if report else None,
                    "screened": screening["screened"] if screening else None,
                    "qualified": screening["qualified"] if screening else None})
    return out


@router.post("/drafts")
def upload_draft(file: UploadFile = File(...), title: str | None = Form(None),
                 conn=Depends(get_conn), storage=Depends(get_storage)):
    """A tender the officer has not published yet: checked here, never shown to businesses."""
    path = _save_pdf(file, storage)
    title = title or Path(file.filename or "draft.pdf").stem
    return {"id": db.create_tender(conn, str(path), title, kind="draft"), "title": title}


@router.post("/tenders/{tender_id}/fairness")
def run_fairness(tender_id: int, conn=Depends(get_conn), mem=Depends(get_mem)):
    tender = _tender_or_404(conn, tender_id)
    clauses = pdf_reader.pages_to_clauses(pdf_reader.pdf_to_pages(tender["pdf_path"]))
    mem.add_clauses(tender_id, clauses)
    try:
        report = fairness_agent.check_fairness(lambda query: mem.search_clauses(tender_id, query, k=3))
    except Exception as e:
        raise HTTPException(502, f"The fairness check could not finish: {e}")
    db.save_report(conn, tender_id, "fairness", report)
    return report


@router.get("/tenders/{tender_id}")
def gov_tender(tender_id: int, conn=Depends(get_conn)):
    tender = _tender_or_404(conn, tender_id)
    keys = ("id", "title", "status", "kind", "portal", "buyer", "published", "deadline", "emd", "source_id")
    return {"tender": {k: tender.get(k) for k in keys},
            "fairness": db.get_report(conn, tender_id, "fairness"),
            "insights": participation.insights(conn, tender_id)}


@router.post("/tenders/{tender_id}/screen")
def screen(tender_id: int, background: BackgroundTasks, conn=Depends(get_conn), mem=Depends(get_mem)):
    """Screen every registered business against this tender, in the background."""
    _tender_or_404(conn, tender_id)
    if not participation.claim(tender_id):
        raise HTTPException(409, "Screening is already running")
    background.add_task(participation.screen, conn, mem, tender_id)
    return {"running": True}
