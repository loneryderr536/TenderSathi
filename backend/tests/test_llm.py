import pytest
from langchain_groq import ChatGroq

from app import config, llm

GPT_OSS, QWEN = "openai/gpt-oss-120b", "qwen/qwen3.8-27b"


@pytest.mark.parametrize("agent,model", [
    ("reader", GPT_OSS), ("eligibility", QWEN), ("checklist", GPT_OSS),
    ("drafter", GPT_OSS), ("reviewer", GPT_OSS), ("tracker", GPT_OSS),
])
def test_default_model_per_agent(agent, model, monkeypatch):
    monkeypatch.delenv(f"{agent.upper()}_MODEL", raising=False)
    assert config.model_for(agent) == model


def test_env_override(monkeypatch):
    monkeypatch.setenv("READER_MODEL", "openai/gpt-oss-20b")
    assert config.model_for("reader") == "openai/gpt-oss-20b"


def test_unknown_agent():
    with pytest.raises(ValueError, match="Unknown agent: writer"):
        config.model_for("writer")


def test_get_llm_is_groq_with_agent_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("ELIGIBILITY_MODEL", raising=False)
    model = llm.get_llm("eligibility")
    assert isinstance(model, ChatGroq) and model.model_name == QWEN
    assert model.request_timeout == 60


def test_get_llm_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.get_llm("reader")


def test_structured_output_uses_json_schema(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    seen = {}

    def record(self, schema, **kwargs):
        seen.update(kwargs)
        return "runnable"
    monkeypatch.setattr(ChatGroq, "with_structured_output", record)
    from langchain_core.runnables import RunnableLambda
    seen_runnable = RunnableLambda(lambda x: x)
    monkeypatch.setattr(ChatGroq, "with_structured_output", lambda self, schema, **kw: (seen.update(kw), seen_runnable)[1])
    from app.schemas import TenderFacts
    assert llm.get_llm("reader").with_structured_output(TenderFacts).invoke("ok") == "ok"
    assert seen["method"] == "json_schema" and seen["strict"] is True


def _fail_then_succeed(monkeypatch, errors):
    """Patch ChatGroq so the structured runnable raises `errors` in turn, then returns "draft"."""
    from langchain_core.runnables import RunnableLambda
    attempts = []

    def flaky(_):
        attempts.append(1)
        if len(attempts) <= len(errors):
            raise errors[len(attempts) - 1]
        return "draft"
    monkeypatch.setattr(ChatGroq, "with_structured_output", lambda self, schema, **kw: RunnableLambda(flaky))
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return attempts


def test_wrong_shape_answers_are_retried(monkeypatch):
    from langchain_core.exceptions import OutputParserException
    from app.schemas import BidDraft
    attempts = _fail_then_succeed(monkeypatch, [OutputParserException("list, not object"),
                                                OutputParserException("section is a string")])
    assert llm.get_llm("drafter").with_structured_output(BidDraft).invoke("write") == "draft"
    assert len(attempts) == 3


def test_other_errors_are_not_retried_here(monkeypatch):
    from app.schemas import BidDraft
    attempts = _fail_then_succeed(monkeypatch, [TimeoutError("slow")])
    with pytest.raises(TimeoutError):
        llm.get_llm("drafter").with_structured_output(BidDraft).invoke("write")
    assert len(attempts) == 1
