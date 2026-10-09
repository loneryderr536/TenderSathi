"""Match the rules a model echoes back to the original rules, tolerating small changes."""
import re


# A clause number the model may put in front of the rule: "4.1 ", "4.1. ", "Clause 4.1: ", "2) ".
# A bare "3 years ..." is part of the rule, so a plain number needs "clause" or a separator.
LEADING_CLAUSE = re.compile(r"^\s*(?:clause\s+\d+(?:\.\d+)*|\d+(?:\.\d+)+|\d+[.):])[.):]?\s+", re.IGNORECASE)


# The "(clause 4.1)" / "(clause 4.1, page 7, must-have)" our prompts put after each rule; models copy it back.
CLAUSE_SUFFIX = re.compile(r"\s*\(clause [^)]*\)\s*$", re.IGNORECASE)


def rule_key(text: str) -> str:
    """Lowercase, clause number or "(clause ...)" suffix, punctuation and extra spaces removed: "4.1 Turnover" matches "turnover"."""
    text = CLAUSE_SUFFIX.sub("", LEADING_CLAUSE.sub("", text))
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def index_by_rule(items, text_of) -> dict:
    """Map rule_key(text) -> item, keeping the first item for each key."""
    out = {}
    for item in items:
        out.setdefault(rule_key(text_of(item)), item)
    return out
