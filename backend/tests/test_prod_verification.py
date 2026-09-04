"""Production verification suite against https://align-report.emergent.host.

Covers the four review-request feature sets:
  1) Professional share links return 2 invitations w/ /join/ links
  2) Foundation Statements merge into agreement report + PDF
  3) Family-violence flow: email-less pro request + empty-body prepare 400 +
     valid prepare 200 creates an is_safety report visible to the pro
  4) Core regression: joint report full cycle, /joint/config, cron auth, /health
"""
import io
import os
import uuid
import requests
from pypdf import PdfReader

PROD = "https://align-report.emergent.host"
API = f"{PROD}/api"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
HDRS = {"User-Agent": UA}

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]
AREA_KEYS = ["parenting_schedule", "holidays", "decision_making", "communication",
             "exchanges", "expenses", "information_sharing", "dispute_resolution"]


def _answers(theme="general"):
    return {
        "needs_most": f"Our child needs {theme} consistency across both homes.",
        "working_well": f"The {theme} routines are largely stable on weekdays.",
        "concerns": f"I am concerned about {theme} homework follow through.",
        "improve": f"Better {theme} written communication would help us.",
        "options": f"Option A shared calendar. Option B {theme} weekly check-in.",
        "other_parent": f"The other parent likely values {theme} predictability.",
    }


def _sess():
    s = requests.Session()
    s.headers.update(HDRS)
    return s


def _reg(role="parent", prefix="p", email=None):
    email = email or f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@testmail.dev"
    s = _sess()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": role,
    })
    assert r.status_code == 200, f"register {email}: {r.status_code} {r.text[:300]}"
    return s, email


# -------------------- 1) Professional share links --------------------
class TestProShareLinks:
    def test_pro_create_returns_two_parent_join_links(self):
        pro, _ = _reg("professional", "prodpro")
        pa = f"TEST_prodpa_{uuid.uuid4().hex[:8]}@testmail.dev"
        pb = f"TEST_prodpb_{uuid.uuid4().hex[:8]}@testmail.dev"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "Prod Kid",
            "parent_a_name": "Ann", "parent_a_email": pa,
            "parent_b_name": "Jordan", "parent_b_email": pb,
        })
        assert r.status_code in (200, 201), r.text
        invs = r.json().get("invitations")
        assert invs and len(invs) == 2
        by_role = {i["role"]: i for i in invs}
        assert set(by_role) == {"a", "b"}
        for role, email in (("a", pa), ("b", pb)):
            inv = by_role[role]
            assert inv["invitee_email"] == email.lower()
            assert "/join/" in inv["link"], f"missing /join/ in link: {inv}"
            assert len(inv["code"]) >= 6
        assert by_role["a"]["link"] != by_role["b"]["link"]
        # Both links should target the prod domain (not stale preview)
        assert "align-report.emergent.host" in by_role["a"]["link"] or \
               "align-report" in by_role["a"]["link"], by_role["a"]["link"]

    def test_join_route_renders(self):
        pro, _ = _reg("professional", "prodpro2")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "medical", "child_name": "Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_ja_{uuid.uuid4().hex[:6]}@testmail.dev",
            "parent_b_name": "B", "parent_b_email": f"TEST_jb_{uuid.uuid4().hex[:6]}@testmail.dev",
        })
        link = r.json()["invitations"][0]["link"]
        page = requests.get(link, headers=HDRS, timeout=15)
        # 200 is what we want; a hard 404 means the route is broken
        assert page.status_code == 200, f"{link} -> {page.status_code}"


# -------------------- 2) Foundation Statements merge --------------------
class TestFoundationMerge:
    def _agreement_with_foundation(self):
        a, _ = _reg("parent", "fsa")
        b, b_email = _reg("parent", "fsb")
        inv = a.post(f"{API}/joint/agreements", json={
            "child_name": "FS Kid", "co_parent_name": "B", "co_parent_email": b_email,
        })
        assert inv.status_code in (200, 201), inv.text
        rid = inv.json()["id"]
        code = inv.json()["invitation"]["code"]
        assert b.post(f"{API}/joint/invitations/accept", json={"code": code}).status_code == 200
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

    def test_agreement_report_and_pdf_include_foundation(self):
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
    def test_fv_request_without_coparent_email(self):
        parent, _ = _reg("parent", "fvpa")
        pro, pro_email = _reg("professional", "fvpro")
        r = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro_email,
            "child_name": "Kid",
        })
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:300]}"

    def test_prepare_empty_body_400_then_with_emails_200(self):
        parent, parent_email = _reg("parent", "fvpa2")
        pro, pro_email = _reg("professional", "fvpro2")
        # create request
        r = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro_email, "child_name": "Kid",
        })
        assert r.status_code == 200, r.text
        req_id = r.json().get("id") or r.json().get("request_id")
        assert req_id, r.json()

        # empty body -> 400
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare", json={})
        assert r.status_code == 400, f"empty prepare should be 400, got {r.status_code} {r.text[:200]}"

        # valid prepare
        pa = f"TEST_pra_{uuid.uuid4().hex[:6]}@testmail.dev"
        pb = f"TEST_prb_{uuid.uuid4().hex[:6]}@testmail.dev"
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
        assert match[0].get("is_safety") is True


# -------------------- 4) Core regression --------------------
class TestCoreRegression:
    def test_health_ok(self):
        r = requests.get(f"{PROD}/health", headers=HDRS, timeout=15)
        assert r.status_code == 200

    def test_config_has_8_agreement_areas(self):
        r = requests.get(f"{API}/joint/config", headers=HDRS, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("agreement_areas", [])) == 8

    def test_cron_completion_nudge_requires_auth(self):
        r = requests.post(f"{PROD}/api/cron/completion-nudge", headers=HDRS, timeout=15)
        assert r.status_code == 401

    def test_full_joint_cycle_and_pdf(self):
        a, _ = _reg("parent", "corea")
        b_email = f"TEST_coreb_{uuid.uuid4().hex[:6]}@testmail.dev"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "Kid",
            "co_parent_name": "Bob", "co_parent_email": b_email,
        })
        assert r.status_code in (200, 201), r.text
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]

        b, _ = _reg("parent", "coreb", email=b_email)
        r = b.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r.status_code == 200, r.text

        r = a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("A")})
        assert r.status_code == 200, r.text
        r = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("B")})
        assert r.status_code == 200, r.text

        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        r = a.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1000  # non-blank

    def test_share_to_professional_shows_in_shared_with_me(self):
        a, _ = _reg("parent", "shra")
        b_email = f"TEST_shrb_{uuid.uuid4().hex[:6]}@testmail.dev"
        pro, pro_email = _reg("professional", "shrpro")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "Kid",
            "co_parent_name": "B", "co_parent_email": b_email,
        })
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]
        b, _ = _reg("parent", "shrb", email=b_email)
        b.post(f"{API}/joint/invitations/accept", json={"code": code})
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("A")})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("B")})
        r = a.post(f"{API}/joint/reports/{rid}/share", json={"email": pro_email})
        assert r.status_code in (200, 201), r.text
        r = pro.get(f"{API}/joint/reports")
        assert r.status_code == 200
        reports = r.json() if isinstance(r.json(), list) else r.json().get("reports", [])
        assert any(rep.get("id") == rid for rep in reports), "pro should see shared report"
