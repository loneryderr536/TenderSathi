# Agent Model Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each TenderSathi agent its own Claude model (Haiku 5.5 for Reader, Eligibility, Checklist; Sonnet 5.5 for Drafter, Reviewer, Tracker) and fix how many LLM calls the Haiku agents make: Reader and Eligibility do one call each, and Checklist does two (match, then double-check).

**Architecture:** `config.py` holds a per-agent model table, with an env override for each agent. `llm.py` exposes `get_llm(agent)`, which returns a `ChatAnthropic` built for that agent's model. Each Haiku agent gets one pure function that does its LLM work through `get_llm(...)`. Tests swap in a fake LLM that counts calls. Wiring these functions into LangGraph nodes, and building the Drafter, Reviewer and Tracker, is left to the agent-building plan. Those agents only need `get_llm("drafter")` and so on, which Task 1 delivers.

**Tech Stack:** Python, `langchain-anthropic` (`ChatAnthropic`), Pydantic, pytest, python-dotenv.

**Spec:** `docs/superpowers/specs/2026-10-09-tendersathi-design.md` (§6 agents, §7 stack, §12 error handling) plus the user's request:
> reader agent - haiku and it should just read and extract once, Eligibility - haiku and it should read just once, Checklist agent - haiku and it should double check, drafter, reviewer and track use sonnet 5.5

## Global Constraints

- Model IDs, exactly: Haiku = `claude-haiku-5-5`, Sonnet = `claude-sonnet-5-5`.
- Assignment: reader, eligibility, checklist → `claude-haiku-5-5`; drafter, reviewer, tracker → `claude-sonnet-5-5`.
- Each agent's model can be overridden with env var `<AGENT>_MODEL` (e.g. `READER_MODEL`). Overrides are the only way to use a non-Claude provider.
- "Once" means one LLM pass over the input: no per-chunk loop and no per-rule loop. Transport retries (`max_retries=1` on `ChatAnthropic`, per spec §12) still apply.
- Missing `LLM_API_KEY` → `get_llm` raises `RuntimeError` naming `LLM_API_KEY` (spec §12).
- All structured calls go through `.with_structured_output(<PydanticModel>)` (spec §6).
- Tests run from `backend/`: `cd backend && pytest`.

## Review Focus

1. **Eligibility LLM leaves out a rule:** the owner still sees every rule. Any rule left out is added as `missing` with reason `"Not judged by the model"`. (Task 3)
2. **Checklist says "have" but names a file the business doesn't hold:** a fake match must not reach the owner. The code downgrades the item to `need` after the double-check. (Task 4)
3. **A tender with no rules, or no required documents:** no LLM call is made and the result is empty. (Tasks 3, 4)
4. **The double-check pass leaves out an item:** the pass-1 item is kept, so no required document disappears. (Task 4)
5. **A rule marked `missing` on a must-have:** this must not stop the run. Only `fail` on a must-have sets `has_must_have_fail` (spec: "clearly fails"). (Task 3)

---

### Task 1: Per-agent model config and `get_llm`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/llm.py`
- Modify: `.env.example`
- Modify: `docs/superpowers/specs/2026-10-09-tendersathi-design.md` (§6 agent table: add a **Model** column)
- Test: `backend/tests/test_llm.py`

**Interfaces:**
- Produces:
  - `config.AGENT_MODELS: dict[str, str]`: the default table from Global Constraints.
  - `config.model_for(agent: str) -> str`: returns `os.environ[f"{agent.upper()}_MODEL"]` if set, else `AGENT_MODELS[agent]`. Raises `ValueError(f"Unknown agent: {agent}")` for names not in the table.
  - `llm.get_llm(agent: str) -> ChatAnthropic`: `ChatAnthropic(model=model_for(agent), api_key=<LLM_API_KEY>, max_retries=1)`. Reads env at call time, not import time.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_llm.py`

```python
import pytest
from app import config, llm

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"

@pytest.mark.parametrize("agent,model", [
    ("reader", HAIKU), ("eligibility", HAIKU), ("checklist", HAIKU),
    ("drafter", SONNET), ("reviewer", SONNET), ("tracker", SONNET),
])
def test_default_model_per_agent(agent, model, monkeypatch):
    monkeypatch.delenv(f"{agent.upper()}_MODEL", raising=False)
    assert config.model_for(agent) == model

def test_env_override(monkeypatch):
    monkeypatch.setenv("READER_MODEL", "claude-opus-5-5")
    assert config.model_for("reader") == "claude-opus-5-5"

def test_unknown_agent():
    with pytest.raises(ValueError, match="Unknown agent: writer"):
        config.model_for("writer")

