"""Safety (family-violence) joint reports — mediator enforcement, full cycle, privacy."""
import os
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


def _reg(role="parent", prefix="s", email=None):
    email = email or f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": role,
    })
    assert r.status_code == 200, r.text
    s.email = email
    return s, email


def _answers(theme):
    return {
        "needs_most": f"Our child needs {theme} safety and predictable routines.",
        "working_well": f"Currently the {theme} exchange protocol is generally followed.",
        "concerns": f"I am concerned about {theme} escalation during exchanges.",
        "improve": f"I would like {theme} written safety protocols documented.",
        "options": f"Option A: neutral exchange location. Option B: {theme} monitored app only.",
        "other_parent": f"The other parent likely worries about {theme} access to the child.",
    }


# ---------------- Mediator enforcement ----------------
class TestSafetyMediatorEnforcement:
    def test_safety_without_mediator_400(self):
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 400
        assert "mediator" in r.json()["detail"].lower()

    def test_safety_with_unregistered_mediator_404(self):
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
            "mediator_email": f"TEST_ghost_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 404

    def test_safety_with_parent_role_mediator_404(self):
        """Mediator must be a professional, not a parent account."""
        a, _ = _reg(prefix="pa")
        _, parent_email = _reg(role="parent", prefix="notmed")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
            "mediator_email": parent_email,
        })
        assert r.status_code == 404

    def test_safety_with_registered_mediator_200(self):
        a, _ = _reg(prefix="pa")
        _, med_email = _reg(role="professional", prefix="med")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
            "mediator_email": med_email,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_safety"] is True
        assert d["professional_name"]
        assert d["subjects"] == ["safety"]

    def test_all_safety_multi_requires_mediator(self):
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety",
            "subjects": ["safety", "risk", "safety_communication", "safeguards"],
            "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 400

    def test_mixed_safety_and_nonsafety_does_not_require_mediator(self):
        """Mixed subject set (safety + education) should NOT trigger mediator requirement."""
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety",
            "subjects": ["safety", "education"],
            "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_safety"] is False

    def test_nonsafety_subject_no_mediator_required(self):
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 200
        assert r.json()["is_safety"] is False


# ---------------- Full safety cycle ----------------
class TestFullSafetyCycle:
    def test_full_cycle_mediator_view_and_privacy(self):
        a, _ = _reg(prefix="pa")
        b_email = f"TEST_pb_{uuid.uuid4().hex[:6]}@example.com"
        med, med_email = _reg(role="professional", prefix="med")

        # Create safety report
        r = a.post(f"{API}/joint/reports", json={
            "subject": "safety", "child_name": "Kid",
            "co_parent_name": "Bob", "co_parent_email": b_email,
            "mediator_email": med_email,
        })
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]
        assert r.json()["is_safety"] is True

        # B registers + accepts
        b, _ = _reg(prefix="pb", email=b_email)
        r = b.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r.status_code == 200

        # A submits
        r = a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("morning_A ")})
        assert r.status_code == 200

        # PRIVACY: B should not see A's answers
        r = b.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        blob = str(r.json()).lower()
        assert "morning_a" not in blob

        # Mediator BEFORE completion — no report yet (400)
        r = med.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 400

        # Mediator should NOT see individual answers via GET
        r = med.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        blob = str(r.json()).lower()
        assert "morning_a" not in blob

        # B submits
        r = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("evening_B ")})
        assert r.status_code == 200

        # Report ready — A gets it
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        rep = r.json()
        assert rep["is_safety"] is True
        assert rep["confidentiality_note"]
        assert "individual responses will not be shared" in rep["confidentiality_note"].lower()
        assert rep["purpose"].startswith("This report is prepared through a third-party mediator")

        # Mediator can view completed report
        r = med.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        assert r.json()["is_safety"] is True

        # PDF endpoint works for safety
        r = med.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_nonsafety_report_no_safety_fields(self):
        a, _ = _reg(prefix="pa")
        b_email = f"TEST_pb_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "Kid",
            "co_parent_name": "Bob", "co_parent_email": b_email,
        })
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]
        b, _ = _reg(prefix="pb", email=b_email)
        b.post(f"{API}/joint/invitations/accept", json={"code": code})
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("A ")})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("B ")})
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        rep = r.json()
        assert rep["is_safety"] is False
        assert rep["confidentiality_note"] is None
        assert not rep["purpose"].startswith("This report is prepared through a third-party mediator")


# ---------------- joint_public shape ----------------
class TestJointPublicShape:
    def test_joint_public_returns_subjects_and_is_safety(self):
        a, _ = _reg(prefix="pa")
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        d = r.json()
        assert "subjects" in d
        assert isinstance(d["subjects"], list)
        assert d["subjects"] == ["education"]
        assert d["is_safety"] is False
        assert "professional_name" in d
