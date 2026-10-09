"""Pydantic models: the fixed output shape each agent must return."""
from typing import Literal

from pydantic import BaseModel


class Rule(BaseModel):
    text: str
    clause: str
    page: int
    must_have: bool


class TenderFacts(BaseModel):
    deadline: str
    emd: str
    payment_terms: str
    rules: list[Rule]
    required_documents: list[str]


class RuleVerdict(BaseModel):
    rule_text: str
    verdict: Literal["pass", "fail", "missing"]
    reason: str
    clause: str
    page: int
    must_have: bool


class EligibilityResult(BaseModel):
    verdicts: list[RuleVerdict]

    @property
    def has_must_have_fail(self) -> bool:
        """Only a clear fail on a must-have rule stops the run; 'missing' does not."""
        return any(v.must_have and v.verdict == "fail" for v in self.verdicts)


class ChecklistItem(BaseModel):
    document: str
    status: Literal["have", "need"]
    matched_file: str | None = None


class Checklist(BaseModel):
    items: list[ChecklistItem]
