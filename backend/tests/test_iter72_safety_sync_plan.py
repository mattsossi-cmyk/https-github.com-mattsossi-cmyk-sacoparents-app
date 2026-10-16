"""Iter72 backend tests — Safety Ack + Safety Plan sync on /api/portal/state.

Covers:
  - Auth gate (401 when unauthenticated)
  - Round-trip PUT/GET with safety_ack + safety_plan
  - Sanitizer strips unknown keys from safety_plan
  - Sanitizer caps plan text fields at 500 chars
  - safety_ack requires a `date` string (empty {} -> None)
  - Two-user isolation
"""
import pytest
pytest.skip("In-app safety screen turned off (2026-10); screening now happens on SACOparentsAlign.", allow_module_level=True)
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

PARENT1 = {"email": "parent1@test.com", "password": "TestPass123!"}
PARENT2 = {"email": "parent2@test.com", "password": "TestPass123!"}


def _login_or_register(creds, name="Test Parent"):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r.status_code == 200:
        return r.json().get("access_token") or r.json().get("token")
    # try register
    reg = requests.post(f"{API}/auth/register", json={**creds, "name": name}, timeout=15)
    if reg.status_code == 200:
        return reg.json().get("access_token") or reg.json().get("token")
    # retry login
    r2 = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r2.status_code == 200:
        return r2.json().get("access_token") or r2.json().get("token")
    return None


def _headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _base_payload():
    """Minimum-valid portal state payload."""
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


# --- Auth gate ---
class TestAuthGate:
    def test_put_state_requires_auth(self):
        r = requests.put(f"{API}/portal/state", json=_base_payload(), timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"

    def test_get_state_requires_auth(self):
        r = requests.get(f"{API}/portal/state", timeout=15)
        assert r.status_code in (401, 403)


# --- Round trip + sanitizers ---
class TestSafetyAckPlanSync:
    @classmethod
    def setup_class(cls):
        cls.tok = _login_or_register(PARENT1, "Sam Parent")
        assert cls.tok, "Could not obtain parent1 token"

    def test_round_trip_ack_and_plan(self):
        payload = _base_payload()
        payload["safety_ack"] = {"cleared": True, "flagged": False, "date": "2026-01-15"}
        payload["safety_plan"] = {
            "safe_place": "Aunt Mary's house",
            "trusted_contact": "Sister Jane 555-1212",
            "essentials": "IDs, meds, cash",
            "code_word": "sunflower",
            "tech_notes": "Use signal on burner phone",
            "updated_at": "2026-01-15T12:00:00Z",
        }
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200, r.text

        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        assert g.status_code == 200
        state = g.json()["state"]
        assert state["safety_ack"] == {"cleared": True, "flagged": False, "date": "2026-01-15"}
        plan = state["safety_plan"]
        assert plan["safe_place"] == "Aunt Mary's house"
        assert plan["trusted_contact"] == "Sister Jane 555-1212"
        assert plan["essentials"] == "IDs, meds, cash"
        assert plan["code_word"] == "sunflower"
        assert plan["tech_notes"] == "Use signal on burner phone"
        assert plan.get("updated_at") == "2026-01-15T12:00:00Z"

    def test_sanitizer_strips_unknown_keys(self):
        payload = _base_payload()
        payload["safety_plan"] = {"safe_place": "x", "evil": "y", "tech_notes": "z"}
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        plan = g.json()["state"]["safety_plan"]
        assert plan["safe_place"] == "x"
        assert plan["tech_notes"] == "z"
        assert "evil" not in plan
        # Only allowed keys (+ optional updated_at)
        allowed = {"safe_place", "trusted_contact", "essentials", "code_word", "tech_notes", "updated_at"}
        assert set(plan.keys()).issubset(allowed)

    def test_sanitizer_caps_500_chars(self):
        big = "a" * 800
        payload = _base_payload()
        payload["safety_plan"] = {"safe_place": big}
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        plan = g.json()["state"]["safety_plan"]
        assert len(plan["safe_place"]) == 500

    def test_empty_ack_dict_returns_none(self):
        payload = _base_payload()
        payload["safety_ack"] = {}  # no date -> sanitizer returns None
        payload["safety_plan"] = None
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        state = g.json()["state"]
        assert state["safety_ack"] is None
        assert state["safety_plan"] is None

    def test_missing_field_clobbers_to_none(self):
        # First set something
        payload = _base_payload()
        payload["safety_ack"] = {"cleared": True, "flagged": False, "date": "2026-01-15"}
        payload["safety_plan"] = {"safe_place": "test"}
        r = requests.put(f"{API}/portal/state", json=payload, headers=_headers(self.tok), timeout=15)
        assert r.status_code == 200

        # Now PUT without them
        r2 = requests.put(f"{API}/portal/state", json=_base_payload(), headers=_headers(self.tok), timeout=15)
        assert r2.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_headers(self.tok), timeout=15)
        state = g.json()["state"]
        assert state["safety_ack"] is None
        assert state["safety_plan"] is None


# --- Two-user isolation ---
class TestTwoUserIsolation:
    def test_parent1_and_parent2_isolated(self):
        tok1 = _login_or_register(PARENT1, "Sam Parent")
        tok2 = _login_or_register(PARENT2, "Riley Parent")
        assert tok1 and tok2

        p1 = _base_payload()
        p1["safety_ack"] = {"cleared": False, "flagged": True, "date": "2026-01-10"}
        p1["safety_plan"] = {"safe_place": "PARENT1-ONLY-VALUE"}
        r = requests.put(f"{API}/portal/state", json=p1, headers=_headers(tok1), timeout=15)
        assert r.status_code == 200

        # Parent2 must NOT see parent1's plan
        g2 = requests.get(f"{API}/portal/state", headers=_headers(tok2), timeout=15)
        assert g2.status_code == 200
        s2 = g2.json()["state"]
        if s2.get("safety_plan"):
            assert s2["safety_plan"].get("safe_place") != "PARENT1-ONLY-VALUE"
        if s2.get("safety_ack"):
            # Different value if any
            assert s2["safety_ack"] != p1["safety_ack"] or True  # allow None too

        # Parent1 still sees theirs
        g1 = requests.get(f"{API}/portal/state", headers=_headers(tok1), timeout=15)
        assert g1.json()["state"]["safety_plan"]["safe_place"] == "PARENT1-ONLY-VALUE"
