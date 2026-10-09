"""Endpoints to upload tenders, start a run, poll the agent log, approve and export."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app import db, graph, pdf_reader
from app.agents import reader as reader_agent
from app.agents import tracker as tracker_agent
from app.routes.deps import get_conn, get_mem, get_storage
from app.schemas import Section

router = APIRouter(prefix="/tenders", tags=["tenders"])


def _save_pdf(file: UploadFile, storage) -> Path:
    """Save an uploaded PDF under storage/tenders; scanned or non-PDF files are rejected with a 400."""
    folder = Path(storage) / "tenders"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid4().hex}.pdf"
    path.write_bytes(file.file.read())
    try:
        pdf_reader.pdf_to_pages(str(path))
    except pdf_reader.ScannedPDFError as e:
        path.unlink()
        raise HTTPException(400, str(e))
    except Exception:
        path.unlink()
        raise HTTPException(400, "Please upload a PDF file")
    return path


@router.post("")
def upload_tender(file: UploadFile = File(...), title: str | None = Form(None),
                  conn=Depends(get_conn), storage=Depends(get_storage)):
    """Save the PDF and add it to the inbox; scanned or non-PDF files are rejected here."""
    path = _save_pdf(file, storage)
    title = title or Path(file.filename or "tender.pdf").stem
    tender_id = db.create_tender(conn, str(path), title)
    return {"id": tender_id, "title": title, "status": "new"}


@router.get("")
def inbox(conn=Depends(get_conn)):
    return db.list_tenders(conn)


class RunIn(BaseModel):
    company_id: int


def _tender_or_404(conn, tender_id: int) -> dict:
    tender = db.get_tender(conn, tender_id)
    if tender is None:
        raise HTTPException(404, "Tender not found")
    return tender


@router.post("/{tender_id}/run")
def start_run(tender_id: int, body: RunIn, background: BackgroundTasks,
              conn=Depends(get_conn), mem=Depends(get_mem)):
    """Start the agents in the background; the page then polls /log with the returned run_id."""
    _tender_or_404(conn, tender_id)
    if db.get_company(conn, body.company_id) is None:
        raise HTTPException(404, "Company not found")
    run_id = uuid4().hex
    if not db.claim_run(conn, tender_id, run_id):   # atomic, so a double click can't start two runs
        raise HTTPException(409, "A run is already in progress")
    background.add_task(graph.run_pipeline, conn, mem, tender_id, body.company_id, run_id=run_id)
    return {"run_id": run_id}


@router.get("/{tender_id}/log")
def read_log(tender_id: int, run_id: str | None = None, conn=Depends(get_conn)):
    tender = _tender_or_404(conn, tender_id)
    run_id = run_id or tender["current_run_id"]
    return db.get_log(conn, tender_id, run_id) if run_id else []


@router.get("/{tender_id}/result")
def read_result(tender_id: int, conn=Depends(get_conn)):
    tender = _tender_or_404(conn, tender_id)
    output = db.get_run_output(conn, tender_id)
    summary = {k: tender[k] for k in ("id", "title", "status", "reason", "deadline", "deadline_at", "emd",
                                      "payment_terms")}
    changes = db.get_changes(conn, tender_id)
    return {"tender": summary, **{k: v.model_dump() if v else None for k, v in output.items()},
            "changes": changes.model_dump() if changes else None}


@router.post("/{tender_id}/corrigendum")
def upload_corrigendum(tender_id: int, file: UploadFile = File(...), conn=Depends(get_conn),
                       storage=Depends(get_storage)):
    """A changed version of the tender: the Reader reads it, the Tracker lists what changed."""
    tender = _tender_or_404(conn, tender_id)
    if tender["status"] == "running":
        raise HTTPException(409, "A run is already in progress")
    old = db.get_run_output(conn, tender_id)["facts"]
    if old is None:
        raise HTTPException(409, "Run the agents on this tender first, so there is something to compare")
    path = _save_pdf(file, storage)
    try:
        clauses = pdf_reader.pages_to_clauses(pdf_reader.pdf_to_pages(str(path)))
        new = reader_agent.extract_facts(reader_agent.reader_input(reader_agent.select_key_clauses(clauses)))
        changes = tracker_agent.compare_tenders(old, new)
    except Exception as e:
        path.unlink()
        raise HTTPException(502, f"Could not compare the two versions: {e}")
    db.record_tender_change(conn, tender_id, str(path), changes)
    return changes.model_dump()


class ApproveIn(BaseModel):
    cover_letter: str | None = None
    sections: list[Section] | None = None


@router.post("/{tender_id}/approve")
def approve(tender_id: int, body: ApproveIn | None = None, conn=Depends(get_conn)):
    """The owner approves the bid, with any edits; nothing is ever submitted for them."""
    tender = _tender_or_404(conn, tender_id)
    if tender["status"] != "awaiting_approval":
        raise HTTPException(409, "Bid is not ready for approval")
    body = body or ApproveIn()
    if body.cover_letter is not None and not body.cover_letter.strip():
        raise HTTPException(400, "Cover letter cannot be empty")
    if body.cover_letter is not None or body.sections is not None:
        draft = db.get_run_output(conn, tender_id)["draft"]
        db.update_draft(conn, tender_id, draft.model_copy(update={
            "cover_letter": body.cover_letter if body.cover_letter is not None else draft.cover_letter,
            "sections": body.sections if body.sections is not None else draft.sections,
        }))
    db.set_tender_status(conn, tender_id, "approved")
    return {"status": "approved"}


@router.get("/{tender_id}/export")
def export(tender_id: int, conn=Depends(get_conn)):
    tender = _tender_or_404(conn, tender_id)
    if tender["status"] != "approved":
        raise HTTPException(409, "Approve the bid before exporting")
    return Response(
        bid_pack_markdown(tender, db.get_run_output(conn, tender_id)), media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="bid-pack-{tender_id}.md"'})


def bid_pack_markdown(tender: dict, output: dict) -> str:
    draft, review, checklist = output["draft"], output["review"], output["checklist"]
    lines = [f"# {tender['title']}", "",
             f"- **Deadline:** {tender['deadline']}",
             f"- **EMD:** {tender['emd']}",
             f"- **Payment terms:** {tender['payment_terms']}", "",
             "## Cover letter", "", draft.cover_letter, ""]
    for section in draft.sections:
        lines += [f"## {section.title}", "", section.body, ""]
    if review:
        lines += ["## Compliance matrix", "", "| Rule | Mandatory | Covered | Where |", "|---|---|---|---|"]
        lines += [f"| {r.rule_text} | {'Yes' if r.must_have else 'No'} | {'Yes' if r.covered else 'No'} | {r.where} |"
                  for r in review.matrix]
        lines.append("")
    if checklist:
        lines += ["## Document checklist", ""]
        lines += [f"- [x] {i.document} ({i.matched_file})" if i.status == "have" else f"- [ ] {i.document}"
                  for i in checklist.items]
        lines.append("")
    return "\n".join(lines)
