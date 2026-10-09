"""Match the rules a model echoes back to the original rules, tolerating small changes."""
import re


def rule_key(text: str) -> str:
    """Lowercase, punctuation and extra spaces removed: "  Rule 1. " and "rule 1" match."""
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def index_by_rule(items, text_of) -> dict:
    """Map rule_key(text) -> item, keeping the first item for each key."""
    out = {}
    for item in items:
        out.setdefault(rule_key(text_of(item)), item)
    return out
