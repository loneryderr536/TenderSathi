"""SQLite setup: companies, tenders, runs, agent log, checklist items."""
import functools
import json
import sqlite3
import threading

from app.schemas import (BidDraft, Checklist, ChecklistItem, EligibilityResult, ReviewResult, Rule,
                         RuleVerdict, Section, TenderFacts)

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY, name TEXT, products TEXT, location TEXT, turnover TEXT, udyam INTEGER);
CREATE TABLE IF NOT EXISTS company_documents (
    id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
CREATE TABLE IF NOT EXISTS past_orders (
    id INTEGER PRIMARY KEY, company_id INTEGER, buyer TEXT, item TEXT, value TEXT, year INTEGER);
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY, pdf_path TEXT, title TEXT, deadline TEXT, emd TEXT, payment_terms TEXT,
    required_documents_json TEXT, status TEXT, reason TEXT, current_run_id TEXT);
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY, tender_id INTEGER, text TEXT, clause TEXT, page INTEGER, must_have INTEGER);
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY, tender_id INTEGER, rule_text TEXT, verdict TEXT, reason TEXT,
    clause TEXT, page INTEGER, must_have INTEGER);
CREATE TABLE IF NOT EXISTS checklist_items (
    id INTEGER PRIMARY KEY, tender_id INTEGER, document TEXT, status TEXT, matched_file TEXT);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY, tender_id INTEGER, round INTEGER, cover_letter TEXT, sections_json TEXT,
    review_json TEXT);
CREATE TABLE IF NOT EXISTS agent_log (
    id INTEGER PRIMARY KEY, tender_id INTEGER, run_id TEXT, agent TEXT, message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

OUTPUT_TABLES = ("rules", "verdicts", "checklist_items", "drafts")

# One connection is shared by request handlers and background runs, so every helper
# takes this lock: no interleaved transactions, no "recursive use of cursors".
_lock = threading.RLock()


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return wrapper


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@_locked
def create_company(conn, name, products, location, turnover, udyam: bool,
                   documents: list[str], past_orders: list[dict]) -> int:
    cur = conn.execute(
        "INSERT INTO companies (name, products, location, turnover, udyam) VALUES (?, ?, ?, ?, ?)",
        (name, products, location, turnover, int(udyam)))
    company_id = cur.lastrowid
    conn.executemany("INSERT INTO company_documents (company_id, name) VALUES (?, ?)",
                     [(company_id, d) for d in documents])
    conn.executemany("INSERT INTO past_orders (company_id, buyer, item, value, year) VALUES (?, ?, ?, ?, ?)",
                     [(company_id, o["buyer"], o["item"], o["value"], o["year"]) for o in past_orders])
    conn.commit()
    return company_id


@_locked
def get_company(conn, company_id) -> dict | None:
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    if row is None:
        return None
    company = dict(row)
    company["documents"] = [r["name"] for r in conn.execute(
        "SELECT name FROM company_documents WHERE company_id = ? ORDER BY id", (company_id,))]
    company["past_orders"] = [dict(r) for r in conn.execute(
        "SELECT buyer, item, value, year FROM past_orders WHERE company_id = ? ORDER BY id", (company_id,))]
    return company


@_locked
def create_tender(conn, pdf_path, title) -> int:
    cur = conn.execute("INSERT INTO tenders (pdf_path, title, status) VALUES (?, ?, 'new')", (pdf_path, title))
    conn.commit()
    return cur.lastrowid


@_locked
def get_tender(conn, tender_id) -> dict | None:
    row = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()
    return dict(row) if row else None


@_locked
def set_tender_status(conn, tender_id, status, reason=None):
    """reason: why a run stopped or failed; None clears it."""
    conn.execute("UPDATE tenders SET status = ?, reason = ? WHERE id = ?", (status, reason, tender_id))
    conn.commit()


@_locked
def set_current_run(conn, tender_id, run_id):
    conn.execute("UPDATE tenders SET current_run_id = ? WHERE id = ?", (run_id, tender_id))
    conn.commit()


@_locked
def add_log(conn, tender_id, run_id, agent, message):
    conn.execute("INSERT INTO agent_log (tender_id, run_id, agent, message) VALUES (?, ?, ?, ?)",
                 (tender_id, run_id, agent, message))
    conn.commit()


@_locked
def get_log(conn, tender_id, run_id=None) -> list[dict]:
    sql, args = "SELECT agent, message, created_at FROM agent_log WHERE tender_id = ?", [tender_id]
    if run_id is not None:
        sql, args = sql + " AND run_id = ?", args + [run_id]
    return [dict(r) for r in conn.execute(sql + " ORDER BY id", args)]


@_locked
def save_run_output(conn, tender_id, state: dict):
    """Replace this tender's stored output with whatever parts the run produced."""
    with conn:  # all or nothing: a failure part-way rolls back the deletes too
        for table in OUTPUT_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE tender_id = ?", (tender_id,))
        conn.execute("UPDATE tenders SET required_documents_json = NULL WHERE id = ?", (tender_id,))

        if facts := state.get("facts"):
            conn.execute(
                "UPDATE tenders SET deadline = ?, emd = ?, payment_terms = ?, required_documents_json = ? WHERE id = ?",
                (facts.deadline, facts.emd, facts.payment_terms, json.dumps(facts.required_documents), tender_id))
            conn.executemany(
                "INSERT INTO rules (tender_id, text, clause, page, must_have) VALUES (?, ?, ?, ?, ?)",
                [(tender_id, r.text, r.clause, r.page, int(r.must_have)) for r in facts.rules])
        if verdicts := state.get("verdicts"):
            conn.executemany(
                "INSERT INTO verdicts (tender_id, rule_text, verdict, reason, clause, page, must_have)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(tender_id, v.rule_text, v.verdict, v.reason, v.clause, v.page, int(v.must_have))
                 for v in verdicts.verdicts])
        if checklist := state.get("checklist"):
            conn.executemany(
                "INSERT INTO checklist_items (tender_id, document, status, matched_file) VALUES (?, ?, ?, ?)",
                [(tender_id, i.document, i.status, i.matched_file) for i in checklist.items])
        if draft := state.get("draft"):
            review = state.get("review")
            conn.execute(
                "INSERT INTO drafts (tender_id, round, cover_letter, sections_json, review_json) VALUES (?, ?, ?, ?, ?)",
                (tender_id, state.get("review_rounds", 0), draft.cover_letter,
                 json.dumps([s.model_dump() for s in draft.sections]),
                 review.model_dump_json() if review else None))


