import pytest
from fastapi.testclient import TestClient

from app import auth, db
from app.main import create_app
from tests.conftest import COMPANY


@pytest.fixture
def raw(tmp_path):
    """A client with the real login checks."""
    conn = db.connect(":memory:")
    return TestClient(create_app(conn, None, tmp_path)), conn


def signup(client, role="business", email="owner@shop.in", **extra):
    body = {"name": "Asha", "email": email, "password": "long-enough-1", "role": role, **extra}
    return client.post("/auth/signup", json=body)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_password_is_salted_and_hashed():
    a, b = auth.hash_password("secret-pass"), auth.hash_password("secret-pass")
    assert a != b and "secret-pass" not in a
    assert auth.check_password("secret-pass", a) and not auth.check_password("wrong-pass", a)


def test_signup_login_me_logout(raw):
    client, conn = raw
    r = signup(client, email=" Owner@Shop.in ")
    assert r.status_code == 200 and r.json()["user"]["email"] == "owner@shop.in"
    assert "password_hash" not in r.json()["user"]

    token = client.post("/auth/login", json={"email": "owner@shop.in", "password": "long-enough-1"}).json()["token"]
    me = client.get("/auth/me", headers=bearer(token)).json()
    assert (me["name"], me["role"], me["company_id"]) == ("Asha", "business", None)

    client.post("/auth/logout", headers=bearer(token))
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_bad_logins_and_signups(raw):
    client, _ = raw
    signup(client)
    assert client.post("/auth/login", json={"email": "owner@shop.in", "password": "nope-nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "who@shop.in", "password": "long-enough-1"}).status_code == 401
    assert signup(client).status_code == 409                                       # same email
    assert signup(client, email="x@y.in", password="short").status_code == 400
    assert signup(client, email="not-an-email").status_code == 400
    assert signup(client, role="platform", email="p@y.in").status_code == 400     # no self-made admins
    assert signup(client, role="government", email="g@y.in").status_code == 400   # needs a department
    assert client.get("/auth/me").status_code == 401


def test_roles_guard_the_dashboards(raw):
    client, conn = raw
    business = signup(client).json()["token"]
    gov = signup(client, role="government", email="officer@gov.in", department="Kuttanad Block Panchayat").json()["token"]
    admin_id = db.create_user(conn, "admin@ts.in", "Admin", "platform", auth.hash_password("admin-pass-1"))
    admin = auth.start_session(conn, admin_id)

    assert client.get("/gov/tenders").status_code == 401
    assert client.get("/gov/tenders", headers=bearer(business)).status_code == 403
    assert client.get("/gov/tenders", headers=bearer(gov)).status_code == 200
    assert client.get("/gov/tenders", headers=bearer(admin)).status_code == 200
    assert client.get("/admin/stats", headers=bearer(gov)).status_code == 403
    assert client.get("/admin/stats", headers=bearer(admin)).status_code == 200


def test_first_profile_belongs_to_the_owner(raw):
    client, _ = raw
    token = signup(client).json()["token"]
    company_id = client.post("/companies", json=COMPANY, headers=bearer(token)).json()["id"]
    assert client.get("/auth/me", headers=bearer(token)).json()["company_id"] == company_id
    client.post("/companies", json={**COMPANY, "name": "Second"}, headers=bearer(token))
    assert client.get("/auth/me", headers=bearer(token)).json()["company_id"] == company_id   # not replaced


def test_login_must_match_the_chosen_dashboard(raw):
    client, conn = raw
    signup(client)   # a business account
    creds = {"email": "owner@shop.in", "password": "long-enough-1"}
    assert client.post("/auth/login", json={**creds, "role": "business"}).status_code == 200
    r = client.post("/auth/login", json={**creds, "role": "government"})
    assert r.status_code == 403 and "not a government account" in r.json()["detail"]
    assert client.post("/auth/login", json={**creds, "role": "platform"}).status_code == 403
    # a wrong password says nothing about which dashboard the account belongs to
    assert client.post("/auth/login", json={**creds, "password": "wrong-pass", "role": "government"}).status_code == 401
