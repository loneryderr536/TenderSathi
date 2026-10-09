from app import schemas
from app.agents import reader, tracker
from tests.pdfs import make_pdf
from tests.samples import FACTS

CHANGES = schemas.TenderChanges(changes=[schemas.Change(
    field="deadline", before="2026-10-30", after="2026-11-06", summary="Deadline extended by a week")],
    affects_eligibility=False)
NEW_FACTS = FACTS.model_copy(update={"deadline": "2026-11-06"})


def upload_corrigendum(client, tender, tmp_path, pages=("1. Scope\nSupply desks\n3. Last date 6 November 2026\n",)):
    with open(make_pdf(tmp_path, list(pages), name="corr.pdf"), "rb") as f:
        return client.post(f"/tenders/{tender}/corrigendum", files={"file": ("corr.pdf", f, "application/pdf")})


def test_corrigendum_compares_and_marks_tender_changed(client, company, tender, fake_agents, tmp_path, monkeypatch):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    seen = {}
    monkeypatch.setattr(reader, "extract_facts", lambda text: (seen.setdefault("text", text), NEW_FACTS)[1])
    monkeypatch.setattr(tracker, "compare_tenders", lambda old, new: (seen.update(old=old, new=new), CHANGES)[1])
    r = upload_corrigendum(client, tender, tmp_path)
    assert r.status_code == 200 and r.json() == CHANGES.model_dump()
    assert "[clause 3, page 1]" in seen["text"]
    assert (seen["old"], seen["new"]) == (FACTS, NEW_FACTS)
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["tender"]["status"] == "changed"
    assert result["changes"] == CHANGES.model_dump()
    assert [t["status"] for t in client.get("/tenders").json()] == ["changed"]


def test_corrigendum_before_any_run_409(client, tender, tmp_path):
    r = upload_corrigendum(client, tender, tmp_path)
    assert r.status_code == 409
    assert r.json() == {"detail": "Run the agents on this tender first, so there is something to compare"}


def test_corrigendum_rejects_scanned_pdf(client, company, tender, fake_agents, tmp_path):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})
    r = upload_corrigendum(client, tender, tmp_path, pages=("",))
    assert r.status_code == 400 and r.json()["detail"].startswith("This looks like a scanned PDF")
    assert client.get(f"/tenders/{tender}/result").json()["tender"]["status"] == "awaiting_approval"


def test_corrigendum_comparison_failure_502(client, company, tender, fake_agents, tmp_path, monkeypatch):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})

    def down(*args):
        raise RuntimeError("Groq is down")
    monkeypatch.setattr(reader, "extract_facts", down)
    r = upload_corrigendum(client, tender, tmp_path)
    assert r.status_code == 502 and r.json() == {"detail": "Could not compare the two versions: Groq is down"}
    assert client.get(f"/tenders/{tender}/result").json()["tender"]["status"] == "awaiting_approval"
    assert len(list((tmp_path / "tenders").iterdir())) == 1          # the rejected new version was removed


def test_corrigendum_unknown_tender_404(client, tmp_path):
    assert upload_corrigendum(client, 99, tmp_path).status_code == 404


def test_result_has_no_changes_by_default(client, tender):
    assert client.get(f"/tenders/{tender}/result").json()["changes"] is None
