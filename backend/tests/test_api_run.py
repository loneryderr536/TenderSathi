from app import db
from app.agents import eligibility
from tests.samples import FACTS, verdicts

AGENTS = ["reader", "eligibility", "checklist", "drafter", "reviewer", "await_approval"]


def test_run_end_to_end(client, company, tender, fake_agents):
    r = client.post(f"/tenders/{tender}/run", json={"company_id": company})
    assert r.status_code == 200 and len(r.json()["run_id"]) == 32
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["tender"]["status"] == "awaiting_approval"
    assert result["draft"]["cover_letter"] == "Dear Sir"
    assert len(result["verdicts"]["verdicts"]) == 2
    log = client.get(f"/tenders/{tender}/log").json()
    assert [l["agent"] for l in log if l["message"] == "finished"] == AGENTS
    assert client.get(f"/tenders/{tender}/log", params={"run_id": r.json()["run_id"]}).json() == log


def test_run_while_running_409(client, company, tender, fake_agents):
    db.set_tender_status(client.app.state.conn, tender, "running")
    r = client.post(f"/tenders/{tender}/run", json={"company_id": company})
    assert r.status_code == 409 and r.json() == {"detail": "A run is already in progress"}


def test_run_unknown_ids_404(client, company, tender):
    assert client.post("/tenders/99/run", json={"company_id": company}).status_code == 404
    assert client.post(f"/tenders/{tender}/run", json={"company_id": 99}).status_code == 404


def test_log_before_any_run_is_empty(client, tender):
    assert client.get(f"/tenders/{tender}/log").json() == []


def test_unknown_tender_404_on_reads(client):
    assert client.get("/tenders/99/log").status_code == 404
    assert client.get("/tenders/99/result").status_code == 404


def test_result_shows_stop_reason(client, company, tender, fake_agents):
    fake_agents(eligibility, "judge_eligibility", verdicts("fail", rules=FACTS.rules[:1]))
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["tender"]["status"] == "stopped"
    assert "Turnover of Rs 1 crore (clause 4.1, page 1)" in result["tender"]["reason"]
    assert result["draft"] is None
