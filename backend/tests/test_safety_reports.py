"""Safety (family-violence) joint reports — professional-facilitated model.

Parents can no longer initiate any joint report (403). Safety assessments are
created through the professional-request → prepare flow; the facilitating
professional owns the case and parents participate via secure invitations.
"""
import os
import uuid

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _pro(prefix="med"):
    return new_user(API, "professional", f"Mediator {prefix}")


def _answers(theme):
    return {
        "needs_most": f"Our child needs {theme} safety and predictable routines.",
        "working_well": f"Currently the {theme} exchange protocol is generally followed.",
        "concerns": f"I am concerned about {theme} escalation during exchanges.",
        "improve": f"I would like {theme} written safety protocols documented.",
        "options": f"Option A: neutral exchange location. Option B: {theme} monitored app only.",
        "other_parent": f"The other parent likely worries about {theme} access to the child.",
    }


def _assert_safety_payload(rep: dict) -> None:
    assert rep["is_safety"]
    assert rep["confidentiality_note"]
    assert "individual responses will not be shared" in rep["confidentiality_note"].lower()
    assert rep["purpose"].startswith("This report is prepared through a third-party mediator")


def _submit_side(session, rid: str, theme: str) -> None:
    r = session.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers(theme)})
    assert r.status_code == 200, r.text


# ---------------- Parent initiation blocked ----------------
class TestParentInitiationBlocked:
    def test_parent_cannot_create_safety_report_403(self) -> None:
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 403

    def test_parent_cannot_create_any_report_403(self) -> None:
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 403


# ---------------- Full safety cycle via professional prepare ----------------
class TestFullSafetyCycle:
    def _prepared_case(self):
        """Parent requests FV assessment; professional prepares it. Returns (pro, pa, pb, rid, case_code)."""
        seed_pro, pa, pb, _d = new_case(API)
        pro = _pro()
        r = pa.post(f"{API}/joint/professional-requests", json={
            "professional_email": pro.email, "child_name": "Kid",
            "co_parent_name": "Parent B", "co_parent_email": pb.email,
        })
        assert r.status_code == 200, r.text
        req_id = r.json()["id"]
        rp = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp.status_code == 200, rp.text
        rid = rp.json()["report_id"]
        rep = [x for x in pro.get(f"{API}/joint/reports").json() if x["id"] == rid][0]
        assert rep["is_safety"]
        assert set(rep["subjects"]) == {"safety", "risk", "safety_communication", "safeguards"}
        assert rep.get("case_code", "").startswith("SA-SAF-")
        return pro, pa, pb, rid, rep["case_code"]

    def test_full_cycle_mediator_view_and_privacy(self) -> None:
        pro, pa, pb, rid, code = self._prepared_case()

        # Parents accept via the shared case code (email disambiguation)
        assert pa.post(f"{API}/joint/invitations/accept", json={"code": code}).status_code == 200
        assert pb.post(f"{API}/joint/invitations/accept", json={"code": code}).status_code == 200

        # A submits
        _submit_side(pa, rid, "morning_A ")

        # PRIVACY: B must not see A's answers
        blob = str(pb.get(f"{API}/joint/reports/{rid}").json()).lower()
        assert "morning_a" not in blob

        # Professional BEFORE completion — no report yet (400), and no individual answers via GET
        assert pro.get(f"{API}/joint/reports/{rid}/report").status_code == 400
        blob = str(pro.get(f"{API}/joint/reports/{rid}").json()).lower()
        assert "morning_a" not in blob

        # B submits → ready
        _submit_side(pb, rid, "evening_B ")

        # Parent gets the completed safety report with safety framing
        _assert_safety_payload(pa.get(f"{API}/joint/reports/{rid}/report").json())

        # Professional (facilitator) can view the completed report + PDF
        r = pro.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200 and r.json()["is_safety"]
        r = pro.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_nonsafety_report_no_safety_fields(self) -> None:
        pro, pa, pb, d = new_case(API, subject="education")
        rid = d["id"]
        _submit_side(pa, rid, "A ")
        _submit_side(pb, rid, "B ")
        rep = pro.get(f"{API}/joint/reports/{rid}/report").json()
        assert not rep["is_safety"]
        assert rep["confidentiality_note"] is None
        assert not rep["purpose"].startswith("This report is prepared through a third-party mediator")


# ---------------- joint_public shape ----------------
class TestJointPublicShape:
    def test_joint_public_returns_subjects_and_is_safety(self) -> None:
        pro = _pro("shape")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        d = r.json()
        assert d["subjects"] == ["education"]
        assert not d["is_safety"]
        assert d["professional_name"]
        assert d.get("case_code", "").startswith("SA-EDU-")
