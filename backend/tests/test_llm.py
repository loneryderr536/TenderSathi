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
    from app.schemas import TenderFacts
    assert llm.get_llm("reader").with_structured_output(TenderFacts) == "runnable"
    assert seen["method"] == "json_schema" and seen["strict"] is True
