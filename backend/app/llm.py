"""Returns the LangChain chat model for the chosen provider. Swap providers here only."""
import os

from langchain_anthropic import ChatAnthropic

from app.config import model_for


def get_llm(agent: str) -> ChatAnthropic:
    """Chat model for one agent, using that agent's assigned model."""
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Missing setting: LLM_API_KEY")
    return ChatAnthropic(model=model_for(agent), api_key=api_key, max_retries=1)
