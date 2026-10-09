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
