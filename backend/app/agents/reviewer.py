"""Reviewer agent: builds the compliance matrix; can send the draft back (max 2 rounds)."""
from app import llm
from app.agents.matching import index_by_rule, rule_key
from app.schemas import BidDraft, ComplianceRow, ReviewResult, Rule

PROMPT = """You are checking a government tender bid before the business owner sees it.
For every rule below, decide whether the draft clearly answers it, and name the part of the draft
that does (or leave "where" empty). Return one row per rule, using the rule text exactly as given.

Rules:
{rules}

Draft cover letter:
{cover_letter}

Draft sections:
{sections}"""


def review_draft(draft: BidDraft, rules: list[Rule]) -> ReviewResult:
    """One call; gaps are computed here from the must-have rules, not taken from the model."""
    prompt = PROMPT.format(
        rules="\n".join(f"- {r.text} (clause {r.clause})" for r in rules),
        cover_letter=draft.cover_letter,
        sections="\n\n".join(f"## {s.title}\n{s.body}" for s in draft.sections),
    )
    judged = llm.get_llm("reviewer").with_structured_output(ReviewResult).invoke(prompt)

    by_text = index_by_rule(judged.matrix, lambda row: row.rule_text)
    matrix = []
    for r in rules:
        row = by_text.get(rule_key(r.text))
        matrix.append(ComplianceRow(rule_text=r.text, must_have=r.must_have,
                                    covered=row.covered if row else False,
                                    where=row.where if row else ""))
    gaps = [row.rule_text for row in matrix if row.must_have and not row.covered]
    return ReviewResult(matrix=matrix, gaps=gaps)
