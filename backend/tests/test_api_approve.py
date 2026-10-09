def run(client, tender, company):
    client.post(f"/tenders/{tender}/run", json={"company_id": company})


def test_approve_with_edits_then_export(client, company, tender, fake_agents):
    run(client, tender, company)
    r = client.post(f"/tenders/{tender}/approve", json={"cover_letter": "Respected Sir, edited by owner"})
    assert r.status_code == 200 and r.json() == {"status": "approved"}

    r = client.get(f"/tenders/{tender}/export")
    assert r.status_code == 200
    assert r.headers["content-disposition"] == f'attachment; filename="bid-pack-{tender}.md"'
    text = r.text
    assert text.startswith("# desks\n")
    assert "Respected Sir, edited by owner" in text and "Dear Sir" not in text
    assert "## Experience\n" in text and "KSEB desks" in text
    assert "## Compliance matrix" in text and "| Turnover of Rs 1 crore | Yes | Yes | Experience |" in text
    assert "- [x] GST certificate (gst.pdf)" in text
    assert text.index("## Cover letter") < text.index("## Experience") < text.index("## Compliance matrix") \
        < text.index("## Document checklist")


def test_approve_keeps_review(client, company, tender, fake_agents):
    run(client, tender, company)
    client.post(f"/tenders/{tender}/approve", json={"sections": [{"title": "Scope", "body": "200 desks"}]})
    result = client.get(f"/tenders/{tender}/result").json()
    assert result["draft"]["sections"] == [{"title": "Scope", "body": "200 desks"}]
    assert result["draft"]["cover_letter"] == "Dear Sir"
    assert result["review"]["matrix"][0]["covered"] is True
    assert result["tender"]["status"] == "approved"


def test_approve_before_ready_409(client, tender):
    r = client.post(f"/tenders/{tender}/approve", json={})
    assert r.status_code == 409 and r.json() == {"detail": "Bid is not ready for approval"}


def test_export_before_approve_409(client, company, tender, fake_agents):
    run(client, tender, company)
    r = client.get(f"/tenders/{tender}/export")
    assert r.status_code == 409 and r.json() == {"detail": "Approve the bid before exporting"}


def test_approve_unknown_404(client):
    assert client.post("/tenders/99/approve", json={}).status_code == 404
    assert client.get("/tenders/99/export").status_code == 404


def test_approve_without_body(client, company, tender, fake_agents):
    run(client, tender, company)
    r = client.post(f"/tenders/{tender}/approve")
    assert r.status_code == 200 and r.json() == {"status": "approved"}


def test_approve_blank_cover_letter_400(client, company, tender, fake_agents):
    run(client, tender, company)
    r = client.post(f"/tenders/{tender}/approve", json={"cover_letter": "   "})
    assert r.status_code == 400 and r.json() == {"detail": "Cover letter cannot be empty"}
    assert client.get(f"/tenders/{tender}/result").json()["tender"]["status"] == "awaiting_approval"
