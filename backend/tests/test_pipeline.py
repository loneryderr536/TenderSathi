import pytest

from app import db, schemas
from app.agents import checklist, drafter, eligibility, reader, reviewer
from app.graph import business_lines, run_pipeline
from app.memory import Memory
from tests.fakes import HashEmbedding
from tests.pdfs import make_pdf
from tests.samples import CHECKLIST, FACTS, verdicts

DRAFT = schemas.BidDraft(cover_letter="Dear Sir", sections=[])
REVIEW = schemas.ReviewResult(matrix=[], gaps=[])
COMPANY = dict(name="Ernakulam Woodworks", products="desks, tables", location="Ernakulam",
               turnover="₹1.4 crore", udyam=True, documents=["gst.pdf"],
               past_orders=[{"buyer": "KSEB", "item": "desks", "value": "₹8 lakh", "year": 2025}])


def test_business_lines():
    assert business_lines({**COMPANY, "udyam": 1}) == [
        "Company: Ernakulam Woodworks", "Products: desks, tables", "Location: Ernakulam",
        "Yearly turnover: ₹1.4 crore", "Udyam/MSE registered: yes",
        "Past order: desks for KSEB, ₹8 lakh, 2025", "Holds document: gst.pdf"]


@pytest.fixture
def world(tmp_path, monkeypatch):
    conn = db.connect(":memory:")
    mem = Memory(str(tmp_path / "chroma"), embedding_function=HashEmbedding())
    cid = db.create_company(conn, **COMPANY)
    pdf = make_pdf(tmp_path, ["1. Scope\nSupply 200 desks.\n4.1 Turnover of Rs 1 crore\n"])
    tid = db.create_tender(conn, pdf, "Desks")
    seen = {}

    def fake(name, result):
        def fn(*args):
            seen[name] = args
            return result(*args) if callable(result) else result
        return fn

    monkeypatch.setattr(reader, "extract_facts", fake("reader", FACTS))
    monkeypatch.setattr(eligibility, "judge_eligibility", fake("eligibility", verdicts()))
    monkeypatch.setattr(checklist, "build_checklist", fake("checklist", CHECKLIST))
    monkeypatch.setattr(drafter, "draft_bid", fake("drafter", DRAFT))
    monkeypatch.setattr(reviewer, "review_draft", fake("reviewer", REVIEW))
    return conn, mem, tid, cid, seen, monkeypatch, fake, tmp_path


def test_end_to_end_awaiting_approval(world):
    conn, mem, tid, cid, seen, *_ = world
    state = run_pipeline(conn, mem, tid, cid)
    assert state["status"] == "awaiting_approval"
    assert "[clause 4.1, page 1]" in seen["reader"][0]
    assert "Yearly turnover: ₹1.4 crore" in seen["eligibility"][1]
    assert seen["eligibility"][0] == FACTS.rules
    assert seen["checklist"] == (FACTS.required_documents, ["gst.pdf"])
    assert seen["drafter"] == (FACTS, business_lines(db.get_company(conn, cid)), [])
    assert seen["reviewer"] == (DRAFT, FACTS.rules)
    out = db.get_run_output(conn, tid)
    assert out["draft"] == DRAFT and out["review"].all_covered
    assert [l["agent"] for l in db.get_log(conn, tid) if l["message"] == "finished"] == \
        ["reader", "eligibility", "checklist", "drafter", "reviewer", "await_approval"]


def test_end_to_end_stop_reason(world):
    conn, mem, tid, cid, seen, monkeypatch, fake, _ = world
    failing = verdicts("fail", rules=FACTS.rules[:1])
    monkeypatch.setattr(eligibility, "judge_eligibility", fake("eligibility", failing))
    state = run_pipeline(conn, mem, tid, cid)
    assert state["status"] == "stopped"
    assert state["stop_reason"] == \
        "Fails must-have rule(s): Turnover of Rs 1 crore (clause 4.1, page 1): per profile"
    assert "checklist" not in seen


def test_scanned_pdf_fails_run_with_message(world):
    conn, mem, _, cid, _, _, _, tmp_path = world
    tid = db.create_tender(conn, make_pdf(tmp_path, [""], name="scan.pdf"), "Scanned")
    state = run_pipeline(conn, mem, tid, cid)
    assert state["status"] == "failed"
    assert ("reader", "failed: This looks like a scanned PDF; please use a text PDF") in [
        (l["agent"], l["message"]) for l in db.get_log(conn, tid)]


def test_reader_gets_only_key_clauses_of_a_long_tender(world):
    from app.agents.reader import READER_BUDGET_TOKENS, estimate_tokens
    conn, mem, _, cid, seen, _, _, tmp_path = world
    spec_pages = [f"{n}. Technical specification {n}\n" + "Seasoned teak with polyurethane finish.\n" * 45
                  for n in range(10, 60)]
    pages = ["Notice inviting tender\n4.1 Turnover of Rs 60 lakh\n7. Payment terms: 30 days after delivery\n",
             *spec_pages]
    tid = db.create_tender(conn, make_pdf(tmp_path, pages, name="long.pdf"), "Long tender")
    run_pipeline(conn, mem, tid, cid)
    text = seen["reader"][0]
    assert "[clause 4.1, page 1]" in text and "Payment terms" in text
    assert estimate_tokens(text) <= READER_BUDGET_TOKENS + 200     # + the "[clause, page]" markers
