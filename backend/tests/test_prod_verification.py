"""Production + e2e verification suite.

Public checks (health/config/cron auth) run against the production deployment.
Feature flows run against the preview backend, which shares the local database —
casekit approves test professionals directly in Mongo. Production uses an
isolated database and must not be polluted with test accounts, and current
product rules block public parent signup and unapproved-professional case
creation (403 by design), so feature flows cannot run against prod.
"""
import io
import os
import uuid

import requests
from pypdf import PdfReader

from casekit import new_case, new_user, completed_case, CaseSpec

PROD = "https://align-report.emergent.host"
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PROD_API = f"{PROD}/api"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
HDRS = {"User-Agent": UA}

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]
AREA_KEYS = ["parenting_schedule", "holidays", "decision_making", "communication",
             "exchanges", "expenses", "information_sharing", "dispute_resolution"]


def _answers(theme: str = "general") -> dict:
    return {
        "needs_most": f"Our child needs {theme} consistency across both homes.",
        "working_well": f"The {theme} routines are largely stable on weekdays.",
        "concerns": f"I am concerned about {theme} homework follow through.",
        "improve": f"Better {theme} written communication would help us.",
        "options": f"Option A shared calendar. Option B {theme} weekly check-in.",
        "other_parent": f"The other parent likely values {theme} predictability.",
    }


def _assert_two_invitations(data: dict, pa: str, pb: str) -> None:
    invs = data.get("invitations")
    assert invs and len(invs) == 2
    by_role = {i["role"]: i for i in invs}
    assert set(by_role) == {"a", "b"}
    for role, email in (("a", pa), ("b", pb)):
        inv = by_role[role]
        assert inv["invitee_email"] == email.lower()
        assert "/join/" in inv["link"], f"missing /join/ in link: {inv}"
        assert len(inv["code"]) >= 6
    assert by_role["a"]["link"] != by_role["b"]["link"]


# -------------------- 1) Professional share links --------------------
class TestProShareLinks:
    def test_pro_create_returns_two_parent_join_links(self) -> None:
        pro = new_user(API, "professional", "Prod Pro")
        pa = f"t_prodpa_{uuid.uuid4().hex[:8]}@example.com"
        pb = f"t_prodpb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "Prod Kid",
            "parent_a_name": "Ann", "parent_a_email": pa,
            "parent_b_name": "Jordan", "parent_b_email": pb,
        })
        assert r.status_code in (200, 201), r.text
        _assert_two_invitations(r.json(), pa, pb)

    def test_join_route_renders(self) -> None:
        pro = new_user(API, "professional", "Prod Pro2")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "medical", "child_name": "Kid",
            "parent_a_name": "A", "parent_a_email": f"t_ja_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_jb_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code in (200, 201), r.text
        link = r.json()["invitations"][0]["link"]
        page = requests.get(link, headers=HDRS, timeout=15)
        # 200 is what we want; a hard 404 means the route is broken
        assert page.status_code == 200, f"{link} -> {page.status_code}"


# -------------------- 2) Foundation Statements merge --------------------
class TestFoundationMerge:
    def _agreement_with_foundation(self):
        """Professional creates an agreement case; both parents join via invite tokens."""
        pro = new_user(API, "professional", "FS Pro")
        ea = f"t_fsa_{uuid.uuid4().hex[:8]}@example.com"
        eb = f"t_fsb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/agreements", json={
            "child_name": "FS Kid", "parent_a_name": "A", "parent_a_email": ea,
            "parent_b_name": "B", "parent_b_email": eb,
        })
        assert r.status_code in (200, 201), r.text
        d = r.json()
        rid = d["id"]
        toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}
        a = new_user(API, "parent", "FS Parent A", email=ea, invite=toks["a"])
        b = new_user(API, "parent", "FS Parent B", email=eb, invite=toks["b"])
        assert a.post(f"{API}/joint/invitations/accept", json={"code": toks["a"]}).status_code == 200
        assert b.post(f"{API}/joint/invitations/accept", json={"code": toks["b"]}).status_code == 200
        answers = {k: "We share decisions and keep predictable weekly routines." for k in AREA_KEYS}
        ra = a.put(f"{API}/joint/reports/{rid}/responses", json={
            "answers": answers,
            "foundation": [{"title": "My Foundation Statement",
                            "content": "Our daughter needs calm, predictable handoffs above all else."}],
        })
        assert ra.status_code == 200, ra.text
        rb = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        assert rb.status_code == 200, rb.text
        return a, rid

    def test_agreement_report_and_pdf_include_foundation(self) -> None:
        a, rid = self._agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200, r.text
        fs = r.json().get("foundation_statements", [])
        assert len(fs) == 1
        assert "predictable handoffs" in fs[0]["content"]

        r = a.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "Foundation Statements" in text
        assert "predictable handoffs" in text


