"""Sample agent outputs shared by tests."""
from app import schemas

RULE_TURNOVER = schemas.Rule(text="Turnover of Rs 1 crore", clause="4.1", page=1, must_have=True)
RULE_ISO = schemas.Rule(text="ISO 9001 certificate", clause="4.2", page=2, must_have=False)

FACTS = schemas.TenderFacts(
    deadline="2026-10-30", emd="₹50,000", payment_terms="30 days after delivery",
    rules=[RULE_TURNOVER, RULE_ISO], required_documents=["GST certificate"],
)


def verdicts(verdict="pass", rules=(RULE_TURNOVER, RULE_ISO)):
    return schemas.EligibilityResult(verdicts=[
        schemas.RuleVerdict(rule_text=r.text, verdict=verdict, reason="per profile",
                            clause=r.clause, page=r.page, must_have=r.must_have)
        for r in rules
    ])


CHECKLIST = schemas.Checklist(items=[
    schemas.ChecklistItem(document="GST certificate", status="have", matched_file="gst.pdf")])
