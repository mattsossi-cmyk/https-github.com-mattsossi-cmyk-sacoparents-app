"""Tests for the updated family-violence professional-request flow (no co-parent
email at request time; professional supplies both parents' emails at prepare)
and the share-report email notification."""
import os
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _reg(role="parent", prefix="fv"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": role,
    })
    assert r.status_code == 200, r.text
    return s, email


def _mk_request(parent, pro_email, with_coparent=True):
    body = {"professional_email": pro_email, "child_name": "FV Kid", "co_parent_name": "Other Parent"}
    if with_coparent:
        body["co_parent_email"] = f"TEST_fvcop_{uuid.uuid4().hex[:8]}@example.com"
    r = parent.post(f"{API}/joint/professional-requests", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


class TestProRequestNoCoParentEmail:
    def test_request_without_coparent_email_succeeds(self):
        parent, _ = _reg()
        pro, pro_email = _reg("professional", "fvpro")
        req_id = _mk_request(parent, pro_email, with_coparent=False)
        mine = parent.get(f"{API}/joint/professional-requests").json()
        match = [r for r in mine if r["id"] == req_id]
        assert match and match[0]["co_parent_email"] is None

    def test_prepare_without_emails_400_when_request_lacks_coparent(self):
        parent, _ = _reg()
        pro, pro_email = _reg("professional", "fvpro")
        req_id = _mk_request(parent, pro_email, with_coparent=False)
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r.status_code == 400, r.text
        assert "email" in r.json()["detail"].lower()

    def test_prepare_with_emails_succeeds(self):
        parent, parent_email = _reg()
        pro, pro_email = _reg("professional", "fvpro")
        req_id = _mk_request(parent, pro_email, with_coparent=False)
        coparent = f"TEST_fvb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare",
                     json={"parent_a_email": parent_email, "parent_b_email": coparent})
        assert r.status_code == 200, r.text
        rid = r.json()["report_id"]
        docs = pro.get(f"{API}/joint/reports").json()
        match = [d for d in docs if d["id"] == rid]
        assert match and match[0]["is_safety"], "safety report should be created for the professional"
        # double prepare still blocked
        r2 = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare",
                      json={"parent_a_email": parent_email, "parent_b_email": coparent})
        assert r2.status_code == 400

    def test_legacy_request_with_coparent_email_prepares_without_body(self):
        parent, _ = _reg()
        pro, pro_email = _reg("professional", "fvpro")
        req_id = _mk_request(parent, pro_email, with_coparent=True)
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r.status_code == 200, r.text


class TestShareEmailsProfessional:
    def test_share_grants_access_and_returns_name(self):
        a, _ = _reg(prefix="sharea")
        b, b_email = _reg(prefix="shareb")
        pro, pro_email = _reg("professional", "sharepro")
        inv = a.post(f"{API}/joint/reports", json={
            "subject": "communication", "child_name": "Share Kid",
            "co_parent_name": "B", "co_parent_email": b_email,
        })
        rid = inv.json()["id"]
        code = inv.json()["invitation"]["code"]
        assert b.post(f"{API}/joint/invitations/accept", json={"code": code}).status_code == 200
        keys = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]
        for s in (a, b):
            r = s.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {k: "consistent routines and calm communication" for k in keys}})
            assert r.status_code == 200, r.text
        # share with the professional (email send is guarded; must not 500)
        r = a.post(f"{API}/joint/reports/{rid}/share", json={"email": pro_email})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        # professional can now see the shared report
        docs = pro.get(f"{API}/joint/reports").json()
        assert any(d["id"] == rid for d in docs), "shared report should appear in professional list"
        # unknown professional still 404
        r2 = a.post(f"{API}/joint/reports/{rid}/share", json={"email": f"TEST_nopro_{uuid.uuid4().hex[:6]}@example.com"})
        assert r2.status_code == 404
