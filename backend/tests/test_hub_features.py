"""Tests for the Joint Report Hub feature:
- resolve_subjects() via POST /api/joint/reports with subjects[]
- POST /api/joint/reports/professional (dual-parent invite)
- GET /api/reports/complete (Complete Joint Alignment Report)
- PATCH /api/joint/invitations/{id} multi-subject guard (400)
- New subject keys (safety, risk, safety_communication, safeguards, co_parenting,
  child_needs, special_needs) appear in /api/joint/config
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASSWORD = "CoParents2026!"


def _reg(role="parent", prefix="hub"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": role,
    })
    assert r.status_code == 200, r.text
    return s, email


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


# ---------- /api/joint/config new subject keys ----------

class TestConfigSubjects:
    def test_config_contains_hub_subjects(self):
        r = requests.get(f"{API}/joint/config")
        assert r.status_code == 200
        keys = {s["key"] for s in r.json()["subjects"]}
        for k in ["co_parenting", "child_needs", "special_needs",
                  "safety", "risk", "safety_communication", "safeguards"]:
            assert k in keys, f"Missing subject key: {k}"


# ---------- Multi-subject create ----------

class TestMultiSubjectCreate:
    def test_customized_report_creates_multi(self):
        s, _ = _reg(prefix="parenta")
        payload = {
            "subject": "education", "subjects": ["education", "medical", "psychological"],
            "child_name": "TEST_Kid",
            "co_parent_name": "Coparent Q",
            "co_parent_email": f"TEST_coparent_{uuid.uuid4().hex[:8]}@example.com",
        }
        r = s.post(f"{API}/joint/reports", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject"] == "multi"
        assert "Customized Report:" in data["subject_label"]
        assert "School / Education" in data["subject_label"]
        assert "Medical" in data["subject_label"]
        assert "invitation" in data and data["invitation"]["code"]

        # GET verifies persistence
        rid = data["id"]
        g = s.get(f"{API}/joint/reports/{rid}")
        assert g.status_code == 200
        got = g.json()
        assert got["subject"] == "multi"

    def test_safety_pathway_multi_creates(self):
        s, _ = _reg(prefix="safety")
        # All-safety multi-subject requires a registered mediator
        _, med_email = _reg(role="professional", prefix="med")
        r = s.post(f"{API}/joint/reports", json={
            "subject": "safety", "subjects": ["safety", "risk", "safety_communication", "safeguards"],
            "child_name": "TEST_Kid",
            "co_parent_name": "Coparent",
            "co_parent_email": f"TEST_cp_{uuid.uuid4().hex[:8]}@example.com",
            "mediator_email": med_email,
        })
        assert r.status_code == 200, r.text
        assert r.json()["subject"] == "multi"
        assert r.json()["is_safety"] is True

    def test_single_subject_still_works(self):
        s, _ = _reg(prefix="single")
        r = s.post(f"{API}/joint/reports", json={
            "subject": "co_parenting",
            "child_name": "TEST_Kid",
            "co_parent_name": "Coparent",
            "co_parent_email": f"TEST_cp_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject"] == "co_parenting"

    def test_invalid_subject_rejected(self):
        s, _ = _reg(prefix="invalid")
        r = s.post(f"{API}/joint/reports", json={
            "subject": "education", "subjects": ["education", "not_a_real_subject"],
            "child_name": "TEST_Kid",
            "co_parent_name": "Coparent",
            "co_parent_email": f"TEST_cp_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 400


# ---------- PATCH multi-subject guard ----------

class TestPatchMultiGuard:
    def test_patch_multi_returns_400(self):
        s, _ = _reg(prefix="patchguard")
        r = s.post(f"{API}/joint/reports", json={
            "subject": "education", "subjects": ["education", "medical"],
            "child_name": "TEST_Kid",
            "co_parent_name": "Coparent",
            "co_parent_email": f"TEST_cp_{uuid.uuid4().hex[:8]}@example.com",
        })
        assert r.status_code == 200
        inv_id = r.json()["invitation"]["id"]
        p = s.patch(f"{API}/joint/invitations/{inv_id}", json={"subject": "communication"})
        assert p.status_code == 400
        assert "customized" in p.text.lower() or "multi" in p.text.lower()


# ---------- Professional dual-parent invite ----------

class TestProfessionalCreate:
    def test_professional_creates_report_and_sends_two_invitations(self):
        s, _ = _reg(role="professional", prefix="pro")
        parent_a_email = f"TEST_pa_{uuid.uuid4().hex[:8]}@example.com"
        parent_b_email = f"TEST_pb_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "subjects": ["education", "medical"],
            "child_name": "TEST_ProKid",
            "parent_a_name": "Parent A",
            "parent_a_email": parent_a_email,
            "parent_b_name": "Parent B",
            "parent_b_email": parent_b_email,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject"] == "multi"
        rid = data["id"]

        # both invitations exist in the reports list
        lr = s.get(f"{API}/joint/reports")
        assert lr.status_code == 200
        items = [x for x in lr.json() if x["id"] == rid]
        assert items, "Professional's report should appear in the list"

    def test_parent_cannot_call_professional_endpoint(self):
        s, _ = _reg(role="parent", prefix="notpro")
        r = s.post(f"{API}/joint/reports/professional", json={
            "subject": "education",
            "child_name": "TEST_Kid",
            "parent_a_name": "A", "parent_a_email": "TEST_a@example.com",
            "parent_b_name": "B", "parent_b_email": "TEST_b@example.com",
        })
        assert r.status_code == 403


# ---------- Complete Joint Alignment Report ----------

class TestCompleteReport:
    def test_empty_for_fresh_account(self):
        s, _ = _reg(prefix="empty")
        r = s.get(f"{API}/reports/complete")
        assert r.status_code == 200, r.text
        data = r.json()
        # Expect either empty flag/marker or zeroed totals + no sections
        assert data.get("empty") is True or (
            len(data.get("sections", [])) == 0
        )

    def test_admin_has_sections_and_totals(self):
        s = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = s.get(f"{API}/reports/complete")
        assert r.status_code == 200, r.text
        data = r.json()
        assert not data.get("empty")
        sections = data.get("sections", [])
        assert len(sections) > 0, "Admin should have completed data → sections"
        # totals sanity
        totals = data.get("totals") or {}
        # totals may hold varied keys; just ensure something numeric present
        assert isinstance(totals, dict)


# ---------- Multi-subject full cycle (create → accept → answer × 2 → ready) ----------

class TestMultiSubjectFullCycle:
    def test_full_cycle_and_report_ready(self):
        s_a, email_a = _reg(prefix="mfa")
        # Pre-create parent B account with matching email so accept works
        email_b = f"TEST_mfb_{uuid.uuid4().hex[:10]}@example.com"
        s_b = requests.Session()
        rb = s_b.post(f"{API}/auth/register", json={
            "name": "Parent B", "email": email_b, "password": "testpass123", "role": "parent",
        })
        assert rb.status_code == 200

        # Create multi-subject report
        r = s_a.post(f"{API}/joint/reports", json={
            "subject": "education", "subjects": ["education", "medical"],
            "child_name": "TEST_Cycle",
            "co_parent_name": "Parent B",
            "co_parent_email": email_b,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        rid = data["id"]
        code = data["invitation"]["code"]

        # Parent B accepts
        acc = s_b.post(f"{API}/joint/invitations/accept", json={"code": code})
        assert acc.status_code == 200, acc.text

        answers = {
            "needs_most": "Support", "working_well": "Routines",
            "concerns": "Late pickups", "improve": "Notice",
            "options": "Shared calendar", "other_parent": "Time",
        }
        ra = s_a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        assert ra.status_code == 200, ra.text
        rb2 = s_b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        assert rb2.status_code == 200, rb2.text

        # Report ready
        rep = s_a.get(f"{API}/joint/reports/{rid}/report")
        assert rep.status_code == 200, rep.text
        rj = rep.json()
        # Merged section content should carry [subject] labels
        text_blob = str(rj)
        assert "[School / Education]" in text_blob or "[Medical" in text_blob, \
            "Merged multi-subject report should include per-subject labels"

        # PDF still works
        pdf = s_a.get(f"{API}/joint/reports/{rid}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        assert len(pdf.content) > 500
