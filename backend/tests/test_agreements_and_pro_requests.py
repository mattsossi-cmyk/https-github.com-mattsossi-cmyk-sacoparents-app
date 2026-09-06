"""Co-Parenting Agreement flow + Professional-Request (family violence) flow tests.

Professional-initiated model: agreements are created by professionals with both
parents' emails; parents register through their secure invitations.
"""
import os
import uuid
import requests

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
UA = {"User-Agent": "Mozilla/5.0 (pytest agreement suite)"}

AGREEMENT_KEYS = [
    "parenting_schedule", "holidays", "decision_making", "communication",
    "exchanges", "expenses", "information_sharing", "dispute_resolution",
]


def _pro(prefix="p"):
    return new_user(API, "professional", f"Pro {prefix}")


def _agreement_setup(child="TEST_Kid"):
    """Professional creates an agreement case; both parents register + accept."""
    pro = _pro("agr")
    ea = f"TEST_pa_{uuid.uuid4().hex[:10]}@testmail.dev"
    eb = f"TEST_pb_{uuid.uuid4().hex[:10]}@testmail.dev"
    r = pro.post(f"{API}/joint/agreements", json={
        "child_name": child,
        "parent_a_name": "Test Pa", "parent_a_email": ea,
        "parent_b_name": "Test Pb", "parent_b_email": eb,
    }, headers=UA)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("case_code", "").startswith("SA-AGR-")
    toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}
    a = new_user(API, "parent", "Test Pa", email=ea, invite=toks["a"])
    b = new_user(API, "parent", "Test Pb", email=eb, invite=toks["b"])
    for s, tok in ((a, toks["a"]), (b, toks["b"])):
        r = s.post(f"{API}/joint/invitations/accept", json={"code": tok})
        assert r.status_code == 200, r.text
    return pro, a, b, d["id"]


def _agreement_answers(prefix, aligned=True):
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


def _submit_agreement(session, rid: str, side: str, aligned: bool = True) -> None:
    r = session.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _agreement_answers(side, aligned=aligned)})
    assert r.status_code == 200, r.text


def _assert_agreement_report(data: dict) -> None:
    assert data["report_title"] == "Joint Co-Parenting Agreement"
    assert data.get("purpose")
    assert data.get("confidentiality_note")
    _assert_agreement_terms(data["terms"])


def _assert_agreement_terms(terms: list) -> None:
    assert len(terms) == 8
    assert [t["key"] for t in terms] == AGREEMENT_KEYS
    for t in terms:
        assert t["parent_a"] and t["parent_b"]
        assert t["status"] in {"Likely aligned", "Close", "Needs discussion"}


def _assert_agreement_pdf(pdf) -> None:
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert "coparenting-agreement-" in pdf.headers.get("content-disposition", "")
    assert pdf.content.startswith(b"%PDF")


def _pro_request(session, pro_email: str, co_parent_email: str, child: str = "TEST_Kid"):
    return session.post(f"{API}/joint/professional-requests", json={
        "professional_email": pro_email,
        "child_name": child,
        "co_parent_name": "Test Parent Q",
        "co_parent_email": co_parent_email,
    })


def _assert_safety_listing(rep: dict) -> None:
    assert rep.get("is_safety")
    assert set(rep.get("subjects") or []) == {"safety", "risk", "safety_communication", "safeguards"}
    assert rep.get("case_code", "").startswith("SA-SAF-")


# ------------------- Config -------------------
class TestJointConfig:
    def test_config_returns_8_agreement_areas(self) -> None:
        r = requests.get(f"{API}/joint/config", headers=UA)
        assert r.status_code == 200
        keys = [a["key"] for a in r.json()["agreement_areas"]]
        assert keys == AGREEMENT_KEYS
        for a in r.json()["agreement_areas"]:
            assert a["label"] and a["question"]


# ------------------- Agreement full flow -------------------
class TestAgreementFullFlow:
    def test_parent_cannot_create_agreement_403(self) -> None:
        pro0, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/agreements", json={
            "child_name": "K",
            "parent_a_name": "A", "parent_a_email": pa.email,
            "parent_b_name": "B", "parent_b_email": pb.email,
        })
        assert r.status_code == 403

    def test_create_accept_respond_report_pdf(self) -> None:
        pro, a, b, rid = _agreement_setup()

        _submit_agreement(a, rid, "a")

        detail_a = a.get(f"{API}/joint/reports/{rid}").json()
        assert "b" not in (detail_a.get("responses") or {}) or not detail_a["responses"].get("b", {}).get("answers")

        assert a.get(f"{API}/joint/reports/{rid}/report").status_code == 400

        _submit_agreement(b, rid, "b")

        rpt = pro.get(f"{API}/joint/reports/{rid}/report")
        assert rpt.status_code == 200, rpt.text
        _assert_agreement_report(rpt.json())
        _assert_agreement_pdf(a.get(f"{API}/joint/reports/{rid}/pdf"))

    def test_privacy_detail_view_hides_partner_answers(self) -> None:
        pro, a, b, rid = _agreement_setup()
        _submit_agreement(b, rid, "b", aligned=False)
        detail_a = a.get(f"{API}/joint/reports/{rid}").json()
        blob = str(detail_a).lower()
        for v in _agreement_answers("b", aligned=False).values():
            assert v.lower() not in blob, f"Partner answer leaked in A's detail view: {v}"


# ------------------- Professionals list + Professional-request flow -------------------
class TestProfessionalRequestFlow:
    def _created_request(self) -> tuple:
        """Parent requests an FV assessment from a professional. Returns (parent, parent2, pro, req_id)."""
        _seed_pro, parent, parent2, _d = new_case(API)
        pro = _pro("pro")
        rc = _pro_request(parent, pro.email, parent2.email)
        assert rc.status_code == 200, rc.text
        return parent, parent2, pro, rc.json()["id"]

    def test_request_creation_and_listing(self) -> None:
        parent, parent2, pro, req_id = self._created_request()

        pros = parent.get(f"{API}/professionals").json()
        assert any(p["email"] == pro.email.lower() for p in pros)

        r404 = _pro_request(parent, f"ghost_{uuid.uuid4().hex[:6]}@testmail.dev", parent2.email)
        assert r404.status_code == 404

        assert any(x["id"] == req_id for x in parent.get(f"{API}/joint/professional-requests").json())
        assert any(x["id"] == req_id for x in pro.get(f"{API}/joint/professional-requests").json())

    def test_prepare_flow(self) -> None:
        parent, parent2, pro, req_id = self._created_request()

        r403 = parent.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert r403.status_code == 403

        rp = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp.status_code == 200, rp.text
        rid = rp.json()["report_id"]

        rp2 = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp2.status_code == 400

        found = [r for r in pro.get(f"{API}/joint/reports").json() if r["id"] == rid]
        assert len(found) == 1
        _assert_safety_listing(found[0])

        pa_list = parent.get(f"{API}/joint/reports").json()
        assert not any(r["id"] == rid for r in pa_list), "Parent A must not see safety report before accepting invite"
        pb_list = parent2.get(f"{API}/joint/reports").json()
        assert not any(r["id"] == rid for r in pb_list), "Parent B must not see safety report before accepting invite"
