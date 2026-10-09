"""Loads settings from .env (API key, model names, storage paths)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"

# Haiku for the read/extract/check agents, Sonnet for writing and reviewing.
AGENT_MODELS = {
    "reader": HAIKU,
    "eligibility": HAIKU,
    "checklist": HAIKU,
    "drafter": SONNET,
    "reviewer": SONNET,
    "tracker": SONNET,
}


def model_for(agent: str) -> str:
    """Model name for an agent; <AGENT>_MODEL in the environment overrides the default."""
    if agent not in AGENT_MODELS:
        raise ValueError(f"Unknown agent: {agent}")
    return os.environ.get(f"{agent.upper()}_MODEL") or AGENT_MODELS[agent]


BACKEND_DIR = Path(__file__).resolve().parents[1]


def storage_dir() -> Path:
    """STORAGE_DIR from .env (relative paths are relative to backend/), created if missing."""
    path = Path(os.environ.get("STORAGE_DIR") or "../storage")
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