@_locked
def get_run_output(conn, tender_id) -> dict:
    out = {"facts": None, "verdicts": None, "checklist": None, "draft": None, "review": None}
    tender = get_tender(conn, tender_id)
    if tender and tender["required_documents_json"] is not None:
        rules = [Rule(text=r["text"], clause=r["clause"], page=r["page"], must_have=bool(r["must_have"]))
                 for r in conn.execute("SELECT * FROM rules WHERE tender_id = ? ORDER BY id", (tender_id,))]
        out["facts"] = TenderFacts(deadline=tender["deadline"], emd=tender["emd"],
                                   payment_terms=tender["payment_terms"], rules=rules,
                                   required_documents=json.loads(tender["required_documents_json"]))

    verdict_rows = conn.execute("SELECT * FROM verdicts WHERE tender_id = ? ORDER BY id", (tender_id,)).fetchall()
    if verdict_rows:
        out["verdicts"] = EligibilityResult(verdicts=[
            RuleVerdict(rule_text=r["rule_text"], verdict=r["verdict"], reason=r["reason"],
                        clause=r["clause"], page=r["page"], must_have=bool(r["must_have"]))
            for r in verdict_rows])

    item_rows = conn.execute("SELECT * FROM checklist_items WHERE tender_id = ? ORDER BY id", (tender_id,)).fetchall()
    if item_rows:
        out["checklist"] = Checklist(items=[
            ChecklistItem(document=r["document"], status=r["status"], matched_file=r["matched_file"])
            for r in item_rows])

    draft_row = conn.execute("SELECT * FROM drafts WHERE tender_id = ? ORDER BY id DESC", (tender_id,)).fetchone()
    if draft_row:
        out["draft"] = BidDraft(cover_letter=draft_row["cover_letter"],
                                sections=[Section(**s) for s in json.loads(draft_row["sections_json"])])
        if draft_row["review_json"]:
            out["review"] = ReviewResult.model_validate_json(draft_row["review_json"])
    return out
