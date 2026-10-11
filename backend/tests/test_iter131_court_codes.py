"""Iter131: Court codes created by professionals + Align integration status endpoint + joint cases requested_progress."""
from __future__ import annotations

import os
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
INT_KEY = os.environ["INTEGRATION_SHARED_SECRET"]
P1 = {"email": "parent1@test.com", "password": "TestPass123!"}


def _login(creds):
    r = requests.post(f"{BASE}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _register_fresh():
    ts = int(time.time() * 1000)
    email = f"iter131_{ts}@test.com"
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": "TestPass123!", "name": f"Iter131 {ts}"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


@pytest.fixture(scope="module")
def pro_token():
    return _login(P1)


# ---------- Court code CRUD ----------

class TestCourtCodes:
    def test_auth_required(self):
        r = requests.post(f"{BASE}/professional/court-codes", json={"requested": ["coparent"]}, timeout=20)
        assert r.status_code in (401, 403)

    def test_empty_requested_422(self, pro_token):
        r = requests.post(f"{BASE}/professional/court-codes", json={"requested": []},
                          headers={"Authorization": f"Bearer {pro_token}"}, timeout=20)
        assert r.status_code == 422

    def test_bogus_key_422(self, pro_token):
        r = requests.post(f"{BASE}/professional/court-codes", json={"requested": ["not_a_real_key"]},
                          headers={"Authorization": f"Bearer {pro_token}"}, timeout=20)
        assert r.status_code == 422

    def test_create_list_revoke(self, pro_token):
        H = {"Authorization": f"Bearer {pro_token}"}
        r = requests.post(f"{BASE}/professional/court-codes",
                          json={"label": "TEST_iter131", "requested": ["coparent", "self", "foundation"], "valid_days": 90},
                          headers=H, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["code"].startswith("SAC-") and len(data["code"]) == 13
        assert data["case_id"].startswith("CC-")
        assert set(data["requested"]) == {"coparent", "self", "foundation"}
        assert data["parents"] == []
        case_id = data["case_id"]

        # list — only mine, no key_hash
        r = requests.get(f"{BASE}/professional/court-codes", headers=H, timeout=20)
        assert r.status_code == 200
        codes = r.json()["codes"]
        row = next(c for c in codes if c["case_id"] == case_id)
        assert "key_hash" not in row
        assert row["revoked_at"] is None
        assert row["parents"] == []

        # revoke
        r = requests.post(f"{BASE}/professional/court-codes/{case_id}/revoke", headers=H, timeout=20)
        assert r.status_code == 200
        # second revoke -> 404
        r = requests.post(f"{BASE}/professional/court-codes/{case_id}/revoke", headers=H, timeout=20)
        assert r.status_code == 404
        # someone else's / bogus
        r = requests.post(f"{BASE}/professional/court-codes/CC-NOPE99/revoke", headers=H, timeout=20)
        assert r.status_code == 404

    def test_parent_verify_links_code_and_sees_requested(self, pro_token):
        H = {"Authorization": f"Bearer {pro_token}"}
        r = requests.post(f"{BASE}/professional/court-codes",
                          json={"label": "TEST_link", "requested": ["coparent", "medical"], "valid_days": 60},
                          headers=H, timeout=20)
        assert r.status_code == 200
        code = r.json()["code"]
        case_id = r.json()["case_id"]

        # Fresh parent
        email, p_tok = _register_fresh()
        PH = {"Authorization": f"Bearer {p_tok}"}

        # verify code
        r = requests.post(f"{BASE}/portal/court-keys/verify", json={"key": code}, headers=PH, timeout=20)
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["verified"] is True
        assert v["case_id"] == case_id
        assert v.get("mediator_name")

        # PUT portal state (partial)
        r = requests.put(f"{BASE}/portal/state", json={"court_key": case_id, "court_legal_name": "TEST Iter131 Parent"},
                         headers=PH, timeout=20)
        assert r.status_code == 200

        # GET /court-path/requested
        r = requests.get(f"{BASE}/court-path/requested", headers=PH, timeout=20)
        assert r.status_code == 200
        req = r.json()
        assert set(req.get("keys", [])) >= {"coparent", "medical"}
        assert set(req.get("professional_keys", [])) == {"coparent", "medical"}

        # Pro now sees parent linked
        r = requests.get(f"{BASE}/professional/court-codes", headers=H, timeout=20)
        row = next(c for c in r.json()["codes"] if c["case_id"] == case_id)
        assert len(row["parents"]) == 1
        p = row["parents"][0]
        assert p["name"] == "TEST Iter131 Parent"
        assert {a["key"] for a in p["assessments"]} == {"coparent", "medical"}
        for a in p["assessments"]:
            assert a["status"] in ("done", "in_progress", "todo")
            assert "answers" not in a and "score" not in a

        # revoke -> parent verify sees reason revoked
        r = requests.post(f"{BASE}/professional/court-codes/{case_id}/revoke", headers=H, timeout=20)
        assert r.status_code == 200
        r = requests.post(f"{BASE}/portal/court-keys/verify", json={"key": code}, headers=PH, timeout=20)
        # verify endpoint should indicate not usable; depending on impl: either verified=False with reason, or 200/400
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 200:
            assert j.get("verified") is False
            assert "revok" in str(j.get("reason", "")).lower()
        else:
            # also acceptable: 400/404 explicit error
            assert r.status_code in (400, 404)


# ---------- Align integration status endpoint ----------

class TestAlignIntegration:
    def test_missing_key_401(self):
        r = requests.get(f"{BASE}/integrations/court-keys/ANY/progress", timeout=20)
        assert r.status_code == 401

    def test_wrong_key_401(self):
        r = requests.get(f"{BASE}/integrations/court-keys/ANY/progress",
                         headers={"X-Integration-Key": "wrong"}, timeout=20)
        assert r.status_code == 401

    def test_unknown_case_404(self):
        r = requests.get(f"{BASE}/integrations/court-keys/UNKNOWN-CASE-xyz/progress",
                         headers={"X-Integration-Key": INT_KEY}, timeout=20)
        assert r.status_code == 404

    def test_inapp_code_returns_404_via_integration(self, pro_token):
        H = {"Authorization": f"Bearer {pro_token}"}
        r = requests.post(f"{BASE}/professional/court-codes",
                          json={"requested": ["self"], "valid_days": 30}, headers=H, timeout=20)
        case_id = r.json()["case_id"]
        r = requests.get(f"{BASE}/integrations/court-keys/{case_id}/progress",
                         headers={"X-Integration-Key": INT_KEY}, timeout=20)
        assert r.status_code == 404
        requests.post(f"{BASE}/professional/court-codes/{case_id}/revoke", headers=H, timeout=20)

    def test_align_upsert_then_progress(self):
        ts = int(time.time() * 1000)
        case_id = f"TEST-ALIGN-{ts}"
        key = f"KEY-{ts}"
        r = requests.post(f"{BASE}/integrations/court-keys",
                          json={"key": key, "case_id": case_id, "mediator_name": "TEST Align",
                                "requested": ["coparent", "self"]},
                          headers={"X-Integration-Key": INT_KEY}, timeout=20)
        assert r.status_code == 200, r.text
        assert set(r.json()["requested"]) == {"coparent", "self"}

        r = requests.get(f"{BASE}/integrations/court-keys/{case_id}/progress",
                         headers={"X-Integration-Key": INT_KEY}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["case_id"] == case_id
        assert set(d["requested"]) == {"coparent", "self"}
        assert d["revoked"] is False
        assert d["parents"] == []


# ---------- Joint Alignment: cases-i-created includes requested_progress ----------

class TestJointAlignmentMine:
    def test_requested_progress_present(self, pro_token):
        H = {"Authorization": f"Bearer {pro_token}"}
        r = requests.get(f"{BASE}/professional/joint-alignment/cases-i-created", headers=H, timeout=25)
        assert r.status_code == 200, r.text
        data = r.json()
        cases = data.get("cases") or data if isinstance(data, list) else data.get("cases", [])
        assert isinstance(cases, list), f"unexpected shape: {str(data)[:200]}"
        demo = next((c for c in cases if c.get("case_id") == "SA-DEMO01"), None)
        assert demo is not None, "SA-DEMO01 not found in cases-i-created"
        parents = demo.get("parents") or []
        assert parents, "SA-DEMO01 has no parents"
        # every parent object has requested_progress key (list or None)
        for p in parents:
            assert "requested_progress" in p
            rp = p["requested_progress"]
            assert rp is None or isinstance(rp, list)
            if isinstance(rp, list):
                for row in rp:
                    assert "status" in row and row["status"] in ("done", "in_progress", "todo")
                    assert "answers" not in row and "score" not in row
