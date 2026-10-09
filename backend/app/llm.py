"""Returns the Groq chat model for each agent."""
import os

import groq
from langchain_core.exceptions import OutputParserException
from langchain_groq import ChatGroq
from pydantic import ValidationError

from app.config import model_for


class _GroqChat(ChatGroq):
    """Structured output via Groq's strict JSON-schema mode: the server enforces the shape.

    Tool calling sometimes answered in prose, and non-strict JSON sometimes came back malformed.
    """

    def with_structured_output(self, schema, **kwargs):
        kwargs.setdefault("method", "json_schema")
        kwargs.setdefault("strict", True)
        # Long answers (the drafted bid) occasionally come back in the wrong shape and Groq rejects them
        # (400 json_validate_failed). Ask again, up to 3 attempts; rate limits and timeouts are handled elsewhere.
        return super().with_structured_output(schema, **kwargs).with_retry(
            retry_if_exception_type=(OutputParserException, ValidationError, groq.BadRequestError),
            stop_after_attempt=3, wait_exponential_jitter=False)


def get_llm(agent: str) -> ChatGroq:
    """Chat model for one agent, using that agent's assigned model."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing setting: GROQ_API_KEY")
    # max_retries also covers Groq's 429 (tokens-per-minute) responses; timeout stops a hung call stalling a run.
    return _GroqChat(model=model_for(agent), api_key=api_key, temperature=0, max_retries=3, timeout=60)
