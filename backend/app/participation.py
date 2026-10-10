"""Participation insights (government side): which rules of a tender shut out the registered businesses.

Every registered business is screened against the tender's rules by the Eligibility agent; the dashboard
shows only totals and anonymous labels, never a business's name or profile.
"""
import threading

from app import db, pdf_reader
from app.agents import eligibility as eligibility_agent
from app.agents import reader as reader_agent
from app.graph import business_lines

_running: set[int] = set()
_guard = threading.Lock()


def is_running(tender_id: int) -> bool:
    return tender_id in _running


def claim(tender_id: int) -> bool:
    with _guard:
        if tender_id in _running:
            return False
        _running.add(tender_id)
        return True


def ensure_facts(conn, mem, tender_id: int):
    """The Reader's facts for the tender, reading it first if no run has yet."""
    facts = db.get_run_output(conn, tender_id)["facts"]
    if facts is None:
        tender = db.get_tender(conn, tender_id)
        clauses = pdf_reader.pages_to_clauses(pdf_reader.pdf_to_pages(tender["pdf_path"]))
        mem.add_clauses(tender_id, clauses)
        facts = reader_agent.extract_facts(reader_agent.reader_input(reader_agent.select_key_clauses(clauses)))
        db.save_run_output(conn, tender_id, {"facts": facts})
    return facts


def screen(conn, mem, tender_id: int) -> None:
    """Screen every registered business (call claim() first). Errors leave the previous screening in place."""
    try:
        facts = ensure_facts(conn, mem, tender_id)
        results = {c["id"]: eligibility_agent.judge_eligibility(facts.rules, business_lines(c))
                   for c in db.list_companies(conn)}
        db.save_screenings(conn, tender_id, results)
    finally:
        _running.discard(tender_id)


def _label(i: int, company: dict) -> str:
    place = company["location"].split(",")[0].strip()
    return f"Business {chr(65 + i)} · {'Udyam MSE' if company['udyam'] else 'not MSE-registered'} · {place}"


def insights(conn, tender_id: int) -> dict:
    screenings = db.get_screenings(conn, tender_id)
    companies = {c["id"]: c for c in db.list_companies(conn)}
    facts = db.get_run_output(conn, tender_id)["facts"]
    by_rule = []
    for rule in (facts.rules if facts else []):
        counts = {"pass": 0, "fail": 0, "missing": 0}
        for result in screenings.values():
            v = next((v for v in result.verdicts if v.rule_text == rule.text), None)
            counts[v.verdict if v else "missing"] += 1
        by_rule.append({"rule_text": rule.text, "clause": rule.clause, "page": rule.page,
                        "must_have": rule.must_have, **counts})
    businesses = []
    for i, (cid, result) in enumerate(screenings.items()):
        company = companies.get(cid)
        if company is None:
            continue
        blocking = [f"clause {v.clause}" for v in result.verdicts if v.must_have and v.verdict == "fail"]
        businesses.append({"label": _label(i, company), "msme": bool(company["udyam"]),
                           "outcome": "excluded" if blocking else "qualifies", "blocked_by": blocking})
    qualified = sum(b["outcome"] == "qualifies" for b in businesses)
    msme = [b for b in businesses if b["msme"]]
    return {"running": is_running(tender_id), "screened": len(businesses), "qualified": qualified,
            "msme_screened": len(msme), "msme_qualified": sum(b["outcome"] == "qualifies" for b in msme),
            "by_rule": by_rule, "businesses": businesses}
