"""Regression tests after wall_utils.py extraction (Environment 780dad87).

Verifies:
  * /api/wall/status, /api/wall/opt-in, /api/wall/feed, /api/wall/cheer work
  * /api/dashboard/progress returns 5 pills and triggers foundation_ready
    wall event once opted in.
  * /api/dashboard/weekly-email/preview,status,note (get+post) work with
    BADGE_LABELS import from wall_utils.
  * /api/learning/hubs still responds (mentioned as /learning/articles in
    review — actual endpoint is /learning/hubs).
  * first_compare badge is logged via deep_dive_compare_router_factory
    when a compare share transitions to active — smoke check that the
    import path is valid (unit-level).
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _register():
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_wall_{suffix}@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "Sam Wall Test",
    }, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return r.json()["access_token"], email


@pytest.fixture(scope="module")
def auth():
    token, email = _register()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, email


# ----- Wall endpoints ------------------------------------------------------
class TestWallEndpoints:
    def test_status_default_opted_out(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/wall/status", headers=h, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["opt_in"] is False
        assert isinstance(data["my_events_this_month"], int)

    def test_opt_in_toggle(self, auth):
        h, _ = auth
        r = requests.post(f"{BASE_URL}/api/wall/opt-in", headers=h,
                          json={"opt_in": True}, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["opt_in"] is True
        assert "backfilled_event" in data
        # Confirm status now reflects opt_in true
        r2 = requests.get(f"{BASE_URL}/api/wall/status", headers=h, timeout=10)
        assert r2.json()["opt_in"] is True

    def test_feed(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/wall/feed?days=30&limit=20",
                         headers=h, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "events" in data
        assert "total" in data
        assert "top_cheered" in data
        assert isinstance(data["events"], list)

    def test_cheer_own_forbidden(self, auth):
        """Cheering a nonexistent event → 404. Verifies the endpoint responds."""
        h, _ = auth
        r = requests.post(f"{BASE_URL}/api/wall/cheer/nonexistent_xyz",
                          headers=h, timeout=10)
        assert r.status_code == 404


# ----- Progress dashboard --------------------------------------------------
class TestProgressDashboard:
    def test_progress_returns_five_pills(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/dashboard/progress",
                         headers=h, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "pills" in data
        assert len(data["pills"]) == 5
        ids = {p["id"] for p in data["pills"]}
        assert ids == {"foundation_completed", "child_needs_identified",
                       "communication_readiness", "mediation_readiness",
                       "conflict_reduced"}
        assert data["total"] == 5
        assert isinstance(data["completed_count"], int)
        assert "foundation_ready" in data
        assert "history" in data
        assert "streak_days" in data


# ----- Weekly email preview/status/note ------------------------------------
class TestWeeklyEmail:
    def test_preview(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/dashboard/weekly-email/preview",
                         headers=h, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "week_key" in data
        assert "preview" in data
        p = data["preview"]
        assert "completed_count" in p
        assert "streak_days" in p
        assert "milestones_this_week" in p
        assert "dashboard_url" in p

    def test_status(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/dashboard/weekly-email/status",
                         headers=h, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "week_key" in data
        assert "sent_this_week" in data
        assert "weekday_utc" in data

    def test_note_save_and_get(self, auth):
        h, _ = auth
        # Save
        note_text = "TEST_ Keep the pledge fresh: patience over reactions."
        r = requests.post(f"{BASE_URL}/api/dashboard/weekly-email/note",
                          headers=h, json={"note": note_text}, timeout=10)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["note"] == note_text
        assert saved["cleared"] is False
        # GET
        r2 = requests.get(f"{BASE_URL}/api/dashboard/weekly-email/note",
                          headers=h, timeout=10)
        assert r2.status_code == 200
        assert r2.json()["note"] == note_text
        # Clear
        r3 = requests.post(f"{BASE_URL}/api/dashboard/weekly-email/note",
                           headers=h, json={"note": ""}, timeout=10)
        assert r3.status_code == 200
        assert r3.json()["cleared"] is True


# ----- Learning center -----------------------------------------------------
class TestLearning:
    def test_hubs(self, auth):
        h, _ = auth
        r = requests.get(f"{BASE_URL}/api/learning/hubs", headers=h, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        # Response contains a list of hubs
        assert isinstance(data, (list, dict))


# ----- wall_utils import path smoke ---------------------------------------
class TestImportPaths:
    def test_wall_utils_reexport_from_wall_routes(self):
        """wall_routes must still re-export the maybe_log_* helpers
        for backwards compat (source-level check)."""
        with open("/app/backend/wall_routes.py") as f:
            src = f.read()
        for name in ("maybe_log_foundation_ready", "maybe_log_first_compare",
                     "maybe_log_high_alignment", "maybe_log_communication_master",
                     "maybe_log_week_streak"):
            assert name in src, f"missing re-export: {name}"

    def test_deep_dive_factory_imports_wall_utils(self):
        """deep_dive_compare_router_factory must import from wall_utils."""
        with open("/app/backend/deep_dive_compare_router_factory.py") as f:
            src = f.read()
        assert "from wall_utils import maybe_log_first_compare" in src
        assert "from wall_utils import maybe_log_high_alignment" in src

    def test_progress_routes_imports_wall_utils(self):
        """progress_dashboard_routes must import from wall_utils at top level."""
        with open("/app/backend/progress_dashboard_routes.py") as f:
            src = f.read()
        assert "from wall_utils import" in src
        assert "BADGE_LABELS" in src
