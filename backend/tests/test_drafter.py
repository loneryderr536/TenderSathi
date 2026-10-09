from app import llm, schemas
from app.agents.drafter import draft_bid
from tests.fakes import FakeLLM
from tests.samples import FACTS

DRAFT = schemas.BidDraft(cover_letter="Dear Sir", sections=[schemas.Section(title="Experience", body="KSEB")])


def run(monkeypatch, notes):
    fake = FakeLLM([DRAFT])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    return fake, draft_bid(FACTS, ["Company: Ernakulam Woodworks"], notes)


def test_one_call_with_facts_and_business(monkeypatch):
    fake, draft = run(monkeypatch, [])
    assert draft == DRAFT
    assert fake.agents == ["drafter"] and len(fake.calls) == 1 and fake.calls[0][0] is schemas.BidDraft
    prompt = str(fake.calls[0][1])
    assert FACTS.rules[0].text in prompt and "Ernakulam Woodworks" in prompt
    assert "[PRICE: to be filled by owner]" in prompt


def test_reviewer_notes_included(monkeypatch):
    fake, _ = run(monkeypatch, ["Rule 4.2 ISO certificate not addressed"])
    assert "Rule 4.2 ISO certificate not addressed" in str(fake.calls[0][1])