# -------------------- 3) FV email-less pro request + prepare --------------------
class TestFVEmailless:
    def _parent_and_pro(self, tag: str):
        """Parents exist only via professional invitation; returns (parent_session, pro_session, pro_email)."""
        _pro0, pa, _pb, _d = new_case(API, CaseSpec(subject="education", child=f"FV {tag} Kid"))
        pro = new_user(API, "professional", f"FV Pro {tag}")
        return pa, pro, pro.email

    def test_fv_request_without_coparent_email(self) -> None:
        parent, _pro, pro_email = self._parent_and_pro("one")
        r = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro_email,
            "child_name": "Kid",
        })
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:300]}"

    def _pending_request(self, tag: str) -> tuple:
        parent, pro, pro_email = self._parent_and_pro(tag)
        r = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro_email, "child_name": "Kid",
        })
        assert r.status_code == 200, r.text
        req_id = r.json().get("id") or r.json().get("request_id")
        assert req_id, r.json()
        return parent, pro, req_id

    def test_prepare_empty_body_400(self) -> None:
        _parent, pro, req_id = self._pending_request("two")

        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare", json={})
        assert r.status_code == 400, f"empty prepare should be 400, got {r.status_code} {r.text[:200]}"

    def test_prepare_with_emails_200(self) -> None:
        _parent, pro, req_id = self._pending_request("three")

        pa = f"t_pra_{uuid.uuid4().hex[:6]}@example.com"
        pb = f"t_prb_{uuid.uuid4().hex[:6]}@example.com"
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare", json={
            "parent_a_email": pa, "parent_b_email": pb,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        rid = d.get("report_id") or d.get("id")
        assert rid, d

        # pro can see the safety report in list
        r = pro.get(f"{API}/joint/reports")
        assert r.status_code == 200
        reports = r.json() if isinstance(r.json(), list) else r.json().get("reports", [])
        match = [rep for rep in reports if rep.get("id") == rid]
        assert match, f"safety report {rid} not visible to pro"
        assert match[0].get("is_safety")


# -------------------- 4) Core regression --------------------
class TestCoreRegression:
    def test_health_ok(self) -> None:
        r = requests.get(f"{PROD}/health", headers=HDRS, timeout=15)
        assert r.status_code == 200

    def test_config_has_8_agreement_areas(self) -> None:
        r = requests.get(f"{PROD_API}/joint/config", headers=HDRS, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("agreement_areas", [])) == 8

    def test_cron_completion_nudge_requires_auth(self) -> None:
        r = requests.post(f"{PROD}/api/cron/completion-nudge", headers=HDRS, timeout=15)
        assert r.status_code == 401

    def test_full_joint_cycle_and_pdf(self) -> None:
        pro, pa, pb, d, detail = completed_case(API, subject="education")
        rid = d["id"]
        r = pa.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200, r.text
        r = pa.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1000  # non-blank

    def test_share_to_professional_shows_in_shared_with_me(self) -> None:
        pro, pa, pb, d, detail = completed_case(API, subject="education")
        rid = d["id"]
        other_pro = new_user(API, "professional", "Share Target Pro")
        r = pa.post(f"{API}/joint/reports/{rid}/share", json={"email": other_pro.email})
        assert r.status_code in (200, 201), r.text
        r = other_pro.get(f"{API}/joint/reports")
        assert r.status_code == 200
        reports = r.json() if isinstance(r.json(), list) else r.json().get("reports", [])
        assert any(rep.get("id") == rid for rep in reports), "pro should see shared report"
