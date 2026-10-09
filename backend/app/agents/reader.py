"""Reader agent: extracts deadline, deposit, eligibility rules and required documents."""
import math
import re

from app import llm
from app.schemas import Clause, TenderFacts

# Groq allows 8,000 tokens per minute per model, prompt and answer together, so the
# Reader sends only the clauses that matter, in one call.
READER_BUDGET_TOKENS = 5000

KEY_CLAUSE = re.compile(
    r"eligib|qualif|turnover|experience|similar|document|certificat|registration|licen[cs]e|"
    r"\bemd\b|earnest|deposit|bid security|bank guarantee|payment|advance|"
    r"deadline|last date|due date|submission|opening|udyam|\bmses?\b|micro|exempt|reserved",
    re.IGNORECASE)

PROMPT = """You are reading a government tender. Extract, in one pass:
- the bid submission deadline
- the EMD (earnest money deposit) amount
- the payment terms
- every eligibility rule, with its clause number, page number and whether it is mandatory (must_have)
- every document the bidder must submit

Tender text (the key clauses, each marked with its clause and page):
{text}"""


def estimate_tokens(text: str) -> int:
    """Rough count (about 4 characters per token for English)."""
    return math.ceil(len(text) / 4)


def select_key_clauses(clauses: list[Clause], budget_tokens: int = READER_BUDGET_TOKENS) -> list[Clause]:
    """The preamble and every key clause first, then other clauses while the budget lasts; original order kept."""
    def priority(i: int) -> int:
        if i == 0 and clauses[i].clause == "":
            return 0
        return 1 if KEY_CLAUSE.search(clauses[i].text) else 2

    chosen: dict[int, Clause] = {}
    left = budget_tokens
    for i in sorted(range(len(clauses)), key=lambda i: (priority(i), i)):
        clause, cost = clauses[i], estimate_tokens(clauses[i].text)
        if cost <= left:
            chosen[i], left = clause, left - cost
        elif priority(i) < 2 and left >= 50:   # a key clause too big to fit whole: keep its start
            chosen[i] = clause.model_copy(update={"text": clause.text[: left * 4]})
            left = 0
    return [chosen[i] for i in sorted(chosen)]


def reader_input(clauses: list[Clause]) -> str:
    return "\n\n".join(f"[clause {c.clause}, page {c.page}] {c.text}" for c in clauses)


def extract_facts(tender_text: str) -> TenderFacts:
    """One call over the selected clauses: no chunking, no loop."""
    model = llm.get_llm("reader").with_structured_output(TenderFacts)
    return model.invoke(PROMPT.format(text=tender_text))
