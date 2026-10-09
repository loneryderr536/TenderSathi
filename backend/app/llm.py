"""Returns the Groq chat model for each agent."""
import os

from langchain_groq import ChatGroq

from app.config import model_for


class _GroqChat(ChatGroq):
    """Structured output via Groq's strict JSON-schema mode: the server enforces the shape.

    Tool calling sometimes answered in prose, and non-strict JSON sometimes came back malformed.
    """

    def with_structured_output(self, schema, **kwargs):
        kwargs.setdefault("method", "json_schema")
        kwargs.setdefault("strict", True)
        return super().with_structured_output(schema, **kwargs)


def get_llm(agent: str) -> ChatGroq:
    """Chat model for one agent, using that agent's assigned model."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing setting: GROQ_API_KEY")
    # max_retries also covers Groq's 429 (tokens-per-minute) responses; timeout stops a hung call stalling a run.
    return _GroqChat(model=model_for(agent), api_key=api_key, temperature=0, max_retries=3, timeout=60)
