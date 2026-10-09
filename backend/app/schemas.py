"""Pydantic models: the fixed output shape each agent must return."""
from typing import Literal

from pydantic import BaseModel


class Clause(BaseModel):
    text: str
    clause: str  # heading number like "4.1"; "" for text before the first heading
    page: int


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


class Section(BaseModel):
    title: str
    body: str


class BidDraft(BaseModel):
    cover_letter: str
    sections: list[Section]


class ComplianceRow(BaseModel):
    rule_text: str
    must_have: bool
    covered: bool
    where: str  # which part of the draft answers the rule; "" if none


class ReviewResult(BaseModel):
    matrix: list[ComplianceRow]
    gaps: list[str]  # must-have rules the draft does not cover

    @property
    def all_covered(self) -> bool:
        return not self.gaps


class DeadlineInfo(BaseModel):
    deadline_at: str | None  # "YYYY-MM-DDTHH:MM", or null if the text gives no clear date


class Change(BaseModel):
    field: str      # deadline / emd / payment_terms / rules / required_documents
    before: str
    after: str
    summary: str    # one plain sentence for the owner


class TenderChanges(BaseModel):
    changes: list[Change]
    affects_eligibility: bool
