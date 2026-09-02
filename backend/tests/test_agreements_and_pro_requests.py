"""Co-Parenting Agreement flow + Professional-Request (family violence) flow tests.

Covers iteration-9 additions:
- POST /api/joint/agreements + config agreement_areas + accept + responses + report + PDF + privacy
- GET /api/professionals, POST/GET /api/joint/professional-requests, .../prepare (403/404/400/200)
- Regression: safety subject without mediator_email still returns 400
"""
import os
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
UA = {"User-Agent": "Mozilla/5.0 (pytest agreement suite)"}

AGREEMENT_KEYS = [
    "parenting_schedule", "holidays", "decision_making", "communication",
    "exchanges", "expenses", "information_sharing", "dispute_resolution",
]


def _reg(role="parent", prefix="p"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@testmail.dev"
    s = requests.Session()
    s.headers.update(UA)
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix.title()}",
        "email": email,
        "password": "testpass123",
        "role": role,
    })
    assert r.status_code == 200, r.text
    s.email = email
    return s, email


def _agreement_answers(prefix, aligned=True):
    """Return 8 answers. If aligned=True, use highly overlapping wording for status=Likely aligned."""
    if aligned:
        return {
            "parenting_schedule": "week on week off schedule with midweek dinner visit",
            "holidays": "alternate holidays annually and share birthdays equally",
            "decision_making": "joint legal decision making for major decisions like school and medical",
            "communication": "written communication weekly via co-parenting app only",
            "exchanges": "exchanges at school or neutral public location on friday",
            "expenses": "share child expenses proportional to income through app",
            "information_sharing": "share school medical activity information within 24 hours",
            "dispute_resolution": "attempt mediation before court for any disputes",
        }
    return {
        "parenting_schedule": f"{prefix} unique schedule proposal alpha",
        "holidays": f"{prefix} unique holiday plan beta",
        "decision_making": f"{prefix} unique decisionmaking gamma",
        "communication": f"{prefix} unique communication delta",
        "exchanges": f"{prefix} unique exchange epsilon",
        "expenses": f"{prefix} unique expenses zeta",
        "information_sharing": f"{prefix} unique info eta",
        "dispute_resolution": f"{prefix} unique dispute theta",
    }


# ------------------- Config -------------------
class TestJointConfig:
    def test_config_returns_8_agreement_areas(self):
        r = requests.get(f"{API}/joint/config", headers=UA)
        assert r.status_code == 200
        data = r.json()
        assert "agreement_areas" in data
        keys = [a["key"] for a in data["agreement_areas"]]
        assert keys == AGREEMENT_KEYS
        for a in data["agreement_areas"]:
            assert a["label"] and a["question"]


# ------------------- Agreement full flow -------------------
class TestAgreementFullFlow:
    def _setup(self):
        a, ea = _reg(prefix="pa")
        b, eb = _reg(prefix="pb")
        # create as A
        r = a.post(f"{API}/joint/agreements", json={
            "child_name": "TEST_Kid",
            "co_parent_name": "Test Pb",
            "co_parent_email": eb,
        })
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("invitation", {}).get("code")
        code = j["invitation"]["code"]
        assert len(code) == 6
        rid = j["id"]
        # accept as B
        r2 = b.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r2.status_code == 200, r2.text
        return a, b, rid

    def test_create_accept_respond_report_pdf(self):
        a, b, rid = self._setup()

        # A submits (aligned wording)
        rA = a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _agreement_answers("a", aligned=True)})
        assert rA.status_code == 200, rA.text

        # After only A submits: privacy - detail view of A must not leak B's (still empty)
        detail_a = a.get(f"{API}/joint/reports/{rid}").json()
        assert "b" not in (detail_a.get("responses") or {}) or not detail_a["responses"].get("b", {}).get("answers")

        # Report not ready yet
        rpt_early = a.get(f"{API}/joint/reports/{rid}/report")
        assert rpt_early.status_code == 400

        # B submits (aligned wording)
        rB = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _agreement_answers("b", aligned=True)})
        assert rB.status_code == 200

        # Report ready
        rpt = a.get(f"{API}/joint/reports/{rid}/report")
        assert rpt.status_code == 200, rpt.text
        data = rpt.json()
        assert data["report_title"] == "Joint Co-Parenting Agreement"
        assert data.get("purpose")
        assert data.get("confidentiality_note")
        terms = data["terms"]
        assert len(terms) == 8
        keys = [t["key"] for t in terms]
        assert keys == AGREEMENT_KEYS
        for t in terms:
            assert t["parent_a"] and t["parent_b"]
            assert t["status"] in {"Likely aligned", "Close", "Needs discussion"}

        # PDF
        pdf = a.get(f"{API}/joint/reports/{rid}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        cd = pdf.headers.get("content-disposition", "")
        assert "coparenting-agreement-" in cd
        assert pdf.content.startswith(b"%PDF")

    def test_privacy_detail_view_hides_partner_answers(self):
        a, b, rid = self._setup()
        # B submits first
        rB = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _agreement_answers("b", aligned=False)})
        assert rB.status_code == 200
        # A's detail view before submitting anything: must NOT contain B's raw answers
        detail_a = a.get(f"{API}/joint/reports/{rid}").json()
        blob = str(detail_a).lower()
        for v in _agreement_answers("b", aligned=False).values():
            assert v.lower() not in blob, f"Partner answer leaked in A's detail view: {v}"


