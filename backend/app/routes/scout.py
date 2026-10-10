"""The Scout: sweep the tender portals now, and the history of sweeps."""
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app import config, db, graph
from app.agents import scout as scout_agent
from app.routes.deps import get_conn, get_mem, get_storage

router = APIRouter(prefix="/scout", tags=["scout"])


def waiting(conn, exclude: list[int]) -> list[int]:
    """Portal tenders and private requests already in the inbox that no agent has run on yet."""
    return [t["id"] for t in db.list_tenders(conn, kinds=("portal", "private"))
            if t["status"] == "new" and t["id"] not in exclude]


def _where(tender: dict, new: bool) -> str:
    if tender["kind"] == "private":
        return f"private request from {tender['buyer']}"
    seen = "found" if new else "waiting in the inbox, found earlier"
    return f"{seen} on {tender['portal']} ({tender['source_id']})"


def sweep(conn, storage, feed, company_id, start_run) -> dict:
    """Bring in new portal tenders, then start the agents (start_run(tender_id, run_id)) on every tender
    that fits the business and has not been run yet - new ones and ones already waiting in the inbox."""
    found, added = scout_agent.ingest(conn, storage, feed)
    company = db.get_company(conn, company_id) if company_id is not None else None
    candidates = added + waiting(conn, added) if company else []
    queued = []
    for tid in scout_agent.worth_running(conn, company, candidates) if company else []:
        tender = db.get_tender(conn, tid)
        run_id = uuid4().hex
        if not db.claim_run(conn, tid, run_id):
            continue
        db.add_log(conn, tid, run_id, "scout", f"{_where(tender, tid in added)}; it fits your business, starting the agents")
        start_run(tid, run_id)
        queued.append(tid)
    picked_up = len(candidates) - len(added)
    message = f"{len(added)} new tender(s)"
    if picked_up:
        message += f", {picked_up} waiting in the inbox"
    message += f"; {len(queued)} fit the business and went to the agents"
    if company and len(candidates) > len(queued):
        message += f"; {len(candidates) - len(queued)} did not fit"
    if company is None:
        message += " (no business chosen, so none were checked for fit)"
    db.add_scout_run(conn, found, len(added), len(queued), message)
    return {"found": found, "added": added, "queued": queued, "message": message}


class SweepIn(BaseModel):
    company_id: int | None = None


@router.post("/run")
def run_scout(request: Request, background: BackgroundTasks, body: SweepIn | None = None,
              conn=Depends(get_conn), mem=Depends(get_mem), storage=Depends(get_storage)):
    company_id = body.company_id if body else None
    if company_id is not None and db.get_company(conn, company_id) is None:
        raise HTTPException(404, "Company not found")
    feed = getattr(request.app.state, "feed_path", None) or config.feed_path()
    if not feed.exists():
        raise HTTPException(500, f"Portal feed not found: {feed}")

    def start_run(tid, run_id):
        background.add_task(graph.run_pipeline, conn, mem, tid, company_id, run_id=run_id)

    return sweep(conn, storage, feed, company_id, start_run)


@router.get("/runs")
def scout_runs(conn=Depends(get_conn)):
    return db.list_scout_runs(conn)
