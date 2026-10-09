from datetime import date, datetime

from app import llm, schemas
from app.agents.tracker import compare_tenders, parse_deadline
from tests.fakes import FakeLLM
from tests.samples import FACTS


def test_deadline_parsed_in_one_call(monkeypatch):
    fake = FakeLLM([schemas.DeadlineInfo(deadline_at="2026-10-30T15:00")])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    assert parse_deadline("30 October 2026, 3:00 PM", today=date(2026, 10, 9)) == datetime(2026, 10, 30, 15, 0)
    assert fake.agents == ["tracker"] and len(fake.calls) == 1
    prompt = str(fake.calls[0][1])
    assert "30 October 2026, 3:00 PM" in prompt and "2026-10-09" in prompt


def test_blank_deadline_makes_no_call(monkeypatch):
    fake = FakeLLM([])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    assert parse_deadline("  ", today=date(2026, 10, 9)) is None and fake.calls == []


def test_unparseable_answer_is_none(monkeypatch):
    for answer in [None, "", "next Tuesday", "2026-13-45T10:00"]:
        fake = FakeLLM([schemas.DeadlineInfo(deadline_at=answer)])
        monkeypatch.setattr(llm, "get_llm", fake.factory)
        assert parse_deadline("whenever", today=date(2026, 10, 9)) is None


def test_compare_tenders_one_call_with_both_versions(monkeypatch):
    new = FACTS.model_copy(update={"deadline": "6 November 2026, 3:00 PM", "emd": "₹75,000"})
    changes = schemas.TenderChanges(changes=[
        schemas.Change(field="deadline", before=FACTS.deadline, after=new.deadline, summary="Deadline extended by a week")],
        affects_eligibility=False)
    fake = FakeLLM([changes])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    assert compare_tenders(FACTS, new) == changes
    assert fake.agents == ["tracker"] and len(fake.calls) == 1
    prompt = str(fake.calls[0][1])
    assert FACTS.deadline in prompt and "6 November 2026, 3:00 PM" in prompt and "₹75,000" in prompt


def test_identical_versions_make_no_call(monkeypatch):
    fake = FakeLLM([])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    result = compare_tenders(FACTS, FACTS.model_copy())
    assert result.changes == [] and result.affects_eligibility is False and fake.calls == []
