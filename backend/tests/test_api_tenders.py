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
