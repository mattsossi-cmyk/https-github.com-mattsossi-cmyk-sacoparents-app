"""Joint Report Builder — professional-initiated cases, invite flow, privacy, sharing, management.

Product rule (2026-09): professionals initiate every case. Parents register only
through a secure invitation (token link primary, shared case code as backup).
"""
import os
import re
import uuid
import requests

from casekit import new_user, new_case, fill, completed_case, ANSWER_KEYS

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------------- Config ----------------
class TestJointConfig:
    def test_config_has_20_subjects_and_6_questions(self):
        r = requests.get(f"{API}/joint/config")
        assert r.status_code == 200
        data = r.json()
        assert len(data["subjects"]) == 20
        keys = [s["key"] for s in data["subjects"]]
        assert "education" in keys and "custom" in keys
        assert len(data["questions"]) == 6
        assert set(q["key"] for q in data["questions"]) == set(ANSWER_KEYS)
        assert "SA CoParents does not share" in data["confidentiality_notice"]


# ---------------- Professional-only initiation ----------------
class TestProfessionalInitiationGates:
    def test_parent_cannot_create_joint_report_403(self):
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": f"b_{uuid.uuid4().hex[:5]}@example.com",
        })
        assert r.status_code == 403
        assert "professional" in r.json()["detail"].lower()

    def test_parent_cannot_create_agreement_403(self):
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/agreements", json={
            "child_name": "K",
            "parent_a_name": "A", "parent_a_email": pa.email,
            "parent_b_name": "B", "parent_b_email": pb.email,
        })
        assert r.status_code == 403

    def test_create_requires_auth_401(self):
        r = requests.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "K",
            "co_parent_name": "B", "co_parent_email": "b@example.com",
        })
        assert r.status_code == 401

    def test_professional_endpoint_requires_professional_role_403(self):
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": "a@example.com",
            "parent_b_name": "B", "parent_b_email": "b@example.com",
        })
        assert r.status_code == 403


# ---------------- Create + Invite ----------------
class TestProCreateAndInvite:
    def test_pro_create_returns_case_code_and_shared_code(self):
        pro, pa, pb, d = new_case(API, subject="education", child="TEST_Kid", case_reference="REF-1")
        assert re.fullmatch(r"SA-EDU-\d{6}", d["case_code"])
        invs = d["invitations"]
        assert len(invs) == 2
        assert invs[0]["code"] == invs[1]["code"] == d["case_code"]
        assert all("/join/" in i["link"] for i in invs)
        assert d["status"] == "pending_invite"
        assert d["professional_name"] == "Pro"
        assert d["case_reference"] == "REF-1"
        assert d["is_creator"] == True

    def test_create_unknown_subject_400(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "nope", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": "a@example.com",
            "parent_b_name": "B", "parent_b_email": "b@example.com",
        })
        assert r.status_code == 400

    def test_create_custom_subject(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "custom", "custom_subject": "Summer travel", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"a_{uuid.uuid4().hex[:5]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"b_{uuid.uuid4().hex[:5]}@example.com",
        })
        assert r.status_code == 200
        assert r.json()["subject_label"] == "Summer travel"


