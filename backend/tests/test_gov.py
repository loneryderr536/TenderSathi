from app import llm, schemas
from app.agents import fairness
from tests.fakes import FakeLLM
from tests.pdfs import make_pdf

TENDER_PAGES = ["1. Scope\nSupply of benches. Estimated value Rs. 9 lakh.\n"
                "4.1 Turnover of Rs 2 crore. Mandatory.\n6. EMD of Rs 1,00,000. No bidder is exempt from EMD."]


def all_ok_but_emd():
    return fairness.FairnessFindings(findings=[
        fairness.Finding(check_id=c["id"], status="concern" if c["id"] == "emd_exemption" else "ok",
                         clause="6" if c["id"] == "emd_exemption" else "", page=1, explanation="why",
                         suggestion="Exempt registered MSEs from EMD." if c["id"] == "emd_exemption" else "")
        for c in fairness.CHECKS[1:]] + [fairness.Finding(
            check_id="emd_exemption", status="concern", clause="6", page=1, explanation="No MSE exemption",
            suggestion="Exempt registered MSEs from EMD.")])


def test_fairness_retrieves_clauses_per_check_and_scores(monkeypatch):
    fake = FakeLLM([all_ok_but_emd()])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    queries = []

    def search(q):
        queries.append(q)
        return [schemas.Clause(text="EMD of Rs 1,00,000. No bidder is exempt.", clause="6", page=1)]

    report = fairness.check_fairness(search)
    assert len(queries) == len(fairness.CHECKS) and len(fake.calls) == 1
    assert "Public Procurement Policy" in str(fake.calls[0][1]) and "[clause 6, page 1]" in str(fake.calls[0][1])
    assert report["concerns"] == 1 and report["score"] == round(100 * 5 / 6)
    emd = next(f for f in report["findings"] if f["check_id"] == "emd_exemption")
    assert emd["status"] == "concern" and emd["suggestion"] and emd["policy"]


def test_unjudged_check_is_not_found(monkeypatch):
    fake = FakeLLM([fairness.FairnessFindings(findings=[])])
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    report = fairness.check_fairness(lambda q: [])
    assert {f["status"] for f in report["findings"]} == {"not_found"} and report["score"] == 100


def upload_draft(client, tmp_path):
    with open(make_pdf(tmp_path, TENDER_PAGES, name="draft.pdf"), "rb") as f:
        return client.post("/gov/drafts", files={"file": ("draft.pdf", f, "application/pdf")},
                           data={"title": "Benches draft"}).json()["id"]


def test_draft_is_checked_and_never_shown_to_businesses(client, tmp_path, monkeypatch):
    draft = upload_draft(client, tmp_path)
    assert client.get("/tenders").json() == []
    monkeypatch.setattr(fairness, "check_fairness", lambda search: {
        "score": 83, "concerns": 1, "findings": [{"check_id": "emd_exemption", "clauses_seen": len(search("EMD"))}]})
    report = client.post(f"/gov/tenders/{draft}/fairness").json()
    assert report["score"] == 83 and report["findings"][0]["clauses_seen"] > 0   # clauses were in the memory
    listed = client.get("/gov/tenders").json()
    assert [(t["id"], t["kind"], t["fairness_score"]) for t in listed] == [(draft, "draft", 83)]
    assert client.get(f"/gov/tenders/{draft}").json()["fairness"]["score"] == 83


def test_screening_counts_who_each_rule_shuts_out(client, company, tmp_path, monkeypatch):
    from app.agents import eligibility, reader
    from tests.conftest import COMPANY
    from tests.samples import FACTS, verdicts

    client.post("/companies", json={**COMPANY, "name": "Small Co", "udyam": True, "location": "Thrissur, Kerala"})
    draft = upload_draft(client, tmp_path)
    monkeypatch.setattr(reader, "extract_facts", lambda text: FACTS)
    answers = iter([verdicts("pass"), verdicts("fail")])
    monkeypatch.setattr(eligibility, "judge_eligibility", lambda rules, evidence: next(answers))

    assert client.post(f"/gov/tenders/{draft}/screen").json() == {"running": True}
    insights = client.get(f"/gov/tenders/{draft}").json()["insights"]
    assert insights["screened"] == 2 and insights["qualified"] == 1 and insights["running"] is False
    turnover = insights["by_rule"][0]
    assert (turnover["pass"], turnover["fail"]) == (1, 1)
    excluded = [b for b in insights["businesses"] if b["outcome"] == "excluded"]
    assert len(excluded) == 1 and excluded[0]["label"].startswith("Business B") and "Small Co" not in str(insights)