# ------------------- Professionals list + Professional-request flow -------------------
class TestProfessionalRequestFlow:
    def test_full_flow(self):
        parent, parent_email = _reg(prefix="parp")
        parent2, parent2_email = _reg(prefix="parq")
        pro, pro_email = _reg(role="professional", prefix="pro")

        # /api/professionals lists the pro
        pros = parent.get(f"{API}/professionals").json()
        assert any(p["email"] == pro_email.lower() for p in pros)

        # unknown professional -> 404
        r404 = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": f"ghost_{uuid.uuid4().hex[:6]}@testmail.dev",
            "child_name": "TEST_Kid",
            "co_parent_name": "Test Parent Q",
            "co_parent_email": parent2_email,
        })
        assert r404.status_code == 404

        # create request
        rc = parent.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro_email,
            "child_name": "TEST_Kid",
            "co_parent_name": "Test Parent Q",
            "co_parent_email": parent2_email,
        })
        assert rc.status_code == 200, rc.text
        req_id = rc.json()["id"]

        # parent sees it in their list
        my = parent.get(f"{API}/joint/professional-requests").json()
        assert any(x["id"] == req_id for x in my)

        # pro sees it in their inbox
        inbox = pro.get(f"{API}/joint/professional-requests").json()
        assert any(x["id"] == req_id for x in inbox)

        # parent cannot prepare -> 403
        r403 = parent.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r403.status_code == 403

        # professional prepares -> ok + report_id
        rp = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp.status_code == 200, rp.text
        rid = rp.json()["report_id"]
        assert rid

        # calling prepare again -> 400
        rp2 = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp2.status_code == 400

        # pro sees the safety report in their /joint/reports list
        pro_reports = pro.get(f"{API}/joint/reports").json()
        found = [r for r in pro_reports if r["id"] == rid]
        assert len(found) == 1
        rep = found[0]
        assert rep.get("is_safety") is True
        subjects = rep.get("subjects") or []
        assert set(subjects) == {"safety", "risk", "safety_communication", "safeguards"}

        # parents do NOT see it in their list before accepting invitation
        pa_list = parent.get(f"{API}/joint/reports").json()
        assert not any(r["id"] == rid for r in pa_list), "Parent A must not see safety report before accepting invite"
        pb_list = parent2.get(f"{API}/joint/reports").json()
        assert not any(r["id"] == rid for r in pb_list), "Parent B must not see safety report before accepting invite"


# ------------------- Safety without mediator regression -------------------
class TestSafetyRegression:
    def test_safety_without_mediator_still_400(self):
        a, _ = _reg(prefix="reg")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety",
            "child_name": "TEST_Kid",
            "co_parent_name": "B",
            "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@testmail.dev",
        })
        assert r.status_code == 400
        assert "mediator" in r.json()["detail"].lower() or "third-party" in r.json()["detail"].lower()
