"""Eligibility agent: pass/fail/missing per rule, with clause citations; can stop the run."""
from app import llm
from app.agents.matching import index_by_rule, rule_key
from app.schemas import EligibilityResult, Rule, RuleVerdict

PROMPT = """You are checking whether a small business qualifies for a government tender.
Judge every rule below against the business evidence, in one pass.
For each rule return: the rule text exactly as given, a verdict (pass / fail / missing),
a short reason, and the rule's clause and page.
Use "missing" when the evidence does not say either way; use "fail" only when the evidence
clearly shows the business does not meet the rule.

Rules:
{rules}

Business evidence:
{evidence}"""


def judge_eligibility(rules: list[Rule], evidence: list[str]) -> EligibilityResult:
    """One call for all rules; any rule the model leaves out comes back as 'missing'."""
    if not rules:
        return EligibilityResult(verdicts=[])
    rule_lines = "\n".join(
        f"{i}. {r.text} (clause {r.clause}, page {r.page}, {'must-have' if r.must_have else 'optional'})"
        for i, r in enumerate(rules, 1)
    )
    model = llm.get_llm("eligibility").with_structured_output(EligibilityResult)
    judged = model.invoke(PROMPT.format(rules=rule_lines, evidence="\n".join(f"- {e}" for e in evidence)))

    by_text = index_by_rule(judged.verdicts, lambda v: v.rule_text)
    verdicts = []
    for r in rules:
        v = by_text.get(rule_key(r.text))
        # Citation and must-have flag come from the Reader, not the model's echo of them.
        verdicts.append(RuleVerdict(
            rule_text=r.text,
            verdict=v.verdict if v else "missing",
            reason=v.reason if v else "Not judged by the model",
            clause=r.clause, page=r.page, must_have=r.must_have,
        ))
    return EligibilityResult(verdicts=verdicts)