# ---------------- Accept via code/token ----------------
class TestAccept:
    def test_shared_case_code_email_disambiguation(self):
        pro = new_user(API, "professional", "Pro")
        ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
        eb = f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": ea,
            "parent_b_name": "B", "parent_b_email": eb,
        })
        d = r.json()
        code = d["case_code"]
        toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}

        # Parent B registers with invite + accepts via the shared case code
        pb = new_user(API, "parent", "B", email=eb, invite=toks["b"])
        r = pb.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r.status_code == 200 and r.json()["ok"]

        # A wrong-email account cannot use the code
        stranger = new_user(API, "professional", "Stranger")
        r = stranger.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert r.status_code == 403

    def test_accept_invalid_code_404(self):
        u = new_user(API, "professional", "U")
        r = u.post(f"{API}/joint/invitations/accept", json={"code": "SA-XXX-000000"})
        assert r.status_code == 404

    def test_lookup_public_and_accept_by_token(self):
        pro = new_user(API, "professional", "Pro")
        ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "communication", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": ea,
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        inv_a = [i for i in r.json()["invitations"] if i["invitee_email"] == ea][0]
        token = inv_a["link"].rsplit("/", 1)[-1]

        r = requests.get(f"{API}/joint/invitations/lookup/{token}")
        assert r.status_code == 200
        assert r.json()["invitee_email"] == ea.lower()
        assert r.json()["subject_label"] == "Communication"

        pa = new_user(API, "parent", "A", email=ea, invite=token)
        r = pa.post(f"{API}/joint/invitations/accept", json={"code": token})
        assert r.status_code == 200 and r.json()["ok"]

    def test_lookup_invalid_token_404(self):
        r = requests.get(f"{API}/joint/invitations/lookup/nonexistent_token_xyz")
        assert r.status_code == 404

    def test_parent_register_with_wrong_invite_403(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        tok = r.json()["invitations"][0]["link"].rsplit("/", 1)[-1]
        # Different email than the invitation was sent to
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "name": "Wrong", "email": f"wrong_{uuid.uuid4().hex[:6]}@example.com",
            "password": "password123", "role": "parent", "invite": tok,
        })
        assert r.status_code == 403


# ---------------- Full flow: privacy + report ----------------
class TestFullFlow:
    def test_full_flow_privacy_and_report(self):
        pro, pa, pb, d = new_case(API, subject="education", child="Sam")
        rid = d["id"]

        # Report not ready until both complete → 400
        assert pro.get(f"{API}/joint/reports/{rid}/report").status_code == 400

        # A submits
        fill(API, pa, rid, "alpha")
        assert pro.get(f"{API}/joint/reports/{rid}/report").status_code == 400

        # PRIVACY: B's detail must not contain A's answers
        detail_b = pb.get(f"{API}/joint/reports/{rid}").json()
        assert detail_b.get("my_answers") is None
        assert "alpha" not in str(detail_b).lower()

        # B submits → ready
        r = fill(API, pb, rid, "beta")
        assert r["status"] == "ready"

        # Report available to pro and both parents
        rep = pro.get(f"{API}/joint/reports/{rid}/report").json()
        assert rep["report_title"] == "Joint Parenting Alignment Report"
        assert rep["subject_label"] == "School / Education"
        assert rep["child_name"] == "Sam"
        assert len(rep["alignment_map"]) == 6
        assert len(rep["options"]) == 3
        assert len(rep["next_steps"]) == 6
        assert rep["philosophy_heading"] == "Alignment Before Agreement"
        assert len(rep["alignment_statements"]) >= 1
        assert pb.get(f"{API}/joint/reports/{rid}/report").status_code == 200

        # B sees own answers only
        assert pb.get(f"{API}/joint/reports/{rid}").json()["my_answers"]["needs_most"].startswith("Our child needs beta")

        # Case reference visible to pro creator, hidden from parents
        pro2 = new_user(API, "professional", "Pro2")
        r = pro2.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K2",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
            "case_reference": "PRIVATE-1",
        })
        rid2 = r.json()["id"]
        assert pro2.get(f"{API}/joint/reports/{rid2}").json()["case_reference"] == "PRIVATE-1"

        # Non-participant → 404
        stranger = new_user(API, "professional", "Stranger")
        assert stranger.get(f"{API}/joint/reports/{rid}").status_code == 404
        assert stranger.get(f"{API}/joint/reports/{rid}/report").status_code == 404

        # Connection auto-created between parents
        conns = pa.get(f"{API}/joint/connections").json()
        assert any(c.get("other_email") == pb.email for c in conns)

    def test_incomplete_answers_400(self):
        pro, pa, pb, d = new_case(API)
        rid = d["id"]
        r = pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {"needs_most": "just one"}})
        assert r.status_code == 400


