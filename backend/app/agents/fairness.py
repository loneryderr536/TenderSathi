"""Fairness agent (government side): checks a tender against small-business procurement policy before it goes out.

Retrieval-augmented: for each policy check the vector memory pulls the tender clauses most related to it, and
the model judges each check only on those clauses, citing clause and page.
"""
from typing import Literal

from pydantic import BaseModel

from app import llm
from app.schemas import Clause

# Each check: what to look for, the memory query that finds the relevant clauses, and the policy behind it.
CHECKS = [
    {"id": "emd_exemption", "title": "EMD exemption for registered micro and small enterprises",
     "query": "earnest money deposit EMD exemption micro small enterprises Udyam bid security",
     "policy": "Public Procurement Policy for Micro and Small Enterprises Order, 2012: registered MSEs are exempt "
               "from paying EMD."},
    {"id": "tender_fee", "title": "Tender documents free for registered MSEs",
     "query": "tender fee cost of tender document non-refundable payable by all bidders",
     "policy": "Public Procurement Policy for MSEs Order, 2012: tender sets are to be issued free of cost to "
               "registered MSEs."},
    {"id": "turnover", "title": "Turnover demand in proportion to the order value",
     "query": "average annual turnover financial years estimated value of the order",
     "policy": "General Financial Rules 2017 and the Manual for Procurement of Goods: eligibility criteria should be "
               "reasonable and in proportion to the value of the order, so as not to restrict competition."},
    {"id": "experience", "title": "Experience rules that do not shut out small, new or local suppliers",
     "query": "experience years orders supplied similar work government departments startups relaxation",
     "policy": "Department of Expenditure guidance: prior experience and prior turnover requirements may be relaxed "
               "for startups and MSEs; experience should not be limited to one class of buyer without reason."},
    {"id": "brand", "title": "Specification open to any brand",
     "query": "make brand model specification equivalent only products",
     "policy": "General Financial Rules 2017: specifications should meet the need without naming a brand or "
               "favouring a particular supplier."},
    {"id": "timeline", "title": "Enough time to bid and to deliver, and fair payment terms",
     "query": "last date bid submission published delivery within days payment subject to availability of funds",
     "policy": "General Financial Rules 2017: bidders should get adequate time to prepare bids; MSMED Act 2006: "
               "MSE suppliers are to be paid within 45 days of acceptance."},
]


class Finding(BaseModel):
    check_id: str
    status: Literal["ok", "concern", "not_found"]   # not_found: the tender says nothing about it
    clause: str
    page: int
    explanation: str
    suggestion: str   # "" when status is ok


class FairnessFindings(BaseModel):
    findings: list[Finding]


PROMPT = """You are helping a government procurement officer make a tender fair to small businesses
(micro and small enterprises, startups, women-led and local firms) before it is published.
For each policy check below you are given the tender clauses most related to it.
Judge each check ONLY on those clauses. For each check return:
- check_id exactly as given
- status: "ok" if the tender meets the policy, "concern" if a clause works against small businesses,
  "not_found" if the clauses say nothing about it
- the clause number and page your judgement rests on (use "" and 0 when not_found)
- one or two plain sentences explaining why
- for a concern, a concrete rewrite or fix the officer can paste into the tender; otherwise ""

{checks}"""


def _check_block(check: dict, clauses: list[Clause]) -> str:
    evidence = "\n".join(f"  [clause {c.clause}, page {c.page}] {c.text}" for c in clauses) or "  (no clauses found)"
    return f"Check {check['id']}: {check['title']}\nPolicy: {check['policy']}\nTender clauses:\n{evidence}"


def check_fairness(search) -> dict:
    """search(query) -> clauses from the vector memory. Returns the report the dashboard shows."""
    blocks = [_check_block(c, search(c["query"])) for c in CHECKS]
    judged = llm.get_llm("reviewer").with_structured_output(FairnessFindings).invoke(
        PROMPT.format(checks="\n\n".join(blocks)))
    by_id = {f.check_id: f for f in judged.findings}
    findings = []
    for check in CHECKS:
        f = by_id.get(check["id"]) or Finding(check_id=check["id"], status="not_found", clause="", page=0,
                                               explanation="Not judged by the model", suggestion="")
        findings.append({**f.model_dump(), "title": check["title"], "policy": check["policy"]})
    concerns = sum(f["status"] == "concern" for f in findings)
    score = round(100 * (len(findings) - concerns) / len(findings))
    return {"score": score, "concerns": concerns, "findings": findings}
