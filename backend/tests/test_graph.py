import pytest

from app import db, schemas
from app.graph import run_pipeline
from tests.samples import CHECKLIST, FACTS, verdicts

DRAFT = schemas.BidDraft(cover_letter="Dear Sir", sections=[])
COVERED = schemas.ReviewResult(matrix=[], gaps=[])
GAPS = schemas.ReviewResult(matrix=[], gaps=["Turnover of Rs 1 crore"])


@pytest.fixture
def setup():
    conn = db.connect(":memory:")
    cid = db.create_company(conn, "Woodworks", "desks", "Ernakulam", "₹1.4 crore", True, [], [])
    tid = db.create_tender(conn, "/tmp/t.pdf", "Desks")
    return conn, tid, cid


def fake_nodes(calls, verdict="pass", review=COVERED, checklist=None):
    def node(name, update):
        def fn(state):
            calls.append(name)
            return update(state) if callable(update) else update
        return fn

    def drafter(state):
        return {"draft": DRAFT, "review_rounds": state.get("review_rounds", 0) + ("review" in state)}

    return {
        "reader": node("reader", {"facts": FACTS}),
        "tracker": node("tracker", {}),
        "eligibility": node("eligibility", {"verdicts": verdicts(verdict)}),
        "stop": node("stop", {"status": "stopped", "stop_reason": "fails turnover"}),
        "checklist": checklist or node("checklist", {"checklist": CHECKLIST}),
        "drafter": node("drafter", drafter),
        "reviewer": node("reviewer", {"review": review}),
        "await_approval": node("await_approval", {"status": "awaiting_approval"}),
    }


def test_stops_on_must_have_fail(setup):
    conn, tid, cid = setup
    calls = []
    state = run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls, verdict="fail"))
    assert calls == ["reader", "tracker", "eligibility", "stop"]
    assert state["status"] == "stopped" and state["stop_reason"] == "fails turnover"
    assert db.get_tender(conn, tid)["status"] == "stopped"


def test_happy_path_one_review(setup):
    conn, tid, cid = setup
    calls = []
    state = run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls))
    assert calls == ["reader", "tracker", "eligibility", "checklist", "drafter", "reviewer", "await_approval"]
    assert state["status"] == "awaiting_approval"
    assert db.get_tender(conn, tid)["status"] == "awaiting_approval"
    assert db.get_run_output(conn, tid)["draft"] == DRAFT


def test_review_loop_max_two_sendbacks(setup):
    conn, tid, cid = setup
    calls = []
    state = run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls, review=GAPS))
    assert calls.count("drafter") == 3 and calls.count("reviewer") == 3
    assert calls[-1] == "await_approval" and state["review_rounds"] == 2


def flaky(calls, fail_times):
    attempts = []

    def checklist(state):
        calls.append("checklist")
        attempts.append(1)
        if len(attempts) <= fail_times:
            raise RuntimeError("boom")
        return {"checklist": CHECKLIST}
    return checklist


def test_node_retried_once_then_succeeds(setup):
    conn, tid, cid = setup
    calls = []
    state = run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls, checklist=flaky(calls, 1)))
    assert state["status"] == "awaiting_approval" and calls.count("checklist") == 2
    assert {"agent": "checklist", "message": "error, retrying: boom"} in [
        {"agent": l["agent"], "message": l["message"]} for l in db.get_log(conn, tid)]


def test_node_fails_twice_run_failed(setup):
    conn, tid, cid = setup
    calls = []
    state = run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls, checklist=flaky(calls, 99)))
    assert state["status"] == "failed" and calls.count("checklist") == 2
    assert db.get_tender(conn, tid)["status"] == "failed"
    log = [(l["agent"], l["message"]) for l in db.get_log(conn, tid)]
    assert ("checklist", "failed: boom") in log
    assert db.get_run_output(conn, tid)["facts"] == FACTS


def test_log_has_start_and_finish_per_node(setup):
    conn, tid, cid = setup
    run_pipeline(conn, None, tid, cid, nodes=fake_nodes([]))
    log = [(l["agent"], l["message"]) for l in db.get_log(conn, tid)]
    names = ["reader", "tracker", "eligibility", "checklist", "drafter", "reviewer", "await_approval"]
    assert log == [pair for n in names for pair in ((n, "started"), (n, "finished"))]


def test_reason_and_run_id_saved(setup):
    conn, tid, cid = setup
    run_pipeline(conn, None, tid, cid, nodes=fake_nodes([], verdict="fail"), run_id="run-7")
    t = db.get_tender(conn, tid)
    assert (t["reason"], t["current_run_id"]) == ("fails turnover", "run-7")
    assert {l["agent"] for l in db.get_log(conn, tid, "run-7")} == {"reader", "tracker", "eligibility", "stop"}


def test_failure_reason_saved(setup):
    conn, tid, cid = setup
    calls = []
    run_pipeline(conn, None, tid, cid, nodes=fake_nodes(calls, checklist=flaky(calls, 99)))
    assert db.get_tender(conn, tid)["reason"] == "checklist failed: boom"


def test_runs_wait_for_each_other(setup):
    """Two runs at once would hit Groq's tokens-per-minute limit: the second waits for the first."""
    import threading
    import time

    conn, tid, cid = setup
    order, release = [], threading.Event()

    def slow_reader(state):
        order.append("first-start")
        release.wait(2)
        order.append("first-end")
        return {"facts": FACTS}

    def quick_reader(state):
        order.append("second-start")
        return {"facts": FACTS}

    def nodes(reader):
        n = fake_nodes([], verdict="pass")
        n["reader"] = reader
        return n

    first = threading.Thread(target=run_pipeline, args=(conn, None, tid, cid, nodes(slow_reader)))
    second = threading.Thread(target=run_pipeline, args=(conn, None, tid, cid, nodes(quick_reader)))
    first.start()
    time.sleep(0.2)
    second.start()
    time.sleep(0.2)
    assert order == ["first-start"]          # the second run has not begun
    release.set()
    first.join(5), second.join(5)
    assert order[:3] == ["first-start", "first-end", "second-start"]
