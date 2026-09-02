"""Joint Report Builder — invite flow, privacy, professional flow, sharing, management."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


def _mk_answers(theme_words):
    """Create realistic answer set that will share keywords for alignment heuristic."""
    base = f"I feel our child needs {theme_words} consistent routines and clear homework expectations between homes."
    return {
        "needs_most": f"Our child needs {theme_words} academic support and consistent homework routines.",
        "working_well": f"The current homework schedule at my home works with {theme_words} consistent evening routines.",
        "concerns": f"I'm concerned about inconsistent homework completion and {theme_words} varying expectations between homes.",
        "improve": f"I would like to improve communication about homework and academic {theme_words} expectations.",
        "options": f"Option A: shared homework log. Option B: same homework times. {theme_words} coordinated with teacher.",
        "other_parent": f"The other parent likely worries about homework quality and {theme_words} academic consistency.",
    }


def _register(name="P", role="parent", email=None):
    s = requests.Session()
    email = email or f"jt_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": name, "email": email, "password": "password123", "role": role})
    assert r.status_code == 200, r.text
    s.email = email
    s.name = name
    return s


# ---------------- Config ----------------
class TestJointConfig:
    def test_config_has_13_subjects_and_6_questions(self):
        r = requests.get(f"{API}/joint/config")
        assert r.status_code == 200
        data = r.json()
        assert len(data["subjects"]) == 13
        keys = [s["key"] for s in data["subjects"]]
        assert "education" in keys and "custom" in keys
        assert len(data["questions"]) == 6
        assert set(q["key"] for q in data["questions"]) == set(ANSWER_KEYS)
        assert "SA CoParents does not share" in data["confidentiality_notice"]


# ---------------- Create + Invite ----------------
class TestJointCreateAndInvite:
    def test_create_joint_report_returns_code_and_link(self):
        a = _register("Parent A")
        invitee = f"invitee_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "custom_subject": "", "child_name": "TEST_Kid",
            "co_parent_name": "Parent B", "co_parent_email": invitee,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subject"] == "education"
        assert d["subject_label"] == "School / Education"
        assert d["child_name"] == "TEST_Kid"
        assert d["is_creator"] is True
        assert d["my_role"] == "a"
        assert d["status"] == "pending_invite"
        inv = d["invitation"]
        assert len(inv["code"]) == 6
        assert inv["invitee_email"] == invitee.lower()
        assert "/join/" in inv["link"]

    def test_create_unknown_subject_400(self):
        a = _register()
        r = a.post(f"{API}/joint/reports", json={
            "subject": "nope", "custom_subject": "", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": "b@example.com",
        })
        assert r.status_code == 400

    def test_create_custom_subject(self):
        a = _register()
        r = a.post(f"{API}/joint/reports", json={
            "subject": "custom", "custom_subject": "Summer travel", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": f"b_{uuid.uuid4().hex[:5]}@example.com",
        })
        assert r.status_code == 200
        assert r.json()["subject_label"] == "Summer travel"

    def test_create_requires_auth(self):
        r = requests.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": "b@example.com",
        })
        assert r.status_code == 401


# ---------------- Accept via code + full flow ----------------
class TestAcceptAndFullFlow:
    def test_accept_by_code_wrong_email_403(self):
        a = _register("A")
        invitee = f"target_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": invitee,
        })
        code = r.json()["invitation"]["code"]
        # Register a different email
        wrong = _register("Wrong")
        r2 = wrong.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r2.status_code == 403

    def test_accept_invalid_code(self):
        b = _register("B")
        r = b.post(f"{API}/joint/invitations/accept", json={"code": "ZZZZZZ"})
        assert r.status_code == 404

    def test_full_flow_privacy_and_report(self):
        a = _register("Alice")
        invitee = f"bob_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "Sam",
            "co_parent_name": "Bob", "co_parent_email": invitee,
        })
        assert r.status_code == 200
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]

        # Register B with matching email
        b = _register("Bob", email=invitee)

        # B accepts by code
        r = b.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r.status_code == 200
        assert r.json()["report_id"] == rid

        # Report not ready until both complete → 400
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 400

        # A submits
        r = a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("morning ")})
        assert r.status_code == 200

        # Still 400 — only A done
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 400

        # PRIVACY: B fetches detail — must NOT see A's answers
        r = b.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        detail_b = r.json()
        # B's my_answers should be None (not submitted yet)
        assert detail_b.get("my_answers") is None
        # No key in detail_b should contain parent A's response text
        blob = str(detail_b).lower()
        assert "morning" not in blob, f"Parent A's answers leaked to B: {detail_b}"

        # B submits with different theme
        r = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("evening ")})
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

        # Report available now
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        rep = r.json()
        assert rep["report_title"] == "Joint Parenting Alignment Report"
        assert rep["subject_label"] == "School / Education"
        assert rep["child_name"] == "Sam"
        assert len(rep["alignment_map"]) == 6
        assert len(rep["options"]) == 3
        assert len(rep["next_steps"]) == 6
        assert rep["philosophy_heading"] == "Alignment Before Agreement"
        assert isinstance(rep["alignment_statements"], list) and len(rep["alignment_statements"]) >= 1

        # B can also fetch report and see own answers now
        r = b.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        assert r.json()["my_answers"]["needs_most"].startswith("Our child needs evening")
        r = b.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200

        # Non-participant → 404
        c = _register("Stranger")
        r = c.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 404
        r = c.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 404

        # Connection auto-created
        r = a.get(f"{API}/joint/connections")
        assert r.status_code == 200
        assert any(c.get("other_email") == invitee for c in r.json())

    def test_incomplete_answers_400(self):
        a = _register()
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": f"b_{uuid.uuid4().hex[:5]}@example.com",
        })
        rid = r.json()["id"]
        r = a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {"needs_most": "just one"}})
        assert r.status_code == 400


# ---------------- Accept via token/link ----------------
class TestAcceptByToken:
    def test_lookup_and_accept_by_token(self):
        a = _register("A")
        invitee = f"tok_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "communication", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": invitee,
        })
        link = r.json()["invitation"]["link"]
        token = link.rsplit("/", 1)[-1]

        # Public lookup (no auth)
        r = requests.get(f"{API}/joint/invitations/lookup/{token}")
        assert r.status_code == 200
        assert r.json()["invitee_email"] == invitee.lower()
        assert r.json()["subject_label"] == "Communication"

        # Accept via token as body.code
        b = _register("B", email=invitee)
        r = b.post(f"{API}/joint/invitations/accept", json={"code": token})
        assert r.status_code == 200

    def test_lookup_invalid_token_404(self):
        r = requests.get(f"{API}/joint/invitations/lookup/nonexistent_token_xyz")
        assert r.status_code == 404


# ---------------- Invitation management ----------------
class TestInvitationManagement:
    def _setup(self):
        a = _register("A")
        invitee = f"mgmt_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": invitee,
        })
        return a, invitee, r.json()

    def test_resend_ok(self):
        a, invitee, d = self._setup()
        r = a.post(f"{API}/joint/invitations/{d['invitation']['id']}/resend")
        assert r.status_code == 200

    def test_resend_non_creator_forbidden(self):
        a, invitee, d = self._setup()
        other = _register("Other")
        r = other.post(f"{API}/joint/invitations/{d['invitation']['id']}/resend")
        assert r.status_code in (403, 404)

    def test_change_subject_before_ready(self):
        a, invitee, d = self._setup()
        r = a.patch(f"{API}/joint/invitations/{d['invitation']['id']}", json={
            "subject": "medical", "custom_subject": ""
        })
        assert r.status_code == 200
        assert r.json()["subject_label"] == "Medical Care"
        # Verify persistence
        r = a.get(f"{API}/joint/reports/{d['id']}")
        assert r.json()["subject_label"] == "Medical Care"

    def test_change_subject_unknown_400(self):
        a, invitee, d = self._setup()
        r = a.patch(f"{API}/joint/invitations/{d['invitation']['id']}", json={
            "subject": "bogus", "custom_subject": ""
        })
        assert r.status_code == 400

    def test_change_subject_blocked_when_ready(self):
        a, invitee, d = self._setup()
        rid = d["id"]
        code = d["invitation"]["code"]
        b = _register("B", email=invitee)
        b.post(f"{API}/joint/invitations/accept", json={"code": code})
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("x ")})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("y ")})
        # Now ready
        r = a.patch(f"{API}/joint/invitations/{d['invitation']['id']}", json={
            "subject": "medical", "custom_subject": ""
        })
        assert r.status_code == 400

    def test_cancel_makes_code_invalid(self):
        a, invitee, d = self._setup()
        r = a.post(f"{API}/joint/invitations/{d['invitation']['id']}/cancel")
        assert r.status_code == 200
        b = _register("B", email=invitee)
        r = b.post(f"{API}/joint/invitations/accept", json={"code": d["invitation"]["code"]})
        assert r.status_code == 404


# ---------------- Professional flow + share ----------------
class TestProfessionalFlow:
    def test_professional_creates_and_share(self):
        pro = _register("Doc", role="professional")
        email_a = f"pa_{uuid.uuid4().hex[:6]}@example.com"
        email_b = f"pb_{uuid.uuid4().hex[:6]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "schedule", "custom_subject": "", "child_name": "K",
            "parent_a_name": "PA", "parent_a_email": email_a,
            "parent_b_name": "PB", "parent_b_email": email_b,
        })
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        assert r.json()["professional_name"] == "Doc"

        # Report 400 until both parents complete
        r = pro.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 400

        # Both parents register + accept + complete (need codes — use list_joint_reports on the pro
        # to fetch invitation codes? Pro only sees ONE pending inv via detail. We need to hit
        # DB indirectly by using the invite link in join lookup... instead register both, then
        # they need code. The response only returned one invitation (b/c list_joint_reports maps
        # created_by → one pending). Codes are not returned to pro for both parents through the
        # public API. Let's verify pro can see the report and status.
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        # For share test, use parent-only path: create a report a-b, complete it, then share w/ pro.
        parent_a = _register("PPA")
        invitee_b = f"pshare_{uuid.uuid4().hex[:6]}@example.com"
        r = parent_a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "PB", "co_parent_email": invitee_b,
        })
        rid2 = r.json()["id"]
        code = r.json()["invitation"]["code"]
        parent_b = _register("PPB", email=invitee_b)
        parent_b.post(f"{API}/joint/invitations/accept", json={"code": code})
        parent_a.put(f"{API}/joint/reports/{rid2}/responses", json={"answers": _mk_answers("x ")})
        parent_b.put(f"{API}/joint/reports/{rid2}/responses", json={"answers": _mk_answers("y ")})

        # Share with the professional
        r = parent_a.post(f"{API}/joint/reports/{rid2}/share", json={"email": pro.email})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # Professional now sees it in list + can fetch the report
        r = pro.get(f"{API}/joint/reports")
        assert any(x["id"] == rid2 for x in r.json())
        r = pro.get(f"{API}/joint/reports/{rid2}/report")
        assert r.status_code == 200

    def test_share_to_non_professional_email_404(self):
        a = _register("A")
        invitee = f"share_{uuid.uuid4().hex[:6]}@example.com"
        r = a.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": invitee,
        })
        rid = r.json()["id"]
        code = r.json()["invitation"]["code"]
        b = _register("B", email=invitee)
        b.post(f"{API}/joint/invitations/accept", json={"code": code})
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("x ")})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _mk_answers("y ")})

        r = a.post(f"{API}/joint/reports/{rid}/share", json={"email": "no-such-pro@example.com"})
        assert r.status_code == 404

    def test_professional_endpoint_requires_professional_role(self):
        a = _register("A")  # parent role
        r = a.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": "a@example.com",
            "parent_b_name": "B", "parent_b_email": "b@example.com",
        })
        assert r.status_code == 403
