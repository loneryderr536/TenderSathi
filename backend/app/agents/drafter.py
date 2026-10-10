"""Drafter agent: writes the cover letter and technical bid from business memory."""
from app import llm
from app.schemas import BidDraft, Section, TenderFacts

PRICE_PLACEHOLDER = "[PRICE: to be filled by owner]"

PROMPT = """You are writing a bid for a government tender on behalf of a small business.
Write a formal cover letter and technical sections that answer every eligibility rule below.
Use only the business details given: never invent certificates, numbers, orders or experience.
If the business details do not cover a rule, say so plainly instead of making something up.
Never state a price; write {price} wherever a price belongs.

Tender:
- Deadline: {deadline}
- EMD: {emd}
- Payment terms: {payment_terms}

Eligibility rules:
{rules}

Required documents (mention that they are enclosed or will be enclosed):
{documents}

Business details:
{business}
{notes}"""


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines) or "- (none)"


def draft_bid(facts: TenderFacts, business: list[str], notes: list[str]) -> BidDraft:
    """One call; reviewer notes (if any) are passed in to be fixed."""
    note_block = f"\nReviewer notes - fix every one of these:\n{_bullets(notes)}" if notes else ""
    prompt = PROMPT.format(
        price=PRICE_PLACEHOLDER, deadline=facts.deadline, emd=facts.emd, payment_terms=facts.payment_terms,
        rules=_bullets([f"{r.text} (clause {r.clause}, page {r.page}{', mandatory' if r.must_have else ''})"
                        for r in facts.rules]),
        documents=_bullets(facts.required_documents), business=_bullets(business), notes=note_block,
    )
    draft = llm.get_llm("drafter").with_structured_output(BidDraft).invoke(prompt)
    return ensure_price_placeholder(draft)


def ensure_price_placeholder(draft: BidDraft) -> BidDraft:
    """The price is the owner's to set: if the model left the marker out, add a Price section with it."""
    text = draft.cover_letter + "".join(s.body for s in draft.sections)
    if PRICE_PLACEHOLDER in text:
        return draft
    price = Section(title="Price", body=f"Quoted price: {PRICE_PLACEHOLDER}")
    return draft.model_copy(update={"sections": [*draft.sections, price]})