def test_get_llm_uses_agent_model(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("DRAFTER_MODEL", raising=False)
    assert llm.get_llm("drafter").model == SONNET

def test_get_llm_missing_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        llm.get_llm("reader")
```

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `cd backend && pytest tests/test_llm.py -v`
Expected: FAIL with `AttributeError: module 'app.config' has no attribute 'model_for'`

- [ ] **Step 3: Implement `AGENT_MODELS` and `model_for` in `config.py`, and `get_llm` in `llm.py`**

Call `load_dotenv()` at import time in `config.py`, and keep the existing module docstrings. In `.env.example`, replace `LLM_MODEL=your-model-name` with six commented-out override lines (`# READER_MODEL=claude-haiku-5-5` … `# TRACKER_MODEL=claude-sonnet-5-5`), plus one comment saying OpenAI users must set all six. In the spec's §6 table, add a Model column: Haiku 5.5 / Haiku 5.5 / Haiku 5.5 / Sonnet 5.5 / Sonnet 5.5 / Sonnet 5.5.

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `cd backend && pytest tests/test_llm.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/llm.py backend/tests/test_llm.py .env.example docs/superpowers/specs/2026-10-09-tendersathi-design.md
git commit -m "feat: per-agent model assignment (Haiku 5.5 / Sonnet 5.5)"
```

---

### Task 2: Reader: one extraction call

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/agents/reader.py`
- Create: `backend/tests/fakes.py`
- Test: `backend/tests/test_reader.py`

**Interfaces:**
- Consumes: `llm.get_llm(agent)` (Task 1). Agents must call it as `llm.get_llm(...)` (module attribute) so tests can monkeypatch it.
- Produces:
  - `schemas.Rule(text: str, clause: str, page: int, must_have: bool)`
  - `schemas.TenderFacts(deadline: str, emd: str, payment_terms: str, rules: list[Rule], required_documents: list[str])`
  - `reader.extract_facts(tender_text: str) -> TenderFacts`
  - `tests/fakes.FakeLLM(outputs: list)`: has `.calls: list[tuple[type, object]]` (schema, prompt) and `.agents: list[str]` (the agent names passed to the patched `get_llm`). Tasks 3–4 use it.

- [ ] **Step 1: Write the shared fake and the failing test**

`backend/tests/fakes.py`:

```python
class FakeLLM:
    def __init__(self, outputs):
        self.outputs, self.calls, self.agents = list(outputs), [], []

    def factory(self, agent):          # monkeypatch target for app.llm.get_llm
        self.agents.append(agent)
        return self

    def with_structured_output(self, schema):
        fake = self
        class _Runnable:
            def invoke(self, prompt):
                fake.calls.append((schema, prompt))
                return fake.outputs.pop(0)
        return _Runnable()
```

`backend/tests/test_reader.py`:

```python
from app import llm, schemas
from app.agents import reader
from tests.fakes import FakeLLM

FACTS = schemas.TenderFacts(deadline="2026-10-30", emd="₹50,000", payment_terms="30 days after delivery",
    rules=[schemas.Rule(text="Turnover ≥ ₹1 crore", clause="4.1", page=7, must_have=True)],
    required_documents=["GST certificate"])

def test_reader_extracts_once_with_haiku(monkeypatch):
    fake = FakeLLM([FACTS])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    long_text = "Clause text. " * 20_000
    assert reader.extract_facts(long_text) == FACTS
    assert fake.agents == ["reader"]
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is schemas.TenderFacts
```

- [ ] **Step 2: Run the test to make sure it fails**

Run: `cd backend && pytest tests/test_reader.py -v`
Expected: FAIL with `AttributeError: module 'app.schemas' has no attribute 'TenderFacts'`

- [ ] **Step 3: Add the schemas and implement `extract_facts`**

Make one `get_llm("reader").with_structured_output(TenderFacts).invoke(prompt)` call. The prompt holds a short instruction (extract deadline, EMD, payment terms, every eligibility rule with its clause, page and must-have flag, and the required documents) followed by the full text. Don't chunk or loop.

- [ ] **Step 4: Run the test to make sure it passes**

Run: `cd backend && pytest tests/test_reader.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/agents/reader.py backend/tests/fakes.py backend/tests/test_reader.py
git commit -m "feat: reader extracts tender facts in a single Haiku call"
```

---

### Task 3: Eligibility: judge all rules in one call

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/agents/eligibility.py`
- Test: `backend/tests/test_eligibility.py`

**Interfaces:**
- Consumes: `schemas.Rule` (Task 2), `llm.get_llm`, `tests/fakes.FakeLLM`.
- Produces:
  - `schemas.RuleVerdict(rule_text: str, verdict: Literal["pass","fail","missing"], reason: str, clause: str, page: int, must_have: bool)`
  - `schemas.EligibilityResult(verdicts: list[RuleVerdict])`, with property `has_must_have_fail -> bool`: True only if some verdict has `must_have and verdict == "fail"`.
  - `eligibility.judge_eligibility(rules: list[Rule], evidence: list[str]) -> EligibilityResult`

- [ ] **Step 1: Write the failing tests**

```python
def test_one_call_for_all_rules(monkeypatch):
    # 5 rules in; the fake returns verdicts for all 5
    ...
    assert fake.agents == ["eligibility"]
    assert len(fake.calls) == 1
    prompt = str(fake.calls[0][1])
    assert all(r.text in prompt for r in rules) and "Udyam registered" in prompt

def test_dropped_rule_becomes_missing(monkeypatch):
    # 2 rules in; the fake returns a verdict only for rules[0]
    ...
    assert [v.rule_text for v in result.verdicts] == [rules[0].text, rules[1].text]
    assert result.verdicts[1].verdict == "missing"
    assert result.verdicts[1].reason == "Not judged by the model"
    assert (result.verdicts[1].clause, result.verdicts[1].page) == (rules[1].clause, rules[1].page)

def test_no_rules_no_call(monkeypatch):
    assert judge_eligibility([], ["x"]).verdicts == [] and fake.calls == []

def test_must_have_fail_only_on_fail():
    # must_have + "missing" → False; must_have + "fail" → True; optional + "fail" → False
```

Write the `...` setup with `FakeLLM` and `monkeypatch.setattr(llm, "get_llm", fake.factory)`, as in Task 2.

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `cd backend && pytest tests/test_eligibility.py -v`
Expected: FAIL with `AttributeError: ... 'EligibilityResult'`

- [ ] **Step 3: Implement `judge_eligibility`**

Make one `with_structured_output(EligibilityResult)` call. The prompt lists every rule (numbered, with clause and page) and every evidence line. After the call, return verdicts in the order of the input rules, matched by `rule_text`. Add any unmatched rule as `missing` with the reason above. Return early with no call when `rules` is empty.

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `cd backend && pytest tests/test_eligibility.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/agents/eligibility.py backend/tests/test_eligibility.py
git commit -m "feat: eligibility judges all rules in a single Haiku call"
```

---

### Task 4: Checklist: match, then double-check

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/agents/checklist.py`
- Test: `backend/tests/test_checklist.py`

**Interfaces:**
- Consumes: `llm.get_llm`, `tests/fakes.FakeLLM`.
- Produces:
  - `schemas.ChecklistItem(document: str, status: Literal["have","need"], matched_file: str | None = None)`
  - `schemas.Checklist(items: list[ChecklistItem])`
  - `checklist.build_checklist(required_docs: list[str], stored_docs: list[str]) -> Checklist`

- [ ] **Step 1: Write the failing tests**

```python
def test_two_passes_second_is_verification(monkeypatch):
    # The fake returns pass1 (GST → have "gst.pdf"; PAN → have "pan.pdf"),
    # then pass2 (GST → have "gst.pdf"; PAN → need: the verifier corrected it)
    ...
    assert fake.agents == ["checklist", "checklist"]
    assert len(fake.calls) == 2
    assert "gst.pdf" in str(fake.calls[1][1])        # pass 1 output is shown to the verifier
    assert [i.status for i in result.items] == ["have", "need"]

def test_unknown_file_downgraded(monkeypatch):
    # pass2 says have "iso.pdf", but stored_docs = ["gst.pdf"]
    assert result.items[0].status == "need" and result.items[0].matched_file is None

def test_verifier_drops_item_keeps_pass1(monkeypatch):
    # pass2 leaves out "PAN card"; the result still lists it with its pass-1 status

def test_no_required_docs_no_call(monkeypatch):
    assert build_checklist([], ["gst.pdf"]).items == [] and fake.calls == []
```

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `cd backend && pytest tests/test_checklist.py -v`
Expected: FAIL with `AttributeError: ... 'Checklist'`

- [ ] **Step 3: Implement `build_checklist`**

Pass 1 matches each required doc to a stored file. Pass 2 sends the required docs, the stored docs and the pass-1 checklist to a verifier prompt ("check each match; correct any that are wrong or unsupported") and returns a `Checklist`. Merge the passes in the order of `required_docs`: use the pass-2 item, or the pass-1 item if pass 2 left it out. Then set any `have` whose `matched_file` is not in `stored_docs` to `need` with `matched_file=None`. Return early with no calls when `required_docs` is empty.

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `cd backend && pytest -v`
Expected: all tests across Tasks 1–4 pass (19)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/agents/checklist.py backend/tests/test_checklist.py
git commit -m "feat: checklist double-checks matches with a second Haiku pass"
```
