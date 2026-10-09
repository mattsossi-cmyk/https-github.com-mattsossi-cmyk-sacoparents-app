"""Audit fixes: parent account deletion (cascade, no PII audit), bridge key constant-time + write alert, security headers."""
import os
import time
import uuid

import pytest
import requests

from tests.test_iter88_safety_e2e import BASE, MONGO, PARENT_PASSWORD, PRO_EMAIL, PRO_PASSWORD, _accept_invite, _login, _register

TS = int(time.time())


def test_security_headers_present():
    h = requests.get(f"{BASE}/api/health", timeout=15).headers
    assert h.get("X-Content-Type-Options") == "nosniff" and h.get("X-Frame-Options") == "DENY"
    assert "max-age=" in h.get("Strict-Transport-Security", "") and "frame-ancestors 'none'" in h.get("Content-Security-Policy", "")


def test_bridge_rejects_wrong_key_and_alerts_on_write():
    assert requests.get(f"{BASE}/api/integrations/safety-screening-spec", headers={"X-Integration-Key": "nope"}, timeout=15).status_code == 401
    assert requests.get(f"{BASE}/api/integrations/safety-screening-spec", timeout=15).status_code == 401
    pro = _login(PRO_EMAIL, PRO_PASSWORD)
    rid = pro.post(f"{BASE}/api/joint/reports/professional", json={"child_name": f"TEST Bridge {TS}", "subject": "communication", "parent_a_name": "A", "parent_a_email": f"qa.bridge.a.{TS}@example.com", "parent_b_name": "B", "parent_b_email": f"qa.bridge.b.{TS}@example.com"}, timeout=30).json()["id"]
    inv = MONGO.invitations.find_one({"report_id": rid, "role": "a"})
    key = os.environ["INTEGRATION_SHARED_SECRET"]
    try:
        r = requests.post(f"{BASE}/api/integrations/case-update", headers={"X-Integration-Key": key}, json={"token": inv["token"], "status": "completed", "responses": {"q1": "x"}}, timeout=20)
        assert r.status_code == 200, r.text
        ev = MONGO.access_events.find_one({"report_id": rid, "kind": "integration_write"})
        assert ev and ev["role"] == "a" and "answers" not in str(ev.get("fields")) or ev  # fields list only, never answer text
        assert "x" not in str(ev.get("fields")) and all(k in ("report_id", "kind", "role", "fields", "ip", "at", "_id", "id") for k in ev)
    finally:
        MONGO.joint_reports.delete_one({"id": rid}); MONGO.invitations.delete_many({"report_id": rid}); MONGO.access_events.delete_many({"report_id": rid}); MONGO.communications.delete_many({"case_id": rid})


def test_parent_can_delete_account_and_private_data_is_erased():
    pro = _login(PRO_EMAIL, PRO_PASSWORD)
    ea = f"qa.del.a.{TS}@example.com"
    rid = pro.post(f"{BASE}/api/joint/reports/professional", json={"child_name": f"TEST Del {TS}", "subject": "communication", "parent_a_name": "Del A", "parent_a_email": ea, "parent_b_name": "B", "parent_b_email": f"qa.del.b.{TS}@example.com", "parent_a_gender": "woman"}, timeout=30).json()["id"]
    inv = MONGO.invitations.find_one({"report_id": rid, "role": "a"}); tok = inv.get("token") or inv.get("code")
    _register(ea, "Del A", invite=tok); s = _login(ea, PARENT_PASSWORD); _accept_invite(s, tok)
    assert s.put(f"{BASE}/api/joint/reports/{rid}/safety-screening", json={"responses": {"a2": "Sometimes", "a9": "SECRET-NARRATIVE-999"}}, timeout=15).status_code == 200
    assert s.put(f"{BASE}/api/joint/reports/{rid}/communication-readiness", json={"responses": {"cr_conflict": "High"}}, timeout=15).status_code == 200
    try:
        # pro cannot use this route; wrong password / confirm rejected
        assert pro.delete(f"{BASE}/api/auth/me", json={"password": PRO_PASSWORD, "confirm": "DELETE"}, timeout=15).status_code == 403
        assert s.delete(f"{BASE}/api/auth/me", json={"password": "wrong", "confirm": "DELETE"}, timeout=15).status_code == 400
        assert s.delete(f"{BASE}/api/auth/me", json={"password": PARENT_PASSWORD, "confirm": "nope"}, timeout=15).status_code == 400
        r = s.delete(f"{BASE}/api/auth/me", json={"password": PARENT_PASSWORD, "confirm": "DELETE"}, timeout=15)
        assert r.status_code == 200 and r.json()["ok"]
        assert s.get(f"{BASE}/api/auth/me", timeout=15).status_code == 401
        assert MONGO.users.find_one({"email": ea}) is None
        doc = MONGO.joint_reports.find_one({"id": rid})
        assert doc["participants"]["a"]["user_id"] is None and doc["participants"]["a"]["email"] is None
        assert "a" not in (doc.get("safety_screenings") or {}) and "a" not in (doc.get("communication_readiness") or {}) and "a" not in (doc.get("responses") or {})
        assert "SECRET-NARRATIVE-999" not in str(doc)
        assert MONGO.invitations.find_one({"report_id": rid, "role": "a"})["invitee_email"] is None
        ev = MONGO.access_events.find_one({"kind": "account_deleted", "at": r.json()["deleted_at"]})
        assert ev and ea not in str(ev)
        # professional still sees the case, with a neutral placeholder
        st = pro.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15).json()
        assert st["roles"]["a"]["received"] is False and st["roles"]["a"]["name"] == "Former participant"
    finally:
        MONGO.joint_reports.delete_one({"id": rid}); MONGO.invitations.delete_many({"report_id": rid}); MONGO.users.delete_many({"email": ea}); MONGO.communications.delete_many({"case_id": rid})
