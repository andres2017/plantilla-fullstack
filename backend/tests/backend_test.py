"""Backend tests — auth, RBAC, e Items (CRUD de referencia).

Duplica la clase TestItems como plantilla al agregar pruebas para una entidad nueva.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@example.com", "password": "Admin123!"}
USER = {"email": "usuario@example.com", "password": "Usuario123!"}


def _future_iso(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# ------------------ Fixtures ------------------
@pytest.fixture
def anon():
    return requests.Session()


@pytest.fixture
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture
def user_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=USER)
    assert r.status_code == 200, f"user login failed: {r.status_code} {r.text}"
    return s


# ------------------ Health ------------------
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


# ------------------ Auth ------------------
class TestAuth:
    def test_login_admin(self, anon):
        r = anon.post(f"{API}/auth/login", json=ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["data"]["email"] == ADMIN["email"]
        assert body["data"]["role"] == "admin"
        # cookies set
        assert "access_token" in anon.cookies
        assert "refresh_token" in anon.cookies

    def test_login_invalid_returns_401_envelope(self, anon):
        r = anon.post(f"{API}/auth/login",
                      json={"email": f"nobody-{uuid.uuid4().hex}@example.com", "password": "Wrong123!"})
        assert r.status_code == 401
        body = r.json()
        assert body["success"] is False
        assert body["data"] is None
        assert isinstance(body["error"], str) and body["error"]

    def test_me_without_cookie_401(self, anon):
        r = anon.get(f"{API}/auth/me")
        assert r.status_code == 401
        assert r.json()["success"] is False

    def test_me_with_cookie(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["email"] == ADMIN["email"]
        assert d["role"] == "admin"

    def test_register_creates_usuario_and_sets_cookies(self, anon):
        email = f"test_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = anon.post(f"{API}/auth/register",
                      json={"email": email, "name": "Reg User", "password": "Pass1234!"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["success"] is True
        assert body["data"]["email"] == email
        assert body["data"]["role"] == "usuario"
        assert "access_token" in anon.cookies
        assert "refresh_token" in anon.cookies

    def test_refresh_rotates_and_reuse_fails(self, anon):
        r = anon.post(f"{API}/auth/login", json=ADMIN)
        assert r.status_code == 200
        old_refresh = anon.cookies.get("refresh_token")
        assert old_refresh
        r1 = anon.post(f"{API}/auth/refresh")
        assert r1.status_code == 200, r1.text
        new_refresh = anon.cookies.get("refresh_token")
        assert new_refresh and new_refresh != old_refresh
        reuse = requests.post(f"{API}/auth/refresh", cookies={"refresh_token": old_refresh})
        assert reuse.status_code == 401
        assert reuse.json()["success"] is False

    def test_logout_clears_cookies(self, admin_session):
        r = admin_session.post(f"{API}/auth/logout")
        assert r.status_code == 200
        r2 = admin_session.get(f"{API}/auth/me")
        assert r2.status_code == 401

    def test_bruteforce_lockout_429(self):
        bad_email = f"bf_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        codes = []
        for _ in range(6):
            r = s.post(f"{API}/auth/login", json={"email": bad_email, "password": "x"})
            codes.append(r.status_code)
        assert 429 in codes, f"expected lockout 429 in {codes}"


# ------------------ RBAC (demostrado sobre /items) ------------------
class TestRBAC:
    def test_user_can_get_items(self, user_session):
        r = user_session.get(f"{API}/items")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_user_cannot_post_items(self, user_session):
        r = user_session.post(f"{API}/items", json={"name": "no deberia crearse"})
        assert r.status_code == 403
        assert r.json()["success"] is False

    def test_user_cannot_delete(self, user_session):
        r = user_session.delete(f"{API}/items/000000000000000000000000")
        assert r.status_code == 403


# ------------------ Items CRUD (entidad de referencia) ------------------
class TestItems:
    def test_create_get_update_delete(self, admin_session):
        r = admin_session.post(f"{API}/items", json={"name": f"Item {uuid.uuid4().hex[:6]}", "description": "demo"})
        assert r.status_code == 201, r.text
        item = r.json()["data"]
        assert item["active"] is True
        item_id = item["id"]

        r2 = admin_session.get(f"{API}/items/{item_id}")
        assert r2.status_code == 200
        assert r2.json()["data"]["name"] == item["name"]

        r3 = admin_session.patch(f"{API}/items/{item_id}", json={"active": False})
        assert r3.status_code == 200
        assert r3.json()["data"]["active"] is False

        r4 = admin_session.delete(f"{API}/items/{item_id}")
        assert r4.status_code == 200
        r5 = admin_session.get(f"{API}/items/{item_id}")
        assert r5.status_code == 404

    def test_get_not_found_404(self, admin_session):
        r = admin_session.get(f"{API}/items/000000000000000000000000")
        assert r.status_code == 404
        assert r.json()["success"] is False

    def test_list_pagination_and_filter(self, admin_session):
        r = admin_session.get(f"{API}/items", params={"page": 1, "limit": 5})
        assert r.status_code == 200
        d = r.json()["data"]
        assert "items" in d and "pagination" in d
        assert d["pagination"]["page"] == 1
        assert d["pagination"]["limit"] == 5
        assert len(d["items"]) <= 5

        r2 = admin_session.get(f"{API}/items", params={"active": "true", "limit": 3})
        assert r2.status_code == 200
        for it in r2.json()["data"]["items"]:
            assert it["active"] is True

    def test_validation_422_envelope(self, admin_session):
        # name muy corto
        r = admin_session.post(f"{API}/items", json={"name": "a"})
        assert r.status_code == 422
        b = r.json()
        assert b["success"] is False
        assert isinstance(b["error"], str)
