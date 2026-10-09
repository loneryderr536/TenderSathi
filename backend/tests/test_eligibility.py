from app import llm, schemas
from app.agents.eligibility import judge_eligibility
from tests.fakes import FakeLLM


def rule(i, must_have=True):
    return schemas.Rule(text=f"Rule {i}", clause=f"4.{i}", page=i, must_have=must_have)


def verdict(r, v="pass"):
    return schemas.RuleVerdict(rule_text=r.text, verdict=v, reason="ok",
                               clause=r.clause, page=r.page, must_have=r.must_have)


def test_one_call_for_all_rules(monkeypatch):
    rules = [rule(i) for i in range(1, 6)]
    fake = FakeLLM([schemas.EligibilityResult(verdicts=[verdict(r) for r in rules])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    result = judge_eligibility(rules, ["Udyam registered", "Turnover ₹2 crore"])
    assert fake.agents == ["eligibility"]
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is schemas.EligibilityResult
    prompt = str(fake.calls[0][1])
    assert all(r.text in prompt for r in rules) and "Udyam registered" in prompt
    assert [v.verdict for v in result.verdicts] == ["pass"] * 5


def test_dropped_rule_becomes_missing(monkeypatch):
    rules = [rule(1), rule(2)]
    fake = FakeLLM([schemas.EligibilityResult(verdicts=[verdict(rules[0])])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    result = judge_eligibility(rules, ["x"])
    assert [v.rule_text for v in result.verdicts] == [rules[0].text, rules[1].text]
    assert result.verdicts[1].verdict == "missing"
    assert result.verdicts[1].reason == "Not judged by the model"
    assert (result.verdicts[1].clause, result.verdicts[1].page) == (rules[1].clause, rules[1].page)


def test_no_rules_no_call(monkeypatch):
    fake = FakeLLM([])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    assert judge_eligibility([], ["x"]).verdicts == []
    assert fake.calls == []


def test_must_have_fail_only_on_fail():
    def result(v, must_have):
        return schemas.EligibilityResult(verdicts=[verdict(rule(1, must_have), v)])
    assert result("missing", True).has_must_have_fail is False
    assert result("fail", True).has_must_have_fail is True
    assert result("fail", False).has_must_have_fail is False


def test_citation_and_must_have_come_from_reader(monkeypatch):
    r = rule(1, must_have=True)
    wrong = schemas.RuleVerdict(rule_text=r.text, verdict="fail", reason="low turnover",
                                clause="9.9", page=99, must_have=False)
    fake = FakeLLM([schemas.EligibilityResult(verdicts=[wrong])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    result = judge_eligibility([r], ["x"])
    v = result.verdicts[0]
    assert (v.verdict, v.reason) == ("fail", "low turnover")
    assert (v.clause, v.page, v.must_have) == ("4.1", 1, True)
    assert result.has_must_have_fail is True


def test_rule_echoed_with_small_changes_still_matches(monkeypatch):
    r = rule(1)
    echoed = schemas.RuleVerdict(rule_text="  rule 1. ", verdict="fail", reason="no",
                                 clause=r.clause, page=r.page, must_have=True)
    fake = FakeLLM([schemas.EligibilityResult(verdicts=[echoed])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    v = judge_eligibility([r], ["x"]).verdicts[0]
    assert (v.rule_text, v.verdict) == ("Rule 1", "fail")
