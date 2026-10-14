"""Backend tests for iter: Share With Professional, Alert Preferences, Gentle Nudge."""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET", "")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

PARENT1 = ("parent1@test.com", "TestPass123!")
CCALERT = ("ccalert@test.com", "TestPass123!")
CCPARENT = ("ccparent@test.com", "TestPass123!")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def tok_parent1():
    return _login(*PARENT1)


@pytest.fixture(scope="module")
def tok_ccalert():
    return _login(*CCALERT)


@pytest.fixture(scope="module")
def tok_ccparent():
    return _login(*CCPARENT)


# ---------- Share With Professional: recipients ----------
class TestRecipients:
    def test_ccalert_recipients(self, tok_ccalert):
        r = requests.get(f"{BASE_URL}/api/court-path/completion-summary/recipients", headers=_h(tok_ccalert), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # Must NOT contain emails
        assert "professionals" in data and "can_type_email" in data
        for p in data["professionals"]:
            assert set(p.keys()) == {"ref", "name"}, f"leaked field in {p}"
        refs = [p["ref"] for p in data["professionals"]]
        assert "CC-AKDYZ5" in refs
        pro = next(p for p in data["professionals"] if p["ref"] == "CC-AKDYZ5")
        assert pro["name"] == "Sam Parent"
        assert data["can_type_email"] is False

    def test_align_code_parent_can_type_email(self, db):
        # Create an Align-made court code via integration
        case_id = f"ALIGN-TEST-{uuid.uuid4().hex[:6].upper()}"
        key = f"alignkey-{uuid.uuid4().hex[:12]}"
        r = requests.post(
            f"{BASE_URL}/api/integrations/court-keys",
            headers={"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"},
            json={"key": key, "case_id": case_id, "mediator_name": "Align Mediator",
                  "requested": ["foundation"]},
            timeout=20,
        )
        assert r.status_code == 200, r.text

        # Confirm Align-made (no created_by)
        doc = db.portal_court_keys.find_one({"case_id": case_id})
        assert doc and "created_by" not in doc

        # Register fresh parent
        email = f"TEST_align_{uuid.uuid4().hex[:8]}@test.com"
        rr = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"email": email, "password": "TestPass123!", "name": "TEST Align Parent"},
                           timeout=20)
        assert rr.status_code in (200, 201), rr.text
        tok = rr.json()["access_token"]

        # Verify + link
        v = requests.post(f"{BASE_URL}/api/portal/court-keys/verify", json={"key": key}, timeout=20)
        assert v.status_code == 200 and v.json().get("verified")
        s = requests.put(f"{BASE_URL}/api/portal/state", headers=_h(tok),
                         json={"court_key": case_id}, timeout=20)
        assert s.status_code == 200, s.text

        r2 = requests.get(f"{BASE_URL}/api/court-path/completion-summary/recipients", headers=_h(tok), timeout=20)
        assert r2.status_code == 200
        data = r2.json()
        assert data["can_type_email"] is True

    def test_no_professional_can_type_email(self):
        email = f"TEST_nopro_{uuid.uuid4().hex[:8]}@test.com"
        rr = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"email": email, "password": "TestPass123!", "name": "TEST No Pro"},
                           timeout=20)
        assert rr.status_code in (200, 201)
        tok = rr.json()["access_token"]
        r = requests.get(f"{BASE_URL}/api/court-path/completion-summary/recipients", headers=_h(tok), timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["professionals"] == []
        assert data["can_type_email"] is True


# ---------- Share With Professional: send ----------
class TestSendSummary:
    def test_unknown_ref_404(self, tok_ccalert):
        r = requests.post(f"{BASE_URL}/api/court-path/completion-summary/send",
                          headers=_h(tok_ccalert), json={"ref": "CC-NOPE999"}, timeout=20)
        assert r.status_code == 404

    def test_typed_email_rejected_when_not_allowed(self, tok_ccalert):
        r = requests.post(f"{BASE_URL}/api/court-path/completion-summary/send",
                          headers=_h(tok_ccalert), json={"email": "someone@test.com"}, timeout=20)
        assert r.status_code == 422

    def test_invalid_email(self, tok_ccalert):
        r = requests.post(f"{BASE_URL}/api/court-path/completion-summary/send",
                          headers=_h(tok_ccalert), json={"email": "not-an-email"}, timeout=20)
        assert r.status_code == 422

    def test_not_all_done_409(self, tok_ccparent):
        r = requests.post(f"{BASE_URL}/api/court-path/completion-summary/send",
                          headers=_h(tok_ccparent), json={"ref": "CC-P445YM"}, timeout=20)
        # Could be 409 (unfinished) or 404 (not an owned ref for them). Should be 409 per spec.
        assert r.status_code == 409, f"got {r.status_code}: {r.text}"

    def test_known_ref_send_creates_secure_doc_and_429_cap(self, tok_ccalert, db):
        # ccalert has used 1 today; up to send 5. Then 6th -> 429
        statuses = []
        before = db.secure_documents.count_documents({"label": "Completion summary",
                                                      "recipient_email": "parent1@test.com"})
        for _ in range(5):
            r = requests.post(f"{BASE_URL}/api/court-path/completion-summary/send",
                              headers=_h(tok_ccalert), json={"ref": "CC-AKDYZ5"}, timeout=30)
            statuses.append(r.status_code)
            if r.status_code == 200:
                data = r.json()
                assert data["ok"] is True and data["sent_to"] == "Sam Parent"
            if r.status_code == 429:
                break
        # Expect at least one 429 within these calls (6th in day)
        assert 429 in statuses, f"expected 429 cap, got {statuses}"
        # Any successful send must have created a secure_documents record
        after = db.secure_documents.count_documents({"label": "Completion summary",
                                                     "recipient_email": "parent1@test.com"})
        if 200 in statuses:
            assert after > before, "secure_documents record not created on 200"


# ---------- Alert Preferences ----------
class TestAlertPrefs:
    def test_parent1_eligible(self, tok_parent1):
        r = requests.get(f"{BASE_URL}/api/professional/completion-alerts", headers=_h(tok_parent1), timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["eligible"] is True
        assert "enabled" in data

    def test_ccparent_not_eligible(self, tok_ccparent):
        r = requests.get(f"{BASE_URL}/api/professional/completion-alerts", headers=_h(tok_ccparent), timeout=20)
        assert r.status_code == 200
        assert r.json()["eligible"] is False

    def test_toggle_persist_and_restore(self, tok_parent1):
        # Off
        r = requests.put(f"{BASE_URL}/api/professional/completion-alerts", headers=_h(tok_parent1),
                         json={"enabled": False}, timeout=20)
        assert r.status_code == 200 and r.json()["enabled"] is False
        g = requests.get(f"{BASE_URL}/api/professional/completion-alerts", headers=_h(tok_parent1), timeout=20)
        assert g.json()["enabled"] is False
        # Restore
        r2 = requests.put(f"{BASE_URL}/api/professional/completion-alerts", headers=_h(tok_parent1),
                          json={"enabled": True}, timeout=20)
        assert r2.status_code == 200 and r2.json()["enabled"] is True


# ---------- Gentle Nudge ----------
class TestNudge:
    def test_not_owner_404(self, tok_ccparent):
        # ccparent is not a professional owner
        r = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_ccparent),
                          json={"ref": "CC-AKDYZ5", "pid": "abc123def456"}, timeout=20)
        assert r.status_code == 404

    def test_bad_pid_404(self, tok_parent1):
        r = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_parent1),
                          json={"ref": "CC-P445YM", "pid": "doesnotexist1"}, timeout=20)
        assert r.status_code == 404

    def test_parent_all_done_409(self, tok_parent1):
        # Get pid for ccalert (all done) on CC-AKDYZ5
        r = requests.get(f"{BASE_URL}/api/professional/court-codes", headers=_h(tok_parent1), timeout=20)
        assert r.status_code == 200
        codes = r.json()
        row = next((c for c in (codes if isinstance(codes, list) else codes.get("codes", []))
                    if c.get("case_id") == "CC-AKDYZ5"), None)
        assert row, f"CC-AKDYZ5 not in {codes}"
        parents = row.get("parents") or []
        pid = parents[0]["pid"] if parents else None
        assert pid
        r2 = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_parent1),
                           json={"ref": "CC-AKDYZ5", "pid": pid}, timeout=20)
        assert r2.status_code == 409

    def test_already_nudged_ccparent_429_or_200_suppressed(self, tok_parent1, db):
        # ccparent on CC-P445YM already nudged (suppressed_safety) per context -> expect 429
        r = requests.get(f"{BASE_URL}/api/professional/court-codes", headers=_h(tok_parent1), timeout=20)
        codes = r.json()
        row = next((c for c in (codes if isinstance(codes, list) else codes.get("codes", []))
                    if c.get("case_id") == "CC-P445YM"), None)
        assert row
        parents = row.get("parents") or []
        pid = parents[0]["pid"] if parents else None
        assert pid
        r2 = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_parent1),
                           json={"ref": "CC-P445YM", "pid": pid}, timeout=20)
        assert r2.status_code == 429, f"expected 429 already-nudged, got {r2.status_code} {r2.text}"
        # Also verify suppressed_safety record exists
        rec = db.professional_nudges.find_one({"ref": "CC-P445YM"}, sort=[("sent_at", -1)])
        assert rec and rec["status"] == "suppressed_safety"

    def test_fresh_happy_path_safety_suppressed(self, tok_parent1, db):
        """Create a fresh court code owned by parent1, link a fresh parent (not safety-flagged), and nudge.
        Resend returns 429."""
        r = requests.post(f"{BASE_URL}/api/professional/court-codes", headers=_h(tok_parent1),
                          json={"label": "TEST nudge case", "requested": ["foundation"], "valid_days": 30},
                          timeout=20)
        if r.status_code not in (200, 201):
            pytest.skip(f"cannot create pro code: {r.status_code} {r.text}")
        payload = r.json()
        key = payload.get("code")
        case_id = payload.get("case_id")
        assert key and case_id, payload

        # Register fresh parent + link
        email = f"TEST_nudge_{uuid.uuid4().hex[:8]}@test.com"
        rr = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"email": email, "password": "TestPass123!", "name": "TEST Nudge Parent"},
                           timeout=20)
        assert rr.status_code in (200, 201)
        tok = rr.json()["access_token"]
        v = requests.post(f"{BASE_URL}/api/portal/court-keys/verify", json={"key": key}, timeout=20)
        assert v.json().get("verified")
        requests.put(f"{BASE_URL}/api/portal/state", headers=_h(tok),
                     json={"court_key": case_id}, timeout=20)

        # Now fetch pid
        rc = requests.get(f"{BASE_URL}/api/professional/court-codes", headers=_h(tok_parent1), timeout=20)
        codes = rc.json()
        row = next((c for c in (codes if isinstance(codes, list) else codes.get("codes", []))
                    if c.get("case_id") == case_id), None)
        assert row, f"created case {case_id} not visible"
        parents = row.get("parents") or []
        assert parents, "parent not linked"
        pid = parents[0]["pid"]

        # First nudge -> 200 (or 502 preview email env limit)
        r1 = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_parent1),
                           json={"ref": case_id, "pid": pid}, timeout=30)
        assert r1.status_code in (200, 502), f"first nudge: {r1.status_code} {r1.text}"
        if r1.status_code == 200:
            assert "next_at" in r1.json()
            # Second within 7d -> 429
            r2 = requests.post(f"{BASE_URL}/api/professional/nudges", headers=_h(tok_parent1),
                               json={"ref": case_id, "pid": pid}, timeout=20)
            assert r2.status_code == 429
            # List shows nudge_next_at
            rc2 = requests.get(f"{BASE_URL}/api/professional/court-codes", headers=_h(tok_parent1), timeout=20)
            codes2 = rc2.json()
            row2 = next(c for c in (codes2 if isinstance(codes2, list) else codes2.get("codes", []))
                        if c.get("case_id") == case_id)
            assert row2["parents"][0].get("nudge_next_at")
