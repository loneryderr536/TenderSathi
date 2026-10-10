import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import create_app
from app.memory import Memory
from tests.fakes import HashEmbedding

COMPANY = {"name": "Ernakulam Woodworks", "products": "desks, tables", "location": "Ernakulam",
           "turnover": "₹1.4 crore", "udyam": True, "documents": ["gst.pdf"],
           "past_orders": [{"buyer": "KSEB", "item": "desks", "value": "₹8 lakh", "year": 2025}]}


@pytest.fixture
def client(tmp_path):
    conn = db.connect(":memory:")
    mem = Memory(str(tmp_path / "chroma"), embedding_function=HashEmbedding())
    return TestClient(create_app(conn, mem, tmp_path))


@pytest.fixture
def company(client):
    return client.post("/companies", json=COMPANY).json()["id"]


@pytest.fixture
def fake_agents(monkeypatch):
    """Replace every agent's LLM work with fixed outputs; returns a setter to override one."""
    from app import schemas
    from datetime import datetime

    from app.agents import checklist, concessions, drafter, eligibility, reader, reviewer, tracker
    from tests.samples import CHECKLIST, FACTS, verdicts

    outputs = {
        (reader, "extract_facts"): FACTS,
        (tracker, "parse_deadline"): datetime(2026, 10, 30, 15, 0),
        (eligibility, "judge_eligibility"): verdicts(),
        (checklist, "build_checklist"): CHECKLIST,
        (concessions, "find_concessions"): schemas.Concessions(items=[]),
        (drafter, "draft_bid"): schemas.BidDraft(
            cover_letter="Dear Sir", sections=[schemas.Section(title="Experience", body="KSEB desks")]),
        (reviewer, "review_draft"): schemas.ReviewResult(matrix=[schemas.ComplianceRow(
            rule_text=FACTS.rules[0].text, must_have=True, covered=True, where="Experience")], gaps=[]),
    }

    def use(module, name, value):
        monkeypatch.setattr(module, name, lambda *args, **kwargs: value)

    for (module, name), value in outputs.items():
        use(module, name, value)
    return use


@pytest.fixture
def tender(client, tmp_path):
    from tests.pdfs import make_pdf
    with open(make_pdf(tmp_path, ["1. Scope\nSupply desks\n4.1 Turnover of Rs 1 crore\n"]), "rb") as f:
        return client.post("/tenders", files={"file": ("desks.pdf", f, "application/pdf")}).json()["id"]
