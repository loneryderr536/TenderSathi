"""Gap planner: for every document or rule the business is missing, how to close the gap before the deadline."""
from datetime import date

from pydantic import BaseModel

from app import llm


class GapStep(BaseModel):
    gap: str
    how: str              # the concrete steps, in plain words
    where: str            # office or website to go to
    typical_days: int
    fits_deadline: bool


class GapPlan(BaseModel):
    steps: list[GapStep]


PROMPT = """Today is {today}. A small business in India wants to bid for a government tender due {deadline}.
It is missing the items below. For each one, explain in plain words how a small business obtains it
(the office or website to go to, and the steps), how many days it typically takes, and whether that fits
before the deadline. If an item cannot be obtained in time, say what the owner can do instead
(for example, a self-declaration where tenders allow one, or skipping this tender).

Business:
{business}

Missing items:
{gaps}"""


def plan_gaps(gaps: list[str], deadline: str, business: list[str], today: date) -> GapPlan:
    if not gaps:
        return GapPlan(steps=[])
    return llm.get_llm("checklist").with_structured_output(GapPlan).invoke(PROMPT.format(
        today=today.isoformat(), deadline=deadline or "soon",
        business="\n".join(f"- {b}" for b in business), gaps="\n".join(f"- {g}" for g in gaps)))
