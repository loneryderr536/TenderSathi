from app import llm, schemas
from app.agents import reader
from tests.fakes import FakeLLM

FACTS = schemas.TenderFacts(
    deadline="2026-10-30", emd="₹50,000", payment_terms="30 days after delivery",
    rules=[schemas.Rule(text="Turnover ≥ ₹1 crore", clause="4.1", page=7, must_have=True)],
    required_documents=["GST certificate"],
)


def test_reader_extracts_in_one_call(monkeypatch):
    fake = FakeLLM([FACTS])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    long_text = "Clause text. " * 20_000
    assert reader.extract_facts(long_text) == FACTS
    assert fake.agents == ["reader"]
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is schemas.TenderFacts
    assert long_text in str(fake.calls[0][1])


from app.agents.reader import estimate_tokens, reader_input, select_key_clauses
from app.schemas import Clause


def c(clause, text, page=1):
    return Clause(text=text, clause=clause, page=page)


def test_small_tender_keeps_every_clause_in_order():
    clauses = [c("", "Notice inviting tender"), c("1", "Scope of work: desks"), c("4.1", "Turnover of Rs 60 lakh")]
    assert select_key_clauses(clauses, budget_tokens=5000) == clauses


def test_large_tender_keeps_key_clauses_within_budget():
    filler = [c(f"{i}", f"{i}. Technical specification of item {i}. " + "Grain, finish and joinery details. " * 60)
              for i in range(10, 40)]
    key = [c("4.1", "4.1 Average annual turnover of Rs 60 lakh. Mandatory."),
           c("5", "5. Documents to be submitted: GST certificate, PAN card."),
           c("6", "6. Earnest money deposit (EMD) of Rs 50,000."),
           c("7", "7. Payment terms: 100% within 30 days of delivery."),
           c("3", "3. Last date for bid submission: 30 October 2026.")]
    clauses = [c("", "Notice inviting tender No. 14"), *key[4:], *filler[:15], *key[:4], *filler[15:]]
    picked = select_key_clauses(clauses, budget_tokens=1500)
    assert all(k in picked for k in key)
    assert picked[0] == clauses[0]                                        # title/preamble kept
    assert [p for p in clauses if p in picked] == picked                  # original order
    assert sum(estimate_tokens(p.text) for p in picked) <= 1500
    assert len(picked) < len(clauses)


def test_one_huge_key_clause_is_truncated_to_budget():
    huge = c("4", "4. Eligibility criteria. " + "The bidder shall meet the turnover rule. " * 2000)
    picked = select_key_clauses([huge], budget_tokens=1000)
    assert len(picked) == 1 and picked[0].clause == "4"
    assert estimate_tokens(picked[0].text) <= 1000


def test_reader_input_cites_clause_and_page():
    assert reader_input([c("4.1", "Turnover", page=7)]) == "[clause 4.1, page 7] Turnover"
