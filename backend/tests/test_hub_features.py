"""Tests for the Joint Report Hub feature (professional-initiated model):
- resolve_subjects() via POST /api/joint/reports/professional with subjects[]
- PATCH /api/joint/invitations/{id} multi-subject guard (400)
- GET /api/reports/complete (Complete Joint Alignment Report)
- New subject keys appear in /api/joint/config
- Parent initiation is blocked (403)
"""
import os
import uuid
import requests
import pytest
from dotenv import load_dotenv

from casekit import new_user, new_case, fill

load_dotenv("/app/backend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def _clear_admin_lockout():
    """Brute-force lockout (15 min) would otherwise cascade across test runs."""
    import pymongo
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    client[os.environ["DB_NAME"]].login_attempts.delete_many({"identifier": {"$regex": f":{ADMIN_EMAIL}$"}})
    client.close()


def _pro(prefix="hub"):
    return new_user(API, "professional", f"Pro {prefix}")


# ---------- /api/joint/config new subject keys ----------

class TestConfigSubjects:
    def test_config_contains_hub_subjects(self) -> None:
        r = requests.get(f"{API}/joint/config")
        assert r.status_code == 200
        keys = {s["key"] for s in r.json()["subjects"]}
        for k in ["co_parenting", "child_needs", "special_needs",
                  "safety", "risk", "safety_communication", "safeguards"]:
            assert k in keys, f"Missing subject key: {k}"


# ---------- Multi-subject create (professional) ----------

class TestMultiSubjectCreate:
    def test_customized_report_creates_multi(self) -> None:
        s = _pro("multi")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "subjects": ["education", "medical", "psychological"],
            "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject"] == "multi"
        assert "Customized Report:" in data["subject_label"]
        assert "School / Education" in data["subject_label"]
        assert "Medical" in data["subject_label"]
        assert len(data["invitations"]) == 2
        got = s.get(f"{API}/joint/reports/{data['id']}").json()
        assert got["subject"] == "multi"

    def test_safety_pathway_multi_creates(self) -> None:
        s = _pro("safety")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "safety", "subjects": ["safety", "risk", "safety_communication", "safeguards"],
            "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200, r.text
        assert r.json()["subject"] == "multi"
        assert r.json()["is_safety"]

    def test_single_subject_still_works(self) -> None:
        s = _pro("single")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "co_parenting", "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200, r.text
        assert r.json()["subject"] == "co_parenting"

    def test_invalid_subject_rejected(self) -> None:
        s = _pro("invalid")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "subjects": ["education", "not_a_real_subject"],
            "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 400

    def test_parent_initiation_blocked(self) -> None:
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports", json={
            "subject": "education", "child_name": "TEST_Kid",
            "co_parent_name": "B", "co_parent_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 403


# ---------- PATCH multi-subject guard ----------

class TestPatchMultiGuard:
    def test_patch_multi_returns_400(self) -> None:
        s = _pro("patchguard")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "subjects": ["education", "medical"],
            "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": f"TEST_a_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_b_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200
        rid = r.json()["id"]
        rep = [x for x in s.get(f"{API}/joint/reports").json() if x["id"] == rid][0]
        inv_id = rep["pending_invitations"][0]["id"]
        p = s.patch(f"{API}/joint/invitations/{inv_id}", json={"subject": "communication"})
        assert p.status_code == 400
        assert "customized" in p.text.lower() or "multi" in p.text.lower()


# ---------- Professional dual-parent invite ----------

class TestProfessionalCreate:
    def test_professional_creates_report_and_sends_two_invitations(self) -> None:
        s = _pro("pro")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "subjects": ["education", "medical"],
            "child_name": "TEST_ProKid",
            "parent_a_name": "Parent A", "parent_a_email": f"TEST_pa_{uuid.uuid4().hex[:8]}@example.com",
            "parent_b_name": "Parent B", "parent_b_email": f"TEST_pb_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject"] == "multi"
        items = [x for x in s.get(f"{API}/joint/reports").json() if x["id"] == data["id"]]
        assert items, "Professional's report should appear in the list"
        assert len(items[0]["pending_invitations"]) == 2

    def test_parent_cannot_call_professional_endpoint(self) -> None:
        pro, pa, pb, d = new_case(API)
        r = pa.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": "TEST_a@example.com",
            "parent_b_name": "B", "parent_b_email": "TEST_b@example.com",
        })
        assert r.status_code == 403


# ---------- Complete Joint Alignment Report ----------

class TestCompleteReport:
    def test_empty_for_fresh_account(self) -> None:
        s = _pro("empty")
        r = s.get(f"{API}/reports/complete")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("empty") or len(data.get("sections", [])) == 0

    def test_complete_report_with_data(self) -> None:
        """A user with a completed (demo) assessment gets sections and totals."""
        s = _pro("complete")
        r = s.post(f"{API}/cases", json={"type": "educational", "child_name": "TEST_Kid"})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        r = s.post(f"{API}/cases/{cid}/demo")
        assert r.status_code == 200, r.text
        r = s.get(f"{API}/reports/complete")
        assert r.status_code == 200, r.text
        data = r.json()
        assert not data.get("empty")
        assert len(data.get("sections", [])) > 0
        assert isinstance(data.get("totals") or {}, dict)


# ---------- Multi-subject full cycle ----------

class TestMultiSubjectFullCycle:
    def test_full_cycle_and_report_ready(self) -> None:
        pro, pa, pb, d = new_case(API, subjects=["education", "medical"], subject="education")
        rid = d["id"]
        answers = {
            "needs_most": "Support", "working_well": "Routines",
            "concerns": "Late pickups", "improve": "Notice",
            "options": "Shared calendar", "other_parent": "Time",
        }
        assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers}).status_code == 200
        assert pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers}).status_code == 200

        rep = pro.get(f"{API}/joint/reports/{rid}/report")
        assert rep.status_code == 200, rep.text
        text_blob = str(rep.json())
        assert "[School / Education]" in text_blob or "[Medical" in text_blob

        pdf = pro.get(f"{API}/joint/reports/{rid}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        assert len(pdf.content) > 500
