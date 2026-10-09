import pytest

from app import db, schemas
from tests.samples import CHECKLIST, FACTS, RULE_TURNOVER, verdicts


@pytest.fixture
def conn():
    return db.connect(":memory:")


def make_company(conn):
    return db.create_company(conn, "Ernakulam Woodworks", "desks, tables", "Ernakulam", "₹1.4 crore", True,
                             ["gst.pdf"], [{"buyer": "KSEB", "item": "desks", "value": "₹8 lakh", "year": 2025}])


def test_company_roundtrip(conn):
    c = db.get_company(conn, make_company(conn))
    assert c["name"] == "Ernakulam Woodworks" and c["udyam"] in (1, True)
    assert c["documents"] == ["gst.pdf"] and c["past_orders"][0]["buyer"] == "KSEB"


def test_missing_rows_are_none(conn):
    assert db.get_company(conn, 99) is None and db.get_tender(conn, 99) is None


def test_tender_create_and_status(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "Desks for schools")
    assert db.get_tender(conn, tid)["status"] == "new"
    db.set_tender_status(conn, tid, "running")
    assert db.get_tender(conn, tid)["status"] == "running"


def test_log_order_and_filter(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.add_log(conn, tid, "r1", "reader", "started")
    db.add_log(conn, tid, "r2", "reader", "started")
    db.add_log(conn, tid, "r2", "reader", "finished")
    assert [l["message"] for l in db.get_log(conn, tid, "r2")] == ["started", "finished"]
    assert len(db.get_log(conn, tid)) == 3


def test_run_output_roundtrip_and_rerun_replaces(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    draft = schemas.BidDraft(cover_letter="Dear Sir", sections=[schemas.Section(title="Experience", body="KSEB")])
    review = schemas.ReviewResult(matrix=[schemas.ComplianceRow(
        rule_text=RULE_TURNOVER.text, must_have=True, covered=True, where="Experience")], gaps=[])
    state = {"facts": FACTS, "verdicts": verdicts(), "checklist": CHECKLIST, "draft": draft,
             "review": review, "review_rounds": 1}
    db.save_run_output(conn, tid, state)
    out = db.get_run_output(conn, tid)
    assert out == {"facts": FACTS, "verdicts": verdicts(), "checklist": CHECKLIST, "draft": draft, "review": review}
    assert db.get_tender(conn, tid)["deadline"] == FACTS.deadline

    one_rule = FACTS.model_copy(update={"rules": [RULE_TURNOVER]})
    db.save_run_output(conn, tid, {"facts": one_rule})
    assert len(db.get_run_output(conn, tid)["facts"].rules) == 1
    assert conn.execute("SELECT COUNT(*) FROM rules WHERE tender_id=?", (tid,)).fetchone()[0] == 1


def test_partial_output(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.save_run_output(conn, tid, {"facts": FACTS})
    out = db.get_run_output(conn, tid)
    assert out["facts"] == FACTS
    assert out["verdicts"] is None and out["checklist"] is None and out["draft"] is None and out["review"] is None


def test_rerun_without_facts_clears_old_facts(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.save_run_output(conn, tid, {"facts": FACTS})
    db.save_run_output(conn, tid, {})          # rerun failed in the reader
    assert db.get_run_output(conn, tid)["facts"] is None


def test_save_run_output_is_atomic(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.save_run_output(conn, tid, {"facts": FACTS})

    class Broken:                      # verdicts object that blows up mid-save
        @property
        def verdicts(self):
            raise RuntimeError("disk full")
    with pytest.raises(RuntimeError):
        db.save_run_output(conn, tid, {"facts": FACTS.model_copy(update={"rules": []}), "verdicts": Broken()})
    db.add_log(conn, tid, "r", "x", "y")   # another write commits; the half-done save must not
    assert db.get_run_output(conn, tid)["facts"] == FACTS


def test_concurrent_writes_from_threads(tmp_path):
    import threading
    conn = db.connect(str(tmp_path / "app.db"))
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    errors = []

    def work(i):
        try:
            for _ in range(30):
                db.add_log(conn, tid, f"r{i}", "reader", "started")
                db.save_run_output(conn, tid, {"facts": FACTS})
                db.get_log(conn, tid)
                db.get_run_output(conn, tid)
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert conn.execute("SELECT COUNT(*) FROM rules WHERE tender_id=?", (tid,)).fetchone()[0] == 2


def test_tender_reason_and_run_id(conn):
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.set_tender_status(conn, tid, "stopped", reason="Fails turnover")
    db.set_current_run(conn, tid, "abc")
    t = db.get_tender(conn, tid)
    assert (t["status"], t["reason"], t["current_run_id"]) == ("stopped", "Fails turnover", "abc")
