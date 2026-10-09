"""Tracker agent: turns the deadline text into a date, and spots what a tender change (corrigendum) altered."""
from datetime import date, datetime

from app import llm
from app.schemas import DeadlineInfo, TenderChanges, TenderFacts

DEADLINE_PROMPT = """Today is {today}. A government tender gives this bid submission deadline:

"{text}"

Return it as deadline_at in the form YYYY-MM-DDTHH:MM (24-hour clock; use 17:00 if no time is given).
If the text does not give a clear date, return null."""

COMPARE_PROMPT = """A government tender has been changed (a corrigendum was issued). Compare the old and new
versions below and list every change that matters to a bidder: deadline, EMD, payment terms, eligibility
rules (added, removed or altered) and required documents. Ignore rewording that does not change meaning.
For each change give the field, the old value, the new value, and one plain sentence a small business
owner understands. Set affects_eligibility to true if any eligibility rule was added, removed or altered.

Old version:
{old}

New version:
{new}"""


def parse_deadline(deadline_text: str, today: date) -> datetime | None:
    """One call; None when there is no text or the answer is not a valid date."""
    if not deadline_text or not deadline_text.strip():
        return None
    model = llm.get_llm("tracker").with_structured_output(DeadlineInfo)
    answer = model.invoke(DEADLINE_PROMPT.format(today=today.isoformat(), text=deadline_text.strip()))
    try:
        return datetime.fromisoformat(answer.deadline_at) if answer.deadline_at else None
    except ValueError:
        return None


def _describe(facts: TenderFacts) -> str:
    rules = "\n".join(f"  - {r.text} (clause {r.clause}{', mandatory' if r.must_have else ''})" for r in facts.rules)
    docs = "\n".join(f"  - {d}" for d in facts.required_documents)
    return (f"Deadline: {facts.deadline}\nEMD: {facts.emd}\nPayment terms: {facts.payment_terms}\n"
            f"Eligibility rules:\n{rules or '  (none)'}\nRequired documents:\n{docs or '  (none)'}")


def compare_tenders(old: TenderFacts, new: TenderFacts) -> TenderChanges:
    """One call; identical versions need no call."""
    if old == new:
        return TenderChanges(changes=[], affects_eligibility=False)
    model = llm.get_llm("tracker").with_structured_output(TenderChanges)
    return model.invoke(COMPARE_PROMPT.format(old=_describe(old), new=_describe(new)))
