from app.agents import gap_plan


def test_gap_plan_for_missing_items(client, company, tender, fake_agents, monkeypatch):
    from app.agents import eligibility
    from tests.samples import verdicts
    fake_agents(eligibility, "judge_eligibility", verdicts("missing"))
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    seen = {}

    def fake_plan(gaps, deadline, business, today):
        seen["gaps"] = gaps
        return gap_plan.GapPlan(steps=[gap_plan.GapStep(gap=g, how="Apply online", where="udyamregistration.gov.in",
                                                        typical_days=2, fits_deadline=True) for g in gaps])

    monkeypatch.setattr(gap_plan, "plan_gaps", fake_plan)
    plan = client.post(f"/tenders/{tender}/gap-plan", json={"company_id": company}).json()
    assert "ISO 9001 certificate (clause 4.2)" in seen["gaps"] and plan["steps"][0]["fits_deadline"] is True
    assert client.get(f"/tenders/{tender}/result").json()["gap_plan"] == plan


def test_result_has_score_and_feedback(client, company, tender, fake_agents):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    client.post(f"/tenders/{tender}/feedback", json={"agent": "eligibility", "item": "Turnover", "correct": False})
    client.post(f"/tenders/{tender}/feedback", json={"agent": "eligibility", "item": "Turnover", "correct": True})
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["feedback"] == {"Turnover": True}
    assert result["score"]["decision"] in {"bid", "bid_with_care"}
    assert client.get("/tenders").json()[0]["score"] == result["score"]


def test_gap_plan_409_when_nothing_is_missing(client, company, tender, fake_agents):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    assert client.post(f"/tenders/{tender}/gap-plan", json={"company_id": company}).status_code == 409
