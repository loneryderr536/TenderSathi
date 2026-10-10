from datetime import datetime

from app import schemas
from app.scoring import bid_score
from tests.samples import CHECKLIST, verdicts

NOW = datetime(2026, 10, 10, 12, 0)


def out(v, checklist=CHECKLIST, concessions=None):
    return {"verdicts": v, "checklist": checklist, "concessions": concessions}


def test_no_score_before_a_run():
    assert bid_score({"verdicts": None}, None) is None


def test_must_have_fail_is_no_bid():
    s = bid_score(out(verdicts("fail")), None, NOW)
    assert s["score"] == 0 and s["decision"] == "no_bid" and "Fails a must-have rule" in s["reasons"][0]


def test_all_clear_is_bid_and_documents_and_deadline_lower_it():
    clear = bid_score(out(verdicts("pass"), schemas.Checklist(items=[])), "2026-11-10T17:00", NOW)
    assert clear == {"score": 100, "decision": "bid", "reasons": ["You meet every rule and hold every document"]}
    need = schemas.Checklist(items=[schemas.ChecklistItem(document="ISO 9001", status="need")])
    tight = bid_score(out(verdicts("pass"), need), "2026-10-12T17:00", NOW)   # one document missing, 2 days left
    assert tight["score"] == 100 - 8 - 30 and tight["decision"] == "bid_with_care"


def test_passed_deadline_and_concession_bonus():
    assert bid_score(out(verdicts("pass")), "2026-10-01T17:00", NOW)["decision"] == "no_bid"
    bonus = schemas.Concessions(items=[schemas.Concession(benefit="EMD exempt", clause="6", page=2)])
    s = bid_score(out(verdicts("pass"), schemas.Checklist(items=[]), bonus), None, NOW)
    assert s["score"] == 100 and any("EMD exempt" in r for r in s["reasons"])
