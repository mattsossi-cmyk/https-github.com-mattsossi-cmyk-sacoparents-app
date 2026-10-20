"""Iter73 tests — Grey-rock BIFF variant + Safety Plan delete round-trip.

Covers:
  - POST /api/portal/biff-refine with safety_flagged=true returns same JSON shape
    ({biff, flags, risk}) as default flow.
  - Grey-rock biff response is shorter and lacks warm openers vs default.
  - safety_flagged accepts bool; missing defaults to false; string is rejected.
  - PUT /api/portal/state with safety_plan=null accepted, GET returns None
    (delete round-trip).
"""
import os
import re
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

from ai_ready import ai_headers  # noqa: E402

_AI = {}


def _ai():
    """Signed in with the AI notice accepted (AI endpoints need both)."""
    if not _AI:
        _AI.update(ai_headers(f"{BASE_URL}/api"))
    return _AI

PARENT1 = {"email": "parent1@test.com", "password": "TestPass123!"}

RAW_DRAFT = "You are always late for pickups and I am sick of your excuses"

WARM_OPENERS = ["thank you", "thanks", "i appreciate", "i understand"]


# --- helpers ---
def _login_or_register(creds, name="Sam Parent"):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r.status_code == 200:
        return r.json().get("access_token") or r.json().get("token")
    reg = requests.post(
        f"{API}/auth/register", json={**creds, "name": name}, timeout=15
    )
    if reg.status_code == 200:
        return reg.json().get("access_token") or reg.json().get("token")
    r2 = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r2.status_code == 200:
        return r2.json().get("access_token") or r2.json().get("token")
    return None


def _headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _base_payload():
    return {
        "align_records": [],
        "milestones": [],
        "biff_logs": [],
        "foundation_text": "",
        "legal_report": {"sigA": "", "sigB": "", "sigMed": ""},
        "health_index": {"s1": 5, "s2": 5, "s3": 5},
        "court_key": "",
        "reassessments": [],
    }


# --- BIFF refine grey-rock ---
class TestBiffRefineGreyRock:
    def test_default_flow_returns_shape(self):
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "biff" in data and isinstance(data["biff"], str)
        assert "flags" in data and isinstance(data["flags"], list)
        assert "risk" in data
        assert data["risk"] in ("Escalation Flag", "Low Risk")
        assert len(data["biff"]) > 0

    def test_safety_flagged_true_returns_shape(self):
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT, "safety_flagged": True},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(["biff", "flags", "risk"]).issubset(data.keys())
        assert isinstance(data["biff"], str) and len(data["biff"]) > 0
        assert isinstance(data["flags"], list)
        assert data["risk"] in ("Escalation Flag", "Low Risk")

    def test_greyrock_shorter_and_lacks_warmth(self):
        r_default = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT, "safety_flagged": False},
            timeout=60,
        )
        r_grey = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT, "safety_flagged": True},
            timeout=60,
        )
        assert r_default.status_code == 200
        assert r_grey.status_code == 200
        biff_default = r_default.json()["biff"]
        biff_grey = r_grey.json()["biff"]

        # Grey-rock text should be materially shorter (allow generous slack)
        assert len(biff_grey) < len(biff_default), (
            f"Expected grey-rock shorter than default. "
            f"default={len(biff_default)} grey={len(biff_grey)}\n"
            f"default: {biff_default!r}\n"
            f"grey: {biff_grey!r}"
        )

        # Grey-rock should lack warm openers
        low = biff_grey.lower()
        for opener in WARM_OPENERS:
            assert opener not in low, (
                f"Grey-rock reply should not contain warm opener {opener!r}: "
                f"{biff_grey!r}"
            )

    def test_missing_field_defaults_to_false(self):
        # No safety_flagged in body — should behave like default flow.
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert "biff" in data

    def test_string_true_rejected(self):
        # Pydantic v2 default coerces "true"/"false" strings into bool; but
        # the review request expects rejection. Accept either 422 OR a 200
        # (documented lax behaviour) and log — HARD assertion is 422.
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": RAW_DRAFT, "safety_flagged": "not-a-bool"},
            timeout=60,
        )
        # Truly invalid non-bool-ish strings must 422
        assert r.status_code == 422, f"Expected 422 for non-bool string, got {r.status_code}: {r.text}"

    def test_empty_raw_rejected(self):
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": "", "safety_flagged": True},
            timeout=15,
        )
        assert r.status_code == 422


# --- Delete round trip on portal state ---
class TestSafetyPlanDelete:
    @classmethod
    def setup_class(cls):
        cls.tok = _login_or_register(PARENT1, "Sam Parent")
        assert cls.tok, "Could not obtain parent1 token"

    def test_old_safety_plan_is_never_written_or_returned(self):
        # The in-app safety screen is off: the old plan stays as saved and portal state never writes or returns it.
        payload = _base_payload()
        payload["safety_plan"] = {"safe_place": "Aunt Mary's"}
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        assert g.status_code == 200 and "safety_plan" not in g.json()["state"]
        payload["safety_plan"] = None
        assert requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15).status_code == 200
        assert "safety_plan" not in requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15).json()["state"]
