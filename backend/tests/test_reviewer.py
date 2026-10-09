from app import llm, schemas
from app.agents.reviewer import review_draft
from tests.fakes import FakeLLM
from tests.samples import RULE_ISO, RULE_TURNOVER

DRAFT = schemas.BidDraft(cover_letter="Dear Sir, we apply.",
                         sections=[schemas.Section(title="Turnover", body="Our turnover is ₹1.4 crore.")])


def row(rule, covered, must_have=None):
    return schemas.ComplianceRow(rule_text=rule.text, covered=covered, where="Turnover" if covered else "",
                                 must_have=rule.must_have if must_have is None else must_have)


def run(monkeypatch, rows, rules=(RULE_TURNOVER, RULE_ISO)):
    fake = FakeLLM([schemas.ReviewResult(matrix=rows, gaps=[])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    return fake, review_draft(DRAFT, list(rules))


def test_one_call_and_all_covered(monkeypatch):
    fake, result = run(monkeypatch, [row(RULE_TURNOVER, True), row(RULE_ISO, True)])
    assert fake.agents == ["reviewer"] and len(fake.calls) == 1 and fake.calls[0][0] is schemas.ReviewResult
    assert result.all_covered and result.gaps == []
    assert [r.rule_text for r in result.matrix] == [RULE_TURNOVER.text, RULE_ISO.text]


def test_uncovered_must_have_is_gap(monkeypatch):
    _, result = run(monkeypatch, [row(RULE_TURNOVER, False), row(RULE_ISO, True)])
    assert result.gaps == [RULE_TURNOVER.text] and not result.all_covered


def test_uncovered_optional_not_gap(monkeypatch):
    _, result = run(monkeypatch, [row(RULE_TURNOVER, True), row(RULE_ISO, False)])
    assert result.all_covered


def test_dropped_must_have_is_gap(monkeypatch):
    _, result = run(monkeypatch, [row(RULE_ISO, True)])
    assert result.matrix[0] == schemas.ComplianceRow(rule_text=RULE_TURNOVER.text, must_have=True,
                                                     covered=False, where="")
    assert result.gaps == [RULE_TURNOVER.text]


def test_must_have_comes_from_rules(monkeypatch):
    _, result = run(monkeypatch, [row(RULE_TURNOVER, False, must_have=False), row(RULE_ISO, True)])
    assert result.matrix[0].must_have is True and result.gaps == [RULE_TURNOVER.text]


def test_draft_text_in_prompt(monkeypatch):
    fake, _ = run(monkeypatch, [row(RULE_TURNOVER, True), row(RULE_ISO, True)])
    prompt = str(fake.calls[0][1])
    assert "Dear Sir, we apply." in prompt and "Our turnover is ₹1.4 crore." in prompt


def test_rule_echoed_with_small_changes_still_matches(monkeypatch):
    echoed = schemas.ComplianceRow(rule_text="turnover of rs 1 crore.", must_have=True, covered=True, where="T")
    _, result = run(monkeypatch, [echoed], rules=[RULE_TURNOVER])
    assert result.matrix[0].covered and result.matrix[0].rule_text == RULE_TURNOVER.text
