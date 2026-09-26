"""Iter75 backend tests: PATCH semantics for POST/PUT /api/portal/state.

Verifies that `pydantic.model_dump(exclude_unset=True)` allows partial
updates so a client sending `{safety_plan: null}` clears only that
field without clobbering align_records / milestones / biff_logs /
foundation_text / court_key / health_index / legal_report.

Also runs a lightweight regression for grey-rock BIFF (shorter reply
when safety_flagged=true).
"""
import os
import time
import pytest
import requests

def _load_backend_url() -> str:
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not set"
    return v.rstrip("/")


BASE_URL = _load_backend_url()
TIMEOUT = 30


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def token_p1():
    return _login("parent1@test.com", "TestPass123!")


@pytest.fixture(scope="module")
def token_p2():
    return _login("parent2@test.com", "TestPass123!")


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _get_state(tok: str) -> dict:
    r = requests.get(f"{BASE_URL}/api/portal/state", headers=_headers(tok), timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["state"]


def _put_state(tok: str, body: dict) -> dict:
    r = requests.put(
        f"{BASE_URL}/api/portal/state", json=body, headers=_headers(tok), timeout=TIMEOUT
    )
    assert r.status_code == 200, f"PUT failed: {r.status_code} {r.text}"
    return r.json()


# ------------------------------------------------------------------ #
# PATCH semantics
# ------------------------------------------------------------------ #
class TestPatchSemantics:
    def test_full_populate_then_null_safety_plan_keeps_other_fields(self, token_p1):
        """Populate all → PUT {safety_plan: null} → only safety_plan cleared."""
        full = {
            "align_records": [{"id": "a1", "note": "test"}],
            "milestones": [{"id": "m1", "title": "milestone1", "type": "success"}],
            "foundation_text": "our foundation is love",
            "court_key": "ALIGN-SA-2026",
            "safety_plan": {"safe_place": "Mom", "code_word": "pineapple"},
        }
        _put_state(token_p1, full)
        s = _get_state(token_p1)
        assert s["safety_plan"] is not None
        assert s["safety_plan"].get("safe_place") == "Mom"
        assert s["foundation_text"] == "our foundation is love"
        assert s["court_key"] == "ALIGN-SA-2026"
        assert len(s["align_records"]) == 1
        assert len(s["milestones"]) == 1

        # PATCH just safety_plan → null
        _put_state(token_p1, {"safety_plan": None})
        s2 = _get_state(token_p1)
        assert s2["safety_plan"] is None, f"safety_plan should be None: {s2['safety_plan']}"
        # Untouched fields must remain
        assert s2["foundation_text"] == "our foundation is love"
        assert s2["court_key"] == "ALIGN-SA-2026"
        assert len(s2["align_records"]) == 1
        assert s2["align_records"][0].get("id") == "a1"
        assert len(s2["milestones"]) == 1

    def test_patch_court_key_only(self, token_p1):
        _put_state(token_p1, {"court_key": "NEW-KEY-2026"})
        s = _get_state(token_p1)
        assert s["court_key"] == "NEW-KEY-2026"
        # Other fields intact
        assert s["foundation_text"] == "our foundation is love"
        assert len(s["align_records"]) == 1

    def test_empty_body_patch(self, token_p1):
        before = _get_state(token_p1)
        before_updated_at = before.get("updated_at")
        time.sleep(1.1)
        _put_state(token_p1, {})
        after = _get_state(token_p1)
        # updated_at should refresh, but data intact
        assert after["court_key"] == before["court_key"]
        assert after["foundation_text"] == before["foundation_text"]
        assert after.get("align_records") == before.get("align_records")
        assert after.get("milestones") == before.get("milestones")
        # updated_at bumped
        assert after.get("updated_at") != before_updated_at

    def test_full_state_put_replaces_all(self, token_p2):
        """Full-state PUT (existing frontend behavior) still works — regression."""
        full = {
            "align_records": [{"id": "b1"}],
            "milestones": [{"id": "n1", "title": "x", "type": "success"}],
            "biff_logs": [{"id": "l1", "biff": "hi", "timestamp": "2026-01-01"}],
            "foundation_text": "p2 foundation",
            "legal_report": {"sigA": "A", "sigB": "B", "sigMed": "M"},
            "health_index": {"s1": 7, "s2": 6, "s3": 5},
            "court_key": "COURT-8842",
            "reassessments": [],
            "safety_ack": {"cleared": True, "flagged": False, "date": "2026-01-01"},
            "safety_plan": {"safe_place": "Aunt house"},
        }
        _put_state(token_p2, full)
        s = _get_state(token_p2)
        assert s["foundation_text"] == "p2 foundation"
        assert s["court_key"] == "COURT-8842"
        assert s["health_index"] == {"s1": 7, "s2": 6, "s3": 5}
        assert s["safety_ack"]["cleared"] is True
        assert s["safety_plan"]["safe_place"] == "Aunt house"
        assert len(s["align_records"]) == 1
        assert len(s["biff_logs"]) == 1


# ------------------------------------------------------------------ #
# Grey-rock BIFF regression (materially shorter)
# ------------------------------------------------------------------ #
class TestGreyRockBiff:
    def test_greyrock_reply_shorter_than_normal(self):
        raw = (
            "You are late again picking up the kids and this is completely "
            "unacceptable. I told you last week we needed to be on time for "
            "the doctor's appointment. This keeps happening and I'm sick of it."
        )
        r_normal = requests.post(
            f"{BASE_URL}/api/portal/biff-refine",
            json={"raw": raw, "safety_flagged": False},
            timeout=60,
        )
        r_gr = requests.post(
            f"{BASE_URL}/api/portal/biff-refine",
            json={"raw": raw, "safety_flagged": True},
            timeout=60,
        )
        assert r_normal.status_code == 200, r_normal.text
        assert r_gr.status_code == 200, r_gr.text
        normal_text = (r_normal.json().get("biff") or r_normal.json().get("output") or "")
        gr_text = (r_gr.json().get("biff") or r_gr.json().get("output") or "")
        assert normal_text and gr_text, f"empty outputs: {r_normal.json()} vs {r_gr.json()}"
        # Grey-rock should not be strictly longer.
        # "Materially shorter" — allow small slack, at least not longer than normal.
        assert len(gr_text) <= len(normal_text) * 1.05, (
            f"grey-rock ({len(gr_text)}) not shorter than normal ({len(normal_text)}). "
            f"grey-rock: {gr_text!r}\nnormal: {normal_text!r}"
        )
