"""Platform dashboard: what the agents are doing, how fast, how often they fail, and how often owners agree."""
from collections import Counter, defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends

from app import auth, config, db
from app.routes.deps import get_conn

router = APIRouter(prefix="/admin", tags=["platform"], dependencies=[Depends(auth.platform_user)])


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def agent_metrics(log: list[dict]) -> list[dict]:
    """Per agent: runs, average seconds from start to finish, retries and failures."""
    starts, stats = {}, defaultdict(lambda: {"runs": 0, "seconds": [], "retries": 0, "failures": 0})
    for line in log:
        key, agent, message = (line["run_id"], line["agent"]), line["agent"], line["message"]
        if message == "started":
            starts[key] = _time(line["created_at"])
            stats[agent]["runs"] += 1
        elif message == "finished" and key in starts:
            stats[agent]["seconds"].append((_time(line["created_at"]) - starts[key]).total_seconds())
        elif message.startswith("error"):
            stats[agent]["retries"] += 1
        elif message.startswith("failed"):
            stats[agent]["failures"] += 1
        elif agent == "scout":   # the Scout writes one line per tender it hands to the agents
            stats[agent]["runs"] += 1
    order = ["scout", "reader", "tracker", "eligibility", "checklist", "drafter", "reviewer", "stop", "await_approval"]
    return [{"agent": a, "model": config.model_for(a) if a in config.AGENT_MODELS else "none (rules)", "runs": s["runs"],
             "avg_seconds": round(sum(s["seconds"]) / len(s["seconds"]), 1) if s["seconds"] else None,
             "retries": s["retries"], "failures": s["failures"]}
            for a, s in sorted(stats.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)]


def recent_runs(conn, log: list[dict], limit=8) -> list[dict]:
    runs = {}
    for line in log:
        if not line["run_id"]:
            continue
        run = runs.setdefault(line["run_id"], {"run_id": line["run_id"], "tender_id": line["tender_id"],
                                               "started": line["created_at"], "ended": line["created_at"],
                                               "last": "", "failed": False})
        run["ended"], run["last"] = line["created_at"], f"{line['agent']} {line['message']}"
        run["failed"] = run["failed"] or line["message"].startswith("failed")
    out = []
    for run in sorted(runs.values(), key=lambda r: r["started"], reverse=True)[:limit]:
        tender = db.get_tender(conn, run["tender_id"]) or {}
        out.append({**run, "title": tender.get("title"),
                    "seconds": (_time(run["ended"]) - _time(run["started"])).total_seconds()})
    return out


def accuracy(feedback: list[dict]) -> list[dict]:
    by_agent = defaultdict(list)
    for f in feedback:
        by_agent[f["agent"]].append(bool(f["correct"]))
    return [{"agent": a, "judged": len(v), "correct": sum(v), "accuracy": round(100 * sum(v) / len(v))}
            for a, v in by_agent.items()]


@router.get("/stats")
def stats(conn=Depends(get_conn)):
    tenders = db.list_tenders(conn, kinds=("upload", "portal", "draft", "private"))
    companies = db.list_companies(conn)
    log = db.all_log(conn)
    return {
        "tenders": len(tenders),
        "by_status": Counter(t["status"] for t in tenders),
        "by_source": Counter(t["portal"] or ("Government draft" if t["kind"] == "draft" else "Uploaded")
                             for t in tenders),
        "businesses": len(companies),
        "msme_businesses": sum(bool(c["udyam"]) for c in companies),
        "agents": agent_metrics(log),
        "runs": recent_runs(conn, log),
        "accuracy": accuracy(db.get_feedback(conn)),
        "scout_runs": db.list_scout_runs(conn),
        "scout_interval_seconds": config.scout_interval(),
    }
