"""Admin user management endpoint tests."""
import os
import pytest
import requests
from pathlib import Path


def _load_frontend_url():
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
    fenv = Path("/app/frontend/.env")
    if fenv.exists():
        for line in fenv.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE = _load_frontend_url()
API = f"{BASE}/api"

ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASS = "AdminPass123!"
USER_EMAIL = "parent1@test.com"
USER_PASS = "TestPass123!"


def _ensure_user(email, password, name):
    r = requests.post(
        f"{API}/auth/login", json={"email": email, "password": password}, timeout=20
    )
    if r.status_code == 403 and "suspended" in r.text.lower():
        # need admin to unsuspend first; caller handles
        return None
    if r.status_code == 200:
        return r.json()["access_token"]
    # try register
    r = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=20,
    )
    if r.status_code == 200:
        return r.json()["access_token"]
    # already exists but wrong password? try login again
    r = requests.post(
        f"{API}/auth/login", json={"email": email, "password": password}, timeout=20
    )
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


@pytest.fixture(scope="module")
def admin_token():
    tok = _ensure_user(ADMIN_EMAIL, ADMIN_PASS, "Matt Sossi")
    if not tok:
        pytest.skip("Admin account unavailable")
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def parent_user(admin_headers):
    """Ensure parent1 exists and is not suspended. Returns (token, user_id)."""
    # try login
    r = requests.post(
        f"{API}/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASS},
        timeout=20,
    )
    if r.status_code == 403:
        # find user_id via admin list and unsuspend
        rl = requests.get(
            f"{API}/analytics/admin/users",
            params={"q": USER_EMAIL, "suspended": "true"},
            headers=admin_headers,
            timeout=20,
        )
        if rl.status_code == 200:
            for u in rl.json().get("users", []):
                if u["email"].lower() == USER_EMAIL:
                    requests.post(
                        f"{API}/analytics/admin/users/{u['user_id']}/unsuspend",
                        headers=admin_headers,
                        timeout=20,
                    )
                    break
        r = requests.post(
            f"{API}/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASS},
            timeout=20,
        )
    if r.status_code != 200:
        # register
        r = requests.post(
            f"{API}/auth/register",
            json={"email": USER_EMAIL, "password": USER_PASS, "name": "Sam Parent"},
            timeout=20,
        )
    if r.status_code != 200:
        pytest.skip(f"Could not establish parent1 user: {r.status_code} {r.text}")
    data = r.json()
    return data["access_token"], data["user"]["user_id"]


# ============ Auth gating ============
class TestAuthGating:
    def test_unauth_returns_401(self):
        r = requests.get(f"{API}/analytics/admin/users", timeout=20)
        assert r.status_code == 401

    def test_non_admin_returns_403(self, parent_user):
        token, _ = parent_user
        r = requests.get(
            f"{API}/analytics/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 403


# ============ Listing ============
class TestListing:
    def test_admin_list_shape(self, admin_headers):
        r = requests.get(f"{API}/analytics/admin/users", headers=admin_headers, timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("users", "total", "limit", "offset"):
            assert k in d
        assert isinstance(d["users"], list)
        # no _id leakage
        for u in d["users"]:
            assert "_id" not in u
            assert "user_id" in u and "email" in u
        assert isinstance(d["total"], int)

    def test_search_filter(self, admin_headers, parent_user):
        r = requests.get(
            f"{API}/analytics/admin/users",
            params={"q": "parent1"},
            headers=admin_headers,
            timeout=20,
        )
        assert r.status_code == 200
        users = r.json()["users"]
        assert len(users) >= 1
        assert any(USER_EMAIL in u["email"] for u in users)

    def test_suspended_filter_excludes_active(self, admin_headers, parent_user):
        # parent1 is active here
        r = requests.get(
            f"{API}/analytics/admin/users",
            params={"suspended": "false", "q": "parent1"},
            headers=admin_headers,
            timeout=20,
        )
        assert r.status_code == 200
        users = r.json()["users"]
        # all returned must be non-suspended
        for u in users:
            assert u.get("suspended") is False

    def test_include_guests(self, admin_headers):
        r_no = requests.get(
            f"{API}/analytics/admin/users",
            params={"include_guests": "false", "limit": 200},
            headers=admin_headers,
            timeout=20,
        )
        r_yes = requests.get(
            f"{API}/analytics/admin/users",
            params={"include_guests": "true", "limit": 200},
            headers=admin_headers,
            timeout=20,
        )
        assert r_no.status_code == 200 and r_yes.status_code == 200
        # include_guests true should be >= without guests
        assert r_yes.json()["total"] >= r_no.json()["total"]

    def test_pagination_limit_clamp(self, admin_headers):
        r = requests.get(
            f"{API}/analytics/admin/users",
            params={"limit": 9999, "offset": 0},
            headers=admin_headers,
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json()["limit"] == 200

    def test_pagination_offset(self, admin_headers):
        r = requests.get(
            f"{API}/analytics/admin/users",
            params={"limit": 1, "offset": 0},
            headers=admin_headers,
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json()["offset"] == 0
        assert len(r.json()["users"]) <= 1


# ============ Suspend / Unsuspend ============
class TestSuspendUnsuspend:
    def test_cannot_suspend_self(self, admin_headers):
        # get admin user_id
        r = requests.get(
            f"{API}/analytics/admin/users",
            params={"q": ADMIN_EMAIL},
            headers=admin_headers,
            timeout=20,
        )
        admin_user = next(
            (u for u in r.json()["users"] if u["email"].lower() == ADMIN_EMAIL), None
        )
        assert admin_user, "admin user not found in listing"
        rs = requests.post(
            f"{API}/analytics/admin/users/{admin_user['user_id']}/suspend",
            headers=admin_headers,
            json={},
            timeout=20,
        )
        assert rs.status_code == 400
        assert "own account" in rs.json().get("detail", "").lower()

    def test_suspend_then_unsuspend_flow(self, admin_headers, parent_user):
        _, user_id = parent_user
        # suspend
        rs = requests.post(
            f"{API}/analytics/admin/users/{user_id}/suspend",
            headers=admin_headers,
            json={"reason": "TEST_automated"},
            timeout=20,
        )
        assert rs.status_code == 200, rs.text
        assert rs.json()["suspended"] is True

        # verify via list
        rl = requests.get(
            f"{API}/analytics/admin/users",
            params={"q": USER_EMAIL, "suspended": "true"},
            headers=admin_headers,
            timeout=20,
        )
        users = rl.json()["users"]
        assert any(u["user_id"] == user_id and u["suspended"] for u in users)

        # login should now 403
        rlog = requests.post(
            f"{API}/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASS},
            timeout=20,
        )
        assert rlog.status_code == 403
        assert "suspended" in rlog.json().get("detail", "").lower()

        # unsuspend
        ru = requests.post(
            f"{API}/analytics/admin/users/{user_id}/unsuspend",
            headers=admin_headers,
            timeout=20,
        )
        assert ru.status_code == 200
        assert ru.json()["suspended"] is False

        # login should now work
        rlog2 = requests.post(
            f"{API}/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASS},
            timeout=20,
        )
        assert rlog2.status_code == 200


# ============ Reset link ============
class TestResetLink:
    def test_send_reset_link_creates_magic_link(self, admin_headers, parent_user):
        _, user_id = parent_user
        r = requests.post(
            f"{API}/analytics/admin/users/{user_id}/send-reset-link",
            headers=admin_headers,
            json={"expires_minutes": 60},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        # either emailed OR fallback link
        assert "emailed" in d
        if not d["emailed"]:
            assert "link" in d and d["link"]
