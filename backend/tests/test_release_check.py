"""Backend tests for release-check admin + cron endpoints (iteration 95)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}
PARENT = {"email": "parent1@test.com", "password": "TestPass123!"}


def _read_cron_secret() -> str:
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith("WEBHOOK_CRON_SECRET="):
                return line.split("=", 1)[1].strip()
    return ""


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def parent_token():
    return _login(PARENT)


# --- /api/admin/release-checks auth gating ------------------------------------
def test_list_release_checks_unauth():
    r = requests.get(f"{BASE_URL}/api/admin/release-checks", timeout=15)
    assert r.status_code == 401


def test_list_release_checks_forbidden_for_parent(parent_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/release-checks",
        headers={"Authorization": f"Bearer {parent_token}"},
        timeout=15,
    )
    assert r.status_code == 403


def test_list_release_checks_admin_ok(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/release-checks",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert "runs" in data and isinstance(data["runs"], list)


# --- POST /run (manual) -------------------------------------------------------
EXPECTED_NAMES = [
    "Home page",
    "Login page",
    "Dashboard page",
    "App code",
    "Backend API",
    "Card 1 Self-Assessment PDF",
    "Card 3 Child's Specific Needs PDF",
    "Card 4 Foundation Statement PDF",
    "Mediator Progress PDF",
]


def test_manual_run_release_check(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/release-checks/run",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["trigger"] == "manual"
    assert doc["ok"] is True, f"expected all checks ok, failures: {[x for x in doc['results'] if not x['ok']]}"
    names = [x["name"] for x in doc["results"]]
    assert names == EXPECTED_NAMES
    assert all(x["ok"] for x in doc["results"])


def test_manual_run_forbidden_for_parent(parent_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/release-checks/run",
        headers={"Authorization": f"Bearer {parent_token}"},
        timeout=30,
    )
    assert r.status_code == 403


# --- /api/cron/release-check --------------------------------------------------
def test_cron_release_check_no_auth():
    r = requests.post(f"{BASE_URL}/api/cron/release-check", timeout=15)
    assert r.status_code == 401


def test_cron_release_check_wrong_bearer():
    r = requests.post(
        f"{BASE_URL}/api/cron/release-check",
        headers={"Authorization": "Bearer not-the-real-secret"},
        timeout=15,
    )
    assert r.status_code == 401


def test_cron_release_check_valid_bearer_enqueues_daily_run(admin_token):
    secret = _read_cron_secret()
    assert secret, "WEBHOOK_CRON_SECRET missing from /app/backend/.env"
    # grab baseline count of 'daily' runs
    r0 = requests.get(
        f"{BASE_URL}/api/admin/release-checks?limit=50",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    baseline_daily = sum(1 for x in r0.json().get("runs", []) if x.get("trigger") == "daily")

    r = requests.post(
        f"{BASE_URL}/api/cron/release-check",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("enqueued") == "release-check"

    # Poll for the new daily run to appear.
    deadline = time.time() + 120
    found = False
    while time.time() < deadline:
        time.sleep(5)
        rr = requests.get(
            f"{BASE_URL}/api/admin/release-checks?limit=50",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        if rr.status_code == 200:
            daily = sum(1 for x in rr.json().get("runs", []) if x.get("trigger") == "daily")
            if daily > baseline_daily:
                found = True
                break
    assert found, "No new 'daily' run appeared within 120s after cron webhook"
