"""Live integration tests for Communication Builder batch (biff-refine + sample purge)."""
import os, time, requests, pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"

from ai_ready import ai_headers  # noqa: E402

_AI = {}


def _ai():
    """Signed in with the AI notice accepted (AI endpoints need both)."""
    if not _AI:
        _AI.update(ai_headers(f"{BASE_URL}/api"))
    return _AI


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _biff(draft, flags=None, retries=3):
    body = {"raw": draft}
    if flags and flags.get("safety_flagged"):
        body["safety_flagged"] = True
    last = None
    for i in range(retries):
        r = requests.post(f"{BASE_URL}/api/portal/biff-refine", json=body, headers=_ai(), timeout=60)
        last = r
        if r.status_code == 429:
            time.sleep(10 + i * 5)
            continue
        return r
    return last


def test_biff_refine_preserves_times_question():
    r = _biff("You are late AGAIN. Can you pick up Sam at 5 or 6 tomorrow? I cannot do Saturday.")
    assert r.status_code in (200, 502), r.text
    if r.status_code == 502:
        assert "Suggested wording isn't available" in r.text
        pytest.skip("provider failure (502)")
    data = r.json()
    assert data["status"] in ("ok", "unavailable")
    if data["status"] == "ok":
        biff = data["biff"].lower()
        assert "5" in biff and "6" in biff
        assert "tomorrow" in biff
        assert "saturday" in biff
        assert "?" in data["biff"]  # question preserved


def test_biff_refine_preserves_money_date():
    r = _biff("You still owe me $120 for the dentist. Pay it by Friday June 12 or I will stop covering extras. Did you even read my email?")
    assert r.status_code in (200, 502), r.text
    if r.status_code == 502:
        pytest.skip("provider failure (502)")
    data = r.json()
    if data["status"] == "ok":
        biff = data["biff"]
        assert "120" in biff
        assert "friday" in biff.lower() or "june" in biff.lower() or "12" in biff
        assert "?" in biff


def test_biff_grey_rock_safety():
    r = _biff("You keep ignoring my messages. Please confirm Thursday pickup at 4pm.", flags={"safety_flagged": True})
    assert r.status_code in (200, 502)
    if r.status_code == 502:
        pytest.skip("provider failure")
    data = r.json()
    assert data["status"] in ("ok", "unavailable")


def test_sample_purge_put_state(headers):
    # Fetch current state
    r = requests.get(f"{BASE_URL}/api/portal/state", headers=headers, timeout=30)
    assert r.status_code == 200
    envelope = r.json()
    orig = envelope.get("state") or envelope
    orig_milestones = list(orig.get("milestones") or [])
    orig_biff = list(orig.get("biff_logs") or [])

    # Exact built-in samples (must be stripped by PUT)
    sample_milestone = {"id": 1, "type": "success", "title": "On-Time Handoff Completed", "date": "2026-09-22",
                        "note": "Exchanged at neutral drop-off point without friction."}
    sample_biff = {"id": 1, "timestamp": "2026-09-20 14:30", "category": "Handoff Delay",
                   "original": "You are late again.", "biff": "Thank you for checking in. Arrived at 4:15 PM due to traffic."}
    # Parent-made entries that share title but different id/date — must survive
    real_milestone = {"id": "real-m-99", "type": "success", "title": "On-Time Handoff Completed",
                      "date": "2026-11-01", "note": "Real entry made by parent."}
    real_biff = {"id": "real-b-99", "timestamp": "2026-11-01 10:00", "category": "Note",
                 "original": "Different wording.", "biff": "Different reply."}

    payload = dict(orig)
    payload["milestones"] = [sample_milestone, real_milestone]
    payload["biff_logs"] = [sample_biff, real_biff]
    put = requests.put(f"{BASE_URL}/api/portal/state", headers=headers, json=payload, timeout=30)
    assert put.status_code in (200, 204), put.text

    g_env = requests.get(f"{BASE_URL}/api/portal/state", headers=headers, timeout=30).json()
    g = g_env.get("state") or g_env
    mids = [m.get("id") for m in (g.get("milestones") or [])]
    bids = [b.get("id") for b in (g.get("biff_logs") or [])]
    # Sample stripped
    assert 1 not in mids, f"sample milestone leaked: {g.get('milestones')}"
    assert 1 not in bids, f"sample biff leaked: {g.get('biff_logs')}"
    # Real preserved
    assert "real-m-99" in mids
    assert "real-b-99" in bids

    # Restore
    restore = dict(orig)
    restore["milestones"] = orig_milestones
    restore["biff_logs"] = orig_biff
    requests.put(f"{BASE_URL}/api/portal/state", headers=headers, json=restore, timeout=30)
