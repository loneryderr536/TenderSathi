"""Concessions agent: small-business benefits the tender offers this business (EMD exemption, relaxed turnover...)."""
from app import llm
from app.schemas import Clause, Concessions

# What the vector memory is asked for: the clauses most likely to grant small-business benefits.
SEARCH_QUERY = ("concession exemption relaxation waiver for micro and small enterprises MSE Udyam "
                "startup women-led local suppliers preference")

PROMPT = """A small business is considering a government tender. Below are clauses from the tender and the business profile.
List every concession the tender gives that THIS business can use, for example exemption from EMD,
relaxed turnover or experience rules, price preference, or waived tender fees.
Only list a concession the clauses state plainly and the profile qualifies for; if the profile does
not show the business qualifies, leave it out. Return an empty list when there are none.
For each give the benefit in one plain sentence, and the clause number and page it came from.

Business profile:
{profile}

Tender clauses:
{clauses}"""


def find_concessions(clauses: list[Clause], profile: list[str]) -> Concessions:
    """One call over the clauses the memory search returned; no clauses, no call."""
    if not clauses:
        return Concessions(items=[])
    prompt = PROMPT.format(
        profile="\n".join(f"- {line}" for line in profile),
        clauses="\n\n".join(f"[clause {c.clause}, page {c.page}] {c.text}" for c in clauses))
    return llm.get_llm("checklist").with_structured_output(Concessions).invoke(prompt)