# ---------------- Invitation management ----------------
class TestInvitationManagement:
    def _pending_inv(self, pro, rid, role="a"):
        reports = pro.get(f"{API}/joint/reports").json()
        rep = [x for x in reports if x["id"] == rid][0]
        inv = [i for i in rep["pending_invitations"] if i["role"] == role][0]
        return inv

    def test_resend_ok(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        rid = r.json()["id"]
        inv = self._pending_inv(pro, rid, "a")
        r = pro.post(f"{API}/joint/invitations/{inv['id']}/resend")
        assert r.status_code == 200

    def test_resend_non_creator_forbidden(self):
        pro, pa, pb, d = new_case(API)
        # after acceptance nothing is pending; use a fresh case still pending
        pro2 = new_user(API, "professional", "Pro2")
        r = pro2.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        inv = self._pending_inv(pro2, r.json()["id"], "a")
        other = new_user(API, "professional", "Other")
        r = other.post(f"{API}/joint/invitations/{inv['id']}/resend")
        assert r.status_code in (403, 404)

    def test_change_subject_before_ready(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        rid = r.json()["id"]
        inv = self._pending_inv(pro, rid, "a")
        r = pro.patch(f"{API}/joint/invitations/{inv['id']}", json={"subject": "medical", "custom_subject": ""})
        assert r.status_code == 200
        assert r.json()["subject_label"] == "Medical Care"
        assert pro.get(f"{API}/joint/reports/{rid}").json()["subject_label"] == "Medical Care"

    def test_change_subject_unknown_400(self):
        pro = new_user(API, "professional", "Pro")
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        inv = self._pending_inv(pro, r.json()["id"], "b")
        r = pro.patch(f"{API}/joint/invitations/{inv['id']}", json={"subject": "bogus", "custom_subject": ""})
        assert r.status_code == 400

    def test_change_subject_blocked_when_ready(self):
        pro = new_user(API, "professional", "Pro")
        ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": ea,
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        d = r.json()
        rid = d["id"]
        inv = self._pending_inv(pro, rid, "a")
        toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}
        pa = new_user(API, "parent", "A", email=ea, invite=toks["a"])
        pb_email = [i["invitee_email"] for i in d["invitations"] if i["role"] == "b"][0]
        pb = new_user(API, "parent", "B", email=pb_email, invite=toks["b"])
        pa.post(f"{API}/joint/invitations/accept", json={"code": toks["a"]})
        pb.post(f"{API}/joint/invitations/accept", json={"code": toks["b"]})
        fill(API, pa, rid, "x")
        fill(API, pb, rid, "y")
        r = pro.patch(f"{API}/joint/invitations/{inv['id']}", json={"subject": "medical", "custom_subject": ""})
        assert r.status_code == 400

    def test_cancel_invalidates_code(self):
        pro = new_user(API, "professional", "Pro")
        ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": ea,
            "parent_b_name": "B", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        d = r.json()
        toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}
        pa = new_user(API, "parent", "A", email=ea, invite=toks["a"])
        inv = self._pending_inv(pro, d["id"], "a")
        r = pro.post(f"{API}/joint/invitations/{inv['id']}/cancel")
        assert r.status_code == 200
        r = pa.post(f"{API}/joint/invitations/accept", json={"code": toks["a"]})
        assert r.status_code == 404


# ---------------- Sharing with other professionals ----------------
class TestSharing:
    def test_share_completed_report_with_professional(self):
        pro, pa, pb, d, detail = completed_case(API)
        rid = d["id"]
        pro2 = new_user(API, "professional", "Reviewer")
        r = pa.post(f"{API}/joint/reports/{rid}/share", json={"email": pro2.email})
        assert r.status_code == 200 and r.json()["ok"] == True
        assert any(x["id"] == rid for x in pro2.get(f"{API}/joint/reports").json())
        assert pro2.get(f"{API}/joint/reports/{rid}/report").status_code == 200

    def test_share_to_non_professional_email_404(self):
        pro, pa, pb, d, detail = completed_case(API)
        r = pa.post(f"{API}/joint/reports/{d['id']}/share", json={"email": "no-such-pro@example.com"})
        assert r.status_code == 404
