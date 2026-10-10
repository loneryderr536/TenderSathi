"""SQLite setup: companies, tenders, runs, agent log, checklist items."""
import functools
import json
import sqlite3
import threading

from app.schemas import (BidDraft, Checklist, ChecklistItem, Concession, Concessions, EligibilityResult, ReviewResult, Rule,
                         RuleVerdict, Section, TenderChanges, TenderFacts)

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY, name TEXT, products TEXT, location TEXT, turnover TEXT, udyam INTEGER);
CREATE TABLE IF NOT EXISTS company_documents (
    id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
CREATE TABLE IF NOT EXISTS past_orders (
    id INTEGER PRIMARY KEY, company_id INTEGER, buyer TEXT, item TEXT, value TEXT, year INTEGER);
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY, pdf_path TEXT, title TEXT, deadline TEXT, emd TEXT, payment_terms TEXT,
    required_documents_json TEXT, status TEXT, reason TEXT, current_run_id TEXT,
    deadline_at TEXT, changes_json TEXT);
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY, tender_id INTEGER, text TEXT, clause TEXT, page INTEGER, must_have INTEGER);
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY, tender_id INTEGER, rule_text TEXT, verdict TEXT, reason TEXT,
    clause TEXT, page INTEGER, must_have INTEGER);
CREATE TABLE IF NOT EXISTS checklist_items (
    id INTEGER PRIMARY KEY, tender_id INTEGER, document TEXT, status TEXT, matched_file TEXT);
CREATE TABLE IF NOT EXISTS concessions (
    id INTEGER PRIMARY KEY, tender_id INTEGER, benefit TEXT, clause TEXT, page INTEGER);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY, tender_id INTEGER, round INTEGER, cover_letter TEXT, sections_json TEXT,
    review_json TEXT);
