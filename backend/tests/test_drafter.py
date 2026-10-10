from app import llm, schemas
from app.agents.drafter import PRICE_PLACEHOLDER, draft_bid, ensure_price_placeholder
from tests.fakes import FakeLLM
from tests.samples import FACTS

DRAFT = schemas.BidDraft(cover_letter="Dear Sir", sections=[schemas.Section(title="Experience", body="KSEB")])


def run(monkeypatch, notes):
    fake = FakeLLM([DRAFT])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    return fake, draft_bid(FACTS, ["Company: Ernakulam Woodworks"], notes)


def test_one_call_with_facts_and_business(monkeypatch):
    fake, draft = run(monkeypatch, [])
    assert draft.cover_letter == DRAFT.cover_letter and draft.sections[0] == DRAFT.sections[0]
    assert fake.agents == ["drafter"] and len(fake.calls) == 1 and fake.calls[0][0] is schemas.BidDraft
    prompt = str(fake.calls[0][1])
    assert FACTS.rules[0].text in prompt and "Ernakulam Woodworks" in prompt
    assert "[PRICE: to be filled by owner]" in prompt


def test_reviewer_notes_included(monkeypatch):
    fake, _ = run(monkeypatch, ["Rule 4.2 ISO certificate not addressed"])
    assert "Rule 4.2 ISO certificate not addressed" in str(fake.calls[0][1])


def test_price_placeholder_added_when_model_leaves_it_out():
    out = ensure_price_placeholder(DRAFT)
    assert out.sections[-1].title == "Price" and PRICE_PLACEHOLDER in out.sections[-1].body
    assert len(out.sections) == len(DRAFT.sections) + 1


def test_price_placeholder_kept_when_present():
    present = schemas.BidDraft(cover_letter=f"Our price is {PRICE_PLACEHOLDER}.", sections=[])
    assert ensure_price_placeholder(present) == present
