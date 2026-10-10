"""The Scout: sweep the tender portals now, and the history of sweeps."""
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app import config, db, graph
from app.agents import scout as scout_agent
from app.routes.deps import get_conn, get_mem, get_storage

router = APIRouter(prefix="/scout", tags=["scout"])


def sweep(conn, storage, feed, company_id, start_run) -> dict:
    """Bring in new portal tenders; start the agents (start_run(tender_id, run_id)) on those that fit."""
    found, added = scout_agent.ingest(conn, storage, feed)
    company = db.get_company(conn, company_id) if company_id is not None else None
    queued = []
    for tid in scout_agent.worth_running(conn, company, added) if company else []:
        tender = db.get_tender(conn, tid)
        run_id = uuid4().hex
        if not db.claim_run(conn, tid, run_id):
            continue
        db.add_log(conn, tid, run_id, "scout", f"found on {tender['portal']} ({tender['source_id']}); "
                                               "it fits your business, starting the agents")
        start_run(tid, run_id)
        queued.append(tid)
    skipped = len(added) - len(queued)
    message = f"{len(added)} new tender(s); {len(queued)} fit the business and went to the agents"
    if company and skipped:
        message += f"; {skipped} did not fit and were only added to the inbox"
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