CREATE TABLE IF NOT EXISTS screenings (
    id INTEGER PRIMARY KEY, tender_id INTEGER, company_id INTEGER, verdicts_json TEXT);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY, tender_id INTEGER, kind TEXT, body_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY, tender_id INTEGER, agent TEXT, item TEXT, correct INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS scout_runs (
    id INTEGER PRIMARY KEY, found INTEGER, added INTEGER, queued INTEGER, message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY, tender_id INTEGER, company_id INTEGER, amount REAL, delivery_days INTEGER,
    note TEXT, status TEXT DEFAULT 'submitted', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, role TEXT, password_hash TEXT,
    company_id INTEGER, department TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS agent_log (
    id INTEGER PRIMARY KEY, tender_id INTEGER, run_id TEXT, agent TEXT, message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

OUTPUT_TABLES = ("rules", "verdicts", "checklist_items", "concessions", "drafts")

# One connection is shared by request handlers and background runs, so every helper
# takes this lock: no interleaved transactions, no "recursive use of cursors".
_lock = threading.RLock()


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return wrapper


# Columns added after the first release: older database files get them on connect.
ADDED_COLUMNS = [("tenders", "reason", "TEXT"), ("tenders", "current_run_id", "TEXT"),
                 ("tenders", "deadline_at", "TEXT"), ("tenders", "changes_json", "TEXT"),
                 # Where a tender came from: "upload" (a business), "portal" (the Scout), "draft" (a government
                 # officer checking a tender before publishing it; never shown to businesses).
                 ("tenders", "kind", "TEXT DEFAULT 'upload'"), ("tenders", "source_id", "TEXT"),
                 ("tenders", "portal", "TEXT"), ("tenders", "buyer", "TEXT"), ("tenders", "published", "TEXT"),
                 # A private owner's request for quotation ("private" kind) and drafts belong to the user who made them.
                 ("tenders", "owner_user_id", "INTEGER"), ("tenders", "advance_percent", "INTEGER")]


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for table, column, kind in ADDED_COLUMNS:
        if column not in {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
    conn.commit()
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
def update_company(conn, company_id, name, products, location, turnover, udyam: bool,
                   documents: list[str], past_orders: list[dict]) -> bool:
    """Replace a company's profile, documents and past orders. False if the id is unknown."""
    with conn:
        cur = conn.execute(
            "UPDATE companies SET name = ?, products = ?, location = ?, turnover = ?, udyam = ? WHERE id = ?",
            (name, products, location, turnover, int(udyam), company_id))
        if cur.rowcount == 0:
            return False
        conn.execute("DELETE FROM company_documents WHERE company_id = ?", (company_id,))
        conn.execute("DELETE FROM past_orders WHERE company_id = ?", (company_id,))
        conn.executemany("INSERT INTO company_documents (company_id, name) VALUES (?, ?)",
                         [(company_id, d) for d in documents])
        conn.executemany(
            "INSERT INTO past_orders (company_id, buyer, item, value, year) VALUES (?, ?, ?, ?, ?)",
            [(company_id, o["buyer"], o["item"], o["value"], o["year"]) for o in past_orders])
    return True


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
def create_tender(conn, pdf_path, title, kind="upload", source_id=None, portal=None, buyer=None,
                  published=None, owner_user_id=None, advance_percent=None) -> int:
    cur = conn.execute(
        "INSERT INTO tenders (pdf_path, title, status, kind, source_id, portal, buyer, published, owner_user_id,"
        " advance_percent) VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?, ?)",
        (pdf_path, title, kind, source_id, portal, buyer, published, owner_user_id, advance_percent))
    conn.commit()
    return cur.lastrowid


@_locked
def tender_by_source(conn, source_id) -> dict | None:
    row = conn.execute("SELECT * FROM tenders WHERE source_id = ?", (source_id,)).fetchone()
    return dict(row) if row else None


@_locked
def list_companies(conn) -> list[dict]:
    return [get_company(conn, r["id"]) for r in conn.execute("SELECT id FROM companies ORDER BY id")]


@_locked
def get_tender(conn, tender_id) -> dict | None:
    row = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()
    return dict(row) if row else None


@_locked
def list_tenders(conn, kinds=("upload", "portal", "private")) -> list[dict]:
    """Newest first. Businesses see uploads, portal tenders and private RFQs; drafts are listed only on request."""
    marks = ", ".join("?" * len(kinds))
    return [dict(r) for r in conn.execute(
        "SELECT id, title, deadline, deadline_at, emd, status, reason, kind, portal, buyer, published, owner_user_id,"
        " advance_percent FROM tenders"
        f" WHERE COALESCE(kind, 'upload') IN ({marks}) ORDER BY id DESC", kinds)]


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
def claim_run(conn, tender_id, run_id) -> bool:
    """Atomically mark the tender running for this run; False if a run is already going."""
    cur = conn.execute(
        "UPDATE tenders SET status = 'running', current_run_id = ?, reason = NULL"
        " WHERE id = ? AND status != 'running'", (run_id, tender_id))
    conn.commit()
    return cur.rowcount == 1


@_locked
def reset_stuck_runs(conn) -> int:
    """At startup: runs that were going when the server stopped can never finish."""
    cur = conn.execute(
        "UPDATE tenders SET status = 'failed', reason = 'Server restarted during run' WHERE status = 'running'")
    conn.commit()
    return cur.rowcount


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
        deadline_at = state.get("deadline_at")
        conn.execute("UPDATE tenders SET deadline_at = ? WHERE id = ?",
                     (deadline_at.isoformat() if deadline_at else None, tender_id))

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
        if concessions := state.get("concessions"):
            conn.executemany(
                "INSERT INTO concessions (tender_id, benefit, clause, page) VALUES (?, ?, ?, ?)",
                [(tender_id, c.benefit, c.clause, c.page) for c in concessions.items])
        if draft := state.get("draft"):
            review = state.get("review")
            conn.execute(
                "INSERT INTO drafts (tender_id, round, cover_letter, sections_json, review_json) VALUES (?, ?, ?, ?, ?)",
                (tender_id, state.get("review_rounds", 0), draft.cover_letter,
                 json.dumps([s.model_dump() for s in draft.sections]),
                 review.model_dump_json() if review else None))


@_locked
def update_draft(conn, tender_id, draft: BidDraft):
    """Overwrite the final draft's text (owner edits); its review stays."""
    conn.execute(
        "UPDATE drafts SET cover_letter = ?, sections_json = ? WHERE id = "
        "(SELECT id FROM drafts WHERE tender_id = ? ORDER BY id DESC LIMIT 1)",
        (draft.cover_letter, json.dumps([s.model_dump() for s in draft.sections]), tender_id))
    conn.commit()


@_locked
def record_tender_change(conn, tender_id, new_pdf_path, changes: TenderChanges):
    """A corrigendum replaced the tender PDF: keep what changed and mark the tender for a fresh run."""
    conn.execute("UPDATE tenders SET pdf_path = ?, changes_json = ?, status = 'changed', reason = NULL WHERE id = ?",
                 (new_pdf_path, changes.model_dump_json(), tender_id))
    conn.commit()


@_locked
def get_changes(conn, tender_id) -> TenderChanges | None:
    row = conn.execute("SELECT changes_json FROM tenders WHERE id = ?", (tender_id,)).fetchone()
    return TenderChanges.model_validate_json(row["changes_json"]) if row and row["changes_json"] else None


@_locked
def get_run_output(conn, tender_id) -> dict:
    out = {"facts": None, "verdicts": None, "checklist": None, "concessions": None, "draft": None,
           "review": None}
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

    concession_rows = conn.execute("SELECT * FROM concessions WHERE tender_id = ? ORDER BY id", (tender_id,)).fetchall()
    if concession_rows:
        out["concessions"] = Concessions(items=[
            Concession(benefit=r["benefit"], clause=r["clause"], page=r["page"]) for r in concession_rows])

    draft_row = conn.execute("SELECT * FROM drafts WHERE tender_id = ? ORDER BY id DESC", (tender_id,)).fetchone()
    if draft_row:
        out["draft"] = BidDraft(cover_letter=draft_row["cover_letter"],
                                sections=[Section(**s) for s in json.loads(draft_row["sections_json"])])
        if draft_row["review_json"]:
            out["review"] = ReviewResult.model_validate_json(draft_row["review_json"])
    return out


# --- Government screenings, saved reports, feedback and scout runs ---------------------------------------

@_locked
def save_screenings(conn, tender_id, results: dict[int, EligibilityResult]):
    """Replace the participation screening of a tender: one eligibility result per registered business."""
    with conn:
        conn.execute("DELETE FROM screenings WHERE tender_id = ?", (tender_id,))
        conn.executemany("INSERT INTO screenings (tender_id, company_id, verdicts_json) VALUES (?, ?, ?)",
                         [(tender_id, cid, r.model_dump_json()) for cid, r in results.items()])


@_locked
def get_screenings(conn, tender_id) -> dict[int, EligibilityResult]:
    return {r["company_id"]: EligibilityResult.model_validate_json(r["verdicts_json"]) for r in conn.execute(
        "SELECT company_id, verdicts_json FROM screenings WHERE tender_id = ? ORDER BY company_id", (tender_id,))}


@_locked
def save_report(conn, tender_id, kind: str, body: dict):
    """The latest report of a kind ("fairness", "gap_plan") for a tender."""
    with conn:
        conn.execute("DELETE FROM reports WHERE tender_id = ? AND kind = ?", (tender_id, kind))
        conn.execute("INSERT INTO reports (tender_id, kind, body_json) VALUES (?, ?, ?)",
                     (tender_id, kind, json.dumps(body)))


@_locked
def get_report(conn, tender_id, kind: str) -> dict | None:
    row = conn.execute("SELECT body_json FROM reports WHERE tender_id = ? AND kind = ?", (tender_id, kind)).fetchone()
    return json.loads(row["body_json"]) if row else None


@_locked
def add_feedback(conn, tender_id, agent, item, correct: bool):
    """One owner judgement on one agent answer; a newer judgement on the same item replaces the old one."""
    with conn:
        conn.execute("DELETE FROM feedback WHERE tender_id = ? AND agent = ? AND item = ?", (tender_id, agent, item))
        conn.execute("INSERT INTO feedback (tender_id, agent, item, correct) VALUES (?, ?, ?, ?)",
                     (tender_id, agent, item, int(correct)))


@_locked
def get_feedback(conn, tender_id=None) -> list[dict]:
    if tender_id is None:
        return [dict(r) for r in conn.execute("SELECT * FROM feedback ORDER BY id")]
    return [dict(r) for r in conn.execute("SELECT * FROM feedback WHERE tender_id = ? ORDER BY id", (tender_id,))]


@_locked
def add_scout_run(conn, found, added, queued, message=""):
    conn.execute("INSERT INTO scout_runs (found, added, queued, message) VALUES (?, ?, ?, ?)",
                 (found, added, queued, message))
    conn.commit()


@_locked
def list_scout_runs(conn, limit=10) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM scout_runs ORDER BY id DESC LIMIT ?", (limit,))]


@_locked
def all_log(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM agent_log ORDER BY id")]


# --- Users and login sessions ---------------------------------------------------------------------------

USER_FIELDS = "id, email, name, role, company_id, department"


@_locked
def create_user(conn, email, name, role, password_hash, company_id=None, department=None) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, name, role, password_hash, company_id, department) VALUES (?, ?, ?, ?, ?, ?)",
        (email, name, role, password_hash, company_id, department))
    conn.commit()
    return cur.lastrowid


@_locked
def user_by_email(conn, email) -> dict | None:
    """Includes password_hash, for checking a login."""
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


@_locked
def get_user(conn, user_id) -> dict | None:
    row = conn.execute(f"SELECT {USER_FIELDS} FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


@_locked
def set_user_company(conn, user_id, company_id):
    conn.execute("UPDATE users SET company_id = ? WHERE id = ?", (company_id, user_id))
    conn.commit()


@_locked
def create_session(conn, token, user_id):
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()


@_locked
def user_for_token(conn, token) -> dict | None:
    row = conn.execute(f"SELECT {', '.join('u.' + f for f in USER_FIELDS.split(', '))} FROM sessions s "
                       "JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)).fetchone()
    return dict(row) if row else None


@_locked
def delete_session(conn, token):
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


# --- Quotations on private requests for quotation ---------------------------------------------------------

@_locked
def save_quotation(conn, tender_id, company_id, amount, delivery_days, note) -> int:
    """One quotation per business per request: sending again replaces it."""
    with conn:
        conn.execute("DELETE FROM quotations WHERE tender_id = ? AND company_id = ?", (tender_id, company_id))
        cur = conn.execute("INSERT INTO quotations (tender_id, company_id, amount, delivery_days, note) VALUES (?, ?, ?, ?, ?)",
                           (tender_id, company_id, amount, delivery_days, note))
    return cur.lastrowid


@_locked
def list_quotations(conn, tender_id) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT q.*, c.name AS company_name, c.location AS company_location, c.udyam AS company_udyam"
        " FROM quotations q JOIN companies c ON c.id = q.company_id WHERE q.tender_id = ? ORDER BY q.amount",
        (tender_id,))]


@_locked
def accept_quotation(conn, tender_id, quotation_id) -> bool:
    with conn:
        cur = conn.execute("UPDATE quotations SET status = 'accepted' WHERE id = ? AND tender_id = ?", (quotation_id, tender_id))
        if cur.rowcount == 0:
            return False
        conn.execute("UPDATE quotations SET status = 'declined' WHERE tender_id = ? AND id != ?", (tender_id, quotation_id))
        conn.execute("UPDATE tenders SET status = 'awarded' WHERE id = ?", (tender_id,))
    return True
