"""Tests for the updated family-violence professional-request flow (no co-parent
email at request time; professional supplies both parents' emails at prepare)
and the share-report email notification. Parents are created via invitations
(professional-initiated model)."""
import os
import uuid
import requests

from casekit import new_user, new_case, completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _pro(prefix="fv"):
    return new_user(API, "professional", f"Pro {prefix}")


def _parent():
    """A registered parent account (created through a real invitation)."""
    pro, pa, pb, d = new_case(API)
    return pa


def _mk_request(parent, pro_email, with_coparent=True):
    body = {"professional_email": pro_email, "child_name": "FV Kid", "co_parent_name": "Other Parent"}
    if with_coparent:
        body["co_parent_email"] = f"TEST_fvcop_{uuid.uuid4().hex[:8]}@example.com"
    r = parent.post(f"{API}/joint/professional-requests", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


class TestProRequestNoCoParentEmail:
    def test_request_without_coparent_email_succeeds(self):
        parent = _parent()
        pro = _pro("fvpro")
        req_id = _mk_request(parent, pro.email, with_coparent=False)
        mine = parent.get(f"{API}/joint/professional-requests").json()
        match = [r for r in mine if r["id"] == req_id]
        assert match and match[0]["co_parent_email"] is None

    def test_prepare_without_emails_400_when_request_lacks_coparent(self):
        parent = _parent()
        pro = _pro("fvpro")
        req_id = _mk_request(parent, pro.email, with_coparent=False)
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r.status_code == 400, r.text
        assert "email" in r.json()["detail"].lower()

    def test_prepare_with_emails_succeeds(self):
        parent = _parent()
        pro = _pro("fvpro")
        req_id = _mk_request(parent, pro.email, with_coparent=False)
        coparent = f"TEST_fvb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare",
                     json={"parent_a_email": parent.email, "parent_b_email": coparent})
        assert r.status_code == 200, r.text
        rid = r.json()["report_id"]
        docs = pro.get(f"{API}/joint/reports").json()
        match = [d for d in docs if d["id"] == rid]
        assert match and match[0]["is_safety"], "safety report should be created for the professional"
        r2 = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare",
                      json={"parent_a_email": parent.email, "parent_b_email": coparent})
        assert r2.status_code == 400

    def test_legacy_request_with_coparent_email_prepares_without_body(self):
        parent = _parent()
        pro = _pro("fvpro")
        req_id = _mk_request(parent, pro.email, with_coparent=True)
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r.status_code == 200, r.text


class TestShareEmailsProfessional:
    def test_share_grants_access_and_returns_name(self):
        pro1, a, b, d, detail = completed_case(API, subject="communication")
        rid = d["id"]
        pro2 = _pro("sharepro")
        r = a.post(f"{API}/joint/reports/{rid}/share", json={"email": pro2.email})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        docs = pro2.get(f"{API}/joint/reports").json()
        assert any(x["id"] == rid for x in docs), "shared report should appear in professional list"
        r2 = a.post(f"{API}/joint/reports/{rid}/share", json={"email": f"TEST_nopro_{uuid.uuid4().hex[:6]}@example.com"})
        assert r2.status_code == 404
