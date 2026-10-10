import json

from app import db
from tests.conftest import COMPANY
from tests.pdfs import make_pdf


def make_feed(tmp_path):
    folder = tmp_path / "feed"
    folder.mkdir()
    make_pdf(folder, ["1. Scope\nSupply of school desks\n4.1 Turnover of Rs 1 crore"], name="desks.pdf")
    make_pdf(folder, ["1. Scope\nSupply of hospital beds\n4.1 Turnover of Rs 5 crore"], name="beds.pdf")
    feed = folder / "portal_feed.json"
    feed.write_text(json.dumps({"tenders": [
        {"source_id": "GEM/1", "portal": "GeM", "buyer": "Schools Board", "title": "Desks", "pdf": "desks.pdf"},
        {"source_id": "CPPP/2", "portal": "CPPP", "buyer": "Health Society", "title": "Beds", "pdf": "beds.pdf"},
    ]}))
    return feed


def test_scout_adds_new_tenders_and_runs_only_those_that_fit(client, company, fake_agents, tmp_path):
    client.app.state.feed_path = make_feed(tmp_path)
    r = client.post("/scout/run", json={"company_id": company}).json()
    assert r["found"] == 2 and len(r["added"]) == 2 and len(r["queued"]) == 1

    inbox = {t["title"]: t for t in client.get("/tenders").json()}
    assert inbox["Desks"]["portal"] == "GeM" and inbox["Desks"]["buyer"] == "Schools Board"
    assert inbox["Desks"]["status"] == "awaiting_approval"          # the agents ran on their own
    assert inbox["Beds"]["status"] == "new"                         # not a fit: added, not run
    log = client.get(f"/tenders/{inbox['Desks']['id']}/log").json()
    assert log[0]["agent"] == "scout" and "GeM" in log[0]["message"]

    again = client.post("/scout/run", json={"company_id": company}).json()
    assert again["added"] == [] and len(client.get("/tenders").json()) == 2   # nothing twice
    runs = client.get("/scout/runs").json()
    assert [r["added"] for r in runs] == [0, 2]


def test_scout_without_a_business_only_adds(client, tmp_path):
    client.app.state.feed_path = make_feed(tmp_path)
    r = client.post("/scout/run").json()
    assert len(r["added"]) == 2 and r["queued"] == []


def test_scout_unknown_company_404(client, tmp_path):
    client.app.state.feed_path = make_feed(tmp_path)
    assert client.post("/scout/run", json={"company_id": 99}).status_code == 404
