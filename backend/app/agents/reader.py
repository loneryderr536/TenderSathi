"""Reader agent: extracts deadline, deposit, eligibility rules and required documents."""
from app import llm
from app.schemas import TenderFacts

PROMPT = """You are reading a government tender. Extract, in one pass:
- the bid submission deadline
- the EMD (earnest money deposit) amount
- the payment terms
- every eligibility rule, with its clause number, page number and whether it is mandatory (must_have)
- every document the bidder must submit

Tender text:
{text}"""


def extract_facts(tender_text: str) -> TenderFacts:
    """One Haiku call over the whole tender text: no chunking, no loop."""
    model = llm.get_llm("reader").with_structured_output(TenderFacts)
    return model.invoke(PROMPT.format(text=tender_text))
