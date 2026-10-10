from app.routes.admin import accuracy, agent_metrics


def line(run, agent, message, t):
    return {"run_id": run, "tender_id": 1, "agent": agent, "message": message, "created_at": f"2026-10-10 10:00:{t:02d}"}


def test_agent_metrics_times_retries_and_failures():
    log = [line("r1", "reader", "started", 0), line("r1", "reader", "finished", 4),
           line("r2", "reader", "started", 10), line("r2", "reader", "error, retrying: 429", 12),
           line("r2", "reader", "finished", 18), line("r2", "drafter", "started", 20),
           line("r2", "drafter", "failed: boom", 30)]
    reader, drafter = agent_metrics(log)
    assert (reader["agent"], reader["runs"], reader["avg_seconds"], reader["retries"]) == ("reader", 2, 6.0, 1)
    assert (drafter["failures"], drafter["avg_seconds"]) == (1, None) and drafter["model"]


def test_accuracy_from_owner_feedback():
    fb = [{"agent": "eligibility", "correct": 1}, {"agent": "eligibility", "correct": 0},
          {"agent": "eligibility", "correct": 1}, {"agent": "eligibility", "correct": 1}]
    assert accuracy(fb) == [{"agent": "eligibility", "judged": 4, "correct": 3, "accuracy": 75}]


def test_stats_endpoint(client, company, tender, fake_agents):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    client.post(f"/tenders/{tender}/feedback", json={"agent": "eligibility", "item": "rule", "correct": True})
    stats = client.get("/admin/stats").json()
    assert stats["tenders"] == 1 and stats["businesses"] == 1 and stats["by_source"] == {"Uploaded": 1}
    assert {a["agent"] for a in stats["agents"]} >= {"reader", "drafter", "reviewer"}
    assert stats["runs"][0]["title"] and stats["accuracy"][0]["accuracy"] == 100
