"""Loads settings from .env (API key, model names, storage paths)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GPT_OSS_120B = "openai/gpt-oss-120b"
QWEN = "qwen/qwen3.8-27b"

# All agents run on Groq. Each Groq model has its own tokens-per-minute limit,
# so spreading agents across models also spreads the load.
AGENT_MODELS = {
    "reader": GPT_OSS_120B,
    "eligibility": QWEN,
    "checklist": GPT_OSS_120B,
    "drafter": GPT_OSS_120B,
    "reviewer": GPT_OSS_120B,
    "tracker": GPT_OSS_120B,
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


DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"]


def cors_origins() -> list[str]:
    """Websites allowed to call the API: CORS_ORIGINS (comma-separated) or the local Vite ports."""
    value = os.environ.get("CORS_ORIGINS", "")
    return [o.strip() for o in value.split(",") if o.strip()] or DEFAULT_CORS_ORIGINS


# Vite moves to the next free port (5174, 5175...) when 5173 is busy, so any local port is allowed.
LOCAL_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1)(:\d+)?"


def cors_origin_regex() -> str | None:
    """Any localhost port, unless CORS_ORIGINS names the allowed websites exactly."""
    return None if os.environ.get("CORS_ORIGINS", "").strip() else LOCAL_ORIGIN_REGEX


def feed_path() -> Path:
    """The portal feed the Scout reads: FEED_PATH, or the sample feed in data/feed/."""
    value = os.environ.get("FEED_PATH")
    if not value:
        return BACKEND_DIR.parent / "data" / "feed" / "portal_feed.json"
    path = Path(value)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def scout_interval() -> int:
    """Seconds between automatic Scout sweeps; 0 (the default) means only when asked."""
    try:
        return max(0, int(os.environ.get("SCOUT_INTERVAL_SECONDS", "0")))
    except ValueError:
        return 0
