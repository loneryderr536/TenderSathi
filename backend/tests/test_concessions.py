from app import llm, schemas
from app.agents.concessions import find_concessions
from tests.fakes import FakeLLM

CLAUSE = schemas.Clause(text="MSEs registered under Udyam are exempt from EMD.", clause="3.2", page=1)
FOUND = schemas.Concessions(items=[schemas.Concession(benefit="EMD exempt for Udyam MSEs", clause="3.2", page=1)])


def test_no_clauses_no_call(monkeypatch):
    fake = FakeLLM([])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    assert find_concessions([], ["Company: X"]).items == [] and fake.calls == []


def test_one_call_with_clauses_and_profile(monkeypatch):
    fake = FakeLLM([FOUND])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    out = find_concessions([CLAUSE], ["Udyam/MSE registered: yes"])
    assert out == FOUND and fake.agents == ["checklist"] and len(fake.calls) == 1
    prompt = str(fake.calls[0][1])
    assert "exempt from EMD" in prompt and "clause 3.2" in prompt and "Udyam/MSE registered: yes" in prompt


def test_pipeline_finds_clauses_in_memory_and_stores_concessions(client, company, tender, fake_agents, monkeypatch):
    from app.agents import concessions
    seen = {}

    def fake_find(clauses, profile):
        seen["clauses"], seen["profile"] = clauses, profile
        return FOUND

    monkeypatch.setattr(concessions, "find_concessions", fake_find)
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["concessions"] == {"items": [FOUND.items[0].model_dump()]}
    assert seen["clauses"] and any("Udyam" in line for line in seen["profile"])   # came from the vector memory
