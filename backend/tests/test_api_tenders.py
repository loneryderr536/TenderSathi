from tests.pdfs import make_pdf


def upload(client, path, name="desks.pdf", **data):
    with open(path, "rb") as f:
        return client.post("/tenders", files={"file": (name, f, "application/pdf")}, data=data)


def saved_files(tmp_path):
    folder = tmp_path / "tenders"
    return list(folder.iterdir()) if folder.exists() else []


def test_upload_and_inbox(client, tmp_path):
    r = upload(client, make_pdf(tmp_path, ["1. Scope\nSupply desks"]))
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "desks" and body["status"] == "new"
    inbox = client.get("/tenders").json()
    assert [(t["id"], t["status"]) for t in inbox] == [(body["id"], "new")]
    assert len(saved_files(tmp_path)) == 1


def test_scanned_pdf_rejected(client, tmp_path):
    r = upload(client, make_pdf(tmp_path, [""], name="scan.pdf"))
    assert r.status_code == 400
    assert r.json() == {"detail": "This looks like a scanned PDF; please use a text PDF"}
    assert client.get("/tenders").json() == [] and saved_files(tmp_path) == []


def test_non_pdf_rejected(client, tmp_path):
    r = client.post("/tenders", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400 and r.json() == {"detail": "Please upload a PDF file"}
    assert client.get("/tenders").json() == [] and saved_files(tmp_path) == []


def test_inbox_newest_first(client, tmp_path):
    pdf = make_pdf(tmp_path, ["1. Scope\nSupply desks"])
    first = upload(client, pdf, title="First").json()["id"]
    second = upload(client, pdf, title="Second").json()["id"]
    assert [t["id"] for t in client.get("/tenders").json()] == [second, first]


def test_text_file_named_pdf_rejected(client, tmp_path):
    r = client.post("/tenders", files={"file": ("notes.pdf", b"# just markdown", "application/pdf")})
    assert r.status_code == 400 and r.json() == {"detail": "Please upload a PDF file"}
    assert saved_files(tmp_path) == []


def test_inbox_marks_tenders_that_fit_the_business(client, company, tmp_path):
    fits = upload(client, make_pdf(tmp_path, ["1. Scope\nSupply of school desks, Ernakulam"]), title="Desks").json()["id"]
    other = upload(client, make_pdf(tmp_path, ["1. Scope\nSupply of hospital beds"]), title="Beds").json()["id"]
    inbox = {t["id"]: t["match"] for t in client.get(f"/tenders?company_id={company}").json()}
    assert inbox[fits] == {"fits": True, "matched": ["desk"], "in_area": True}
    assert inbox[other]["fits"] is False and inbox[other]["matched"] == []
    assert "match" not in client.get("/tenders").json()[0]


def test_inbox_unknown_company_404(client):
    assert client.get("/tenders?company_id=99").status_code == 404
