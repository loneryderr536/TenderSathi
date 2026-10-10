import pytest
from fastapi.testclient import TestClient

from app import auth, db
from app.main import create_app
from app.pdf_reader import pages_to_clauses, pdf_to_pages
from tests.conftest import COMPANY

RFQ = {"title": "Dining tables", "scope": "Supply of 60 wooden dining tables", "deadline": "5 November 2026",
       "requirements": ["One furniture order of Rs. 5 lakh in three years"], "documents": ["GST certificate"],
       "delivery_days": 45, "advance_percent": 30}


@pytest.fixture
def raw(tmp_path):
    """Real logins: a private owner, two businesses with profiles, a government buyer."""
    conn = db.connect(":memory:")
    client = TestClient(create_app(conn, None, tmp_path))

    def account(email, role, company=None, department=None):
        company_id = db.create_company(conn, **{**COMPANY, "name": company}) if company else None
        uid = db.create_user(conn, email, email.split("@")[0], role, auth.hash_password("pass1234"),
                             company_id=company_id, department=department)
        return {"Authorization": f"Bearer {auth.start_session(conn, uid)}"}

    return client, conn, {
        "owner": account("priya@x.in", "private", department="Marine Drive Hotels"),
        "other_owner": account("ravi@x.in", "private", department="Other Hotels"),
        "shop_a": account("a@x.in", "business", company="Shop A"),
        "shop_b": account("b@x.in", "business", company="Shop B"),
        "gov": account("mary@x.in", "government", department="Panchayat"),
    }


def test_advance_must_be_25_to_50_percent(raw):
    client, _, h = raw
    for bad in (0, 24, 51, 100):
        r = client.post("/rfq", json={**RFQ, "advance_percent": bad}, headers=h["owner"])
        assert r.status_code == 400 and "between 25% and 50%" in r.json()["detail"]
    for good in (25, 50):
        assert client.post("/rfq", json={**RFQ, "advance_percent": good}, headers=h["owner"]).status_code == 200


def test_posted_rfq_reaches_businesses_as_a_readable_tender(raw):
    client, conn, h = raw
    tid = client.post("/rfq", json=RFQ, headers=h["owner"]).json()["id"]
    inbox = {t["id"]: t for t in client.get("/tenders").json()}
    assert inbox[tid]["kind"] == "private" and inbox[tid]["buyer"] == "Marine Drive Hotels"
    assert inbox[tid]["advance_percent"] == 30 and inbox[tid]["portal"] == "Private RFQ"
    clauses = pages_to_clauses(pdf_to_pages(db.get_tender(conn, tid)["pdf_path"]))
    text = " ".join(c.text for c in clauses)
    assert "4.1" in [c.clause for c in clauses] and "advance of 30%" in text
    assert client.get(f"/tenders/{tid}/result").json()["tender"]["advance_percent"] == 30


def test_quotations_sent_compared_and_accepted(raw):
    client, _, h = raw
    tid = client.post("/rfq", json=RFQ, headers=h["owner"]).json()["id"]
    a = client.post(f"/rfq/{tid}/quote", json={"amount": 900000, "delivery_days": 40, "note": "Teak"}, headers=h["shop_a"])
    assert a.status_code == 200 and a.json()["status"] == "submitted"
    client.post(f"/rfq/{tid}/quote", json={"amount": 850000, "delivery_days": 50}, headers=h["shop_b"])
    client.post(f"/rfq/{tid}/quote", json={"amount": 880000, "delivery_days": 40}, headers=h["shop_a"])   # replaces

    quotes = client.get(f"/rfq/{tid}/quotations", headers=h["owner"]).json()
    assert [(q["company_name"], q["amount"]) for q in quotes] == [("Shop B", 850000), ("Shop A", 880000)]
    mine = client.get("/rfq/mine", headers=h["owner"]).json()
    assert mine[0]["quotations"] == 2 and mine[0]["lowest"] == 850000

    assert client.post(f"/rfq/{tid}/quotations/{quotes[0]['id']}/accept", headers=h["owner"]).json() == {"status": "awarded"}
    assert client.get(f"/rfq/{tid}/my-quote", headers=h["shop_b"]).json()["status"] == "accepted"
    assert client.get(f"/rfq/{tid}/my-quote", headers=h["shop_a"]).json()["status"] == "declined"
    assert client.post(f"/rfq/{tid}/quote", json={"amount": 1, "delivery_days": 1}, headers=h["shop_a"]).status_code == 409
    assert client.post(f"/rfq/{tid}/quotations/{quotes[1]['id']}/accept", headers=h["owner"]).status_code == 409


def test_owners_only_see_their_own_requests(raw):
    client, _, h = raw
    tid = client.post("/rfq", json=RFQ, headers=h["owner"]).json()["id"]
    assert client.get(f"/rfq/{tid}/quotations", headers=h["other_owner"]).status_code == 404
    assert client.get("/rfq/mine", headers=h["other_owner"]).json() == []
    assert client.get(f"/gov/tenders/{tid}", headers=h["other_owner"]).status_code == 404
    assert client.get(f"/gov/tenders/{tid}", headers=h["owner"]).status_code == 200      # same buyer controls
    assert [t["id"] for t in client.get("/gov/tenders", headers=h["owner"]).json()] == [tid]
    assert client.get(f"/gov/tenders/{tid}", headers=h["gov"]).status_code == 404         # not government's
    assert tid not in [t["id"] for t in client.get("/gov/tenders", headers=h["gov"]).json()]


def test_who_can_post_and_quote(raw):
    client, _, h = raw
    assert client.post("/rfq", json=RFQ, headers=h["shop_a"]).status_code == 403
    assert client.post("/rfq", json=RFQ, headers=h["gov"]).status_code == 403
    tid = client.post("/rfq", json=RFQ, headers=h["owner"]).json()["id"]
    assert client.post(f"/rfq/{tid}/quote", json={"amount": 5, "delivery_days": 5}, headers=h["owner"]).status_code == 403
    assert client.post(f"/rfq/{tid}/quote", json={"amount": 0, "delivery_days": 5}, headers=h["shop_a"]).status_code == 400


def test_private_owner_signup_needs_an_organisation(raw):
    client, _, _ = raw
    body = {"name": "Priya", "email": "new@hotel.in", "password": "long-enough-1", "role": "private"}
    assert client.post("/auth/signup", json=body).status_code == 400
    r = client.post("/auth/signup", json={**body, "department": "Lake Resort"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "private"
