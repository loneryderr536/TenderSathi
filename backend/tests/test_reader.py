from app import llm, schemas
from app.agents import reader
from tests.fakes import FakeLLM

FACTS = schemas.TenderFacts(
    deadline="2026-10-30", emd="₹50,000", payment_terms="30 days after delivery",
    rules=[schemas.Rule(text="Turnover ≥ ₹1 crore", clause="4.1", page=7, must_have=True)],
    required_documents=["GST certificate"],
)


def test_reader_extracts_once_with_haiku(monkeypatch):
    fake = FakeLLM([FACTS])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    long_text = "Clause text. " * 20_000
    assert reader.extract_facts(long_text) == FACTS
    assert fake.agents == ["reader"]
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is schemas.TenderFacts
    assert long_text in str(fake.calls[0][1])
