"""Backend tests for the analytics endpoints (/api/analytics/*).

Covers personal dashboard and admin-only endpoints. Uses the two seeded
credentials documented in /app/memory/test_credentials.md.
"""
import os
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

PARENT_EMAIL = "parent1@test.com"
PARENT_PASSWORD = "TestPass123!"
ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASSWORD = "AdminPass123!"

PREP_SECTIONS = ["child_goals", "issues", "priority", "comm_style", "readiness"]


def _ensure_account(email: str, password: str, name: str) -> str:
    """Try register; if dup, login. Return access_token."""
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=20,
    )
    if r.status_code == 200:
        return r.json()["access_token"]
    # Already exists or other reason -> login
    r2 = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    assert r2.status_code == 200, f"login failed for {email}: {r2.status_code} {r2.text}"
    return r2.json()["access_token"]


@pytest.fixture(scope="module")
def parent_token():
    return _ensure_account(PARENT_EMAIL, PARENT_PASSWORD, "Sam Parent")


@pytest.fixture(scope="module")
def admin_token():
    return _ensure_account(ADMIN_EMAIL, ADMIN_PASSWORD, "Matt Sossi")


def _assert_no_mongo_id(obj):
    """Walk the response and assert no `_id` keys are present anywhere."""
    if isinstance(obj, dict):
        assert "_id" not in obj, f"MongoDB _id leak: {obj}"
        for v in obj.values():
            _assert_no_mongo_id(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_no_mongo_id(v)


# ============ Personal /api/analytics/me ============
class TestPersonalAnalytics:
    def test_me_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/analytics/me", timeout=15)
        assert r.status_code == 401, f"expected 401 got {r.status_code} {r.text}"

    def test_me_returns_full_shape(self, parent_token):
        # Seed at least one prep section so steps_done > 0 isn't required, but
        # we still validate the shape regardless of state.
        h = {"Authorization": f"Bearer {parent_token}"}
        # save readiness so readiness.current is computed
        requests.put(
            f"{BASE_URL}/api/mediation/readiness",
            json={"answers": {"q1": 4, "q2": 3, "q3": 5}},
            headers=h,
            timeout=15,
        )
        r = requests.get(f"{BASE_URL}/api/analytics/me", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_no_mongo_id(data)

        # User block
        assert "user" in data
        assert data["user"]["email"] == PARENT_EMAIL

        # Progress
        assert "progress" in data
        prog = data["progress"]
        assert "steps_done" in prog
        assert prog.get("steps_total") == 5
        assert isinstance(prog["steps_done"], int)
        assert 0 <= prog["steps_done"] <= 5

        # Readiness
        assert "readiness" in data
        assert "current" in data["readiness"]
        assert "trend" in data["readiness"] and isinstance(data["readiness"]["trend"], list)

        # Activity
        act = data["activity"]
        for k in ("summaries", "agreements", "mediator_emails"):
            assert k in act, f"missing activity.{k}"
            assert isinstance(act[k], int)

        # Recent summaries
        assert "recent_summaries" in data
        assert isinstance(data["recent_summaries"], list)


# ============ Admin endpoints ============
class TestAdminAnalytics:
    def test_overview_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/analytics/admin/overview", timeout=15)
        assert r.status_code == 401

    def test_overview_forbidden_for_non_admin(self, parent_token):
        h = {"Authorization": f"Bearer {parent_token}"}
        r = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=h, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_overview_ok_for_admin(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_no_mongo_id(data)

        # users.* keys
        users = data["users"]
        for k in ("total", "new_7d", "auth_breakdown"):
            assert k in users, f"missing users.{k}"
        assert isinstance(users["total"], int)
        assert isinstance(users["new_7d"], int)
        assert isinstance(users["auth_breakdown"], dict)

        # engagement.summaries_total
        assert "summaries_total" in data["engagement"]

        # magic_links.conversion_pct
        ml = data["magic_links"]
        assert "conversion_pct" in ml
        assert isinstance(ml["conversion_pct"], (int, float))

        # funnel for all 5 prep sections
        funnel = data["funnel"]
        for sec in PREP_SECTIONS:
            assert sec in funnel, f"funnel missing {sec}"
            assert isinstance(funnel[sec], int)

    def test_recent_users_admin(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(
            f"{BASE_URL}/api/analytics/admin/recent-users?limit=5",
            headers=h,
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_no_mongo_id(data)
        users = data["users"]
        assert isinstance(users, list)
        assert len(users) <= 5
        for u in users:
            assert "steps_done" in u and isinstance(u["steps_done"], int)
            assert u.get("steps_total") == 5
            assert "summaries" in u and isinstance(u["summaries"], int)

    def test_recent_users_forbidden_for_non_admin(self, parent_token):
        h = {"Authorization": f"Bearer {parent_token}"}
        r = requests.get(
            f"{BASE_URL}/api/analytics/admin/recent-users?limit=5",
            headers=h,
            timeout=15,
        )
        assert r.status_code == 403

    def test_daily_signups_14_days(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(
            f"{BASE_URL}/api/analytics/admin/daily-signups?days=14",
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_no_mongo_id(data)
        assert data["days"] == 14
        series = data["series"]
        assert isinstance(series, list)
        assert len(series) == 14
        for bucket in series:
            assert "date" in bucket and "count" in bucket
            assert isinstance(bucket["count"], int)

    def test_daily_signups_clamps_to_90(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(
            f"{BASE_URL}/api/analytics/admin/daily-signups?days=999",
            headers=h,
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["days"] == 90
        assert len(data["series"]) == 90

    def test_daily_signups_forbidden_for_non_admin(self, parent_token):
        h = {"Authorization": f"Bearer {parent_token}"}
        r = requests.get(
            f"{BASE_URL}/api/analytics/admin/daily-signups?days=14",
            headers=h,
            timeout=15,
        )
        assert r.status_code == 403


# ============ Guest user is NOT admin ============
class TestGuestNotAdmin:
    def test_guest_forbidden_on_admin(self):
        r = requests.post(f"{BASE_URL}/api/auth/guest", json={}, timeout=15)
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        r2 = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=h, timeout=15)
        assert r2.status_code == 403, f"expected 403 got {r2.status_code} {r2.text}"
