from app import config
from tests.conftest import COMPANY


def test_create_and_get_company(client, company):
    got = client.get(f"/companies/{company}").json()
    assert got["name"] == "Ernakulam Woodworks" and got["udyam"] is True
    assert got["documents"] == ["gst.pdf"] and got["past_orders"][0]["buyer"] == "KSEB"


def test_update_company_replaces_documents(client, company):
    r = client.post("/companies", json={**COMPANY, "id": company, "documents": ["pan.pdf"]})
    assert r.status_code == 200 and r.json() == {"id": company}
    assert client.get(f"/companies/{company}").json()["documents"] == ["pan.pdf"]


def test_update_unknown_company_404(client):
    r = client.post("/companies", json={**COMPANY, "id": 99})
    assert r.status_code == 404 and r.json() == {"detail": "Company not found"}


def test_get_unknown_company_404(client):
    assert client.get("/companies/99").status_code == 404


def test_storage_dir_relative_to_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", "../storage")
    backend = config.BACKEND_DIR
    assert config.storage_dir() == (backend / ".." / "storage").resolve()
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "abs"))
    assert config.storage_dir() == tmp_path / "abs" and (tmp_path / "abs").is_dir()


def test_startup_resets_stuck_runs(tmp_path):
    from fastapi.testclient import TestClient
    from app import db
    from app.main import create_app
    from app.memory import Memory
    from tests.fakes import HashEmbedding
    conn = db.connect(":memory:")
    tid = db.create_tender(conn, "/tmp/t.pdf", "t")
    db.set_tender_status(conn, tid, "running")
    with TestClient(create_app(conn, Memory(str(tmp_path / "c"), HashEmbedding()), tmp_path)):
        pass
    assert db.get_tender(conn, tid)["status"] == "failed"
