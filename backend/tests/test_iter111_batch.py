"""Iteration 111 backend tests covering:
- B1: POST /api/parallel-parenting/court-notes/pdf
- D1: PUT /api/child-needs/me/{cat} acknowledged gating (422) + draft/submit flow
- D2: /api/child-needs/pdf + /api/journey-summary/pdf include notices
- E1: /api/journey-guide/child-needs/suggest field validation + auth
- G1: /api/foundation-builder/pdf with/without esign_name — Signatures/Notary/'/s/'
- G2: build_joint_agreement_pdf via module (no active share needed) + 'Co-Parenting Agreement'
"""
from __future__ import annotations

import io
import os
import uuid
import pytest
import requests

def _base() -> str:
    env = os.environ.get("REACT_APP_BACKEND_URL")
    if env:
        return env.rstrip("/")
    # fallback: read /app/frontend/.env
    try:
        with open("/app/frontend/.env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")

BASE_URL = _base()
API = f"{BASE_URL}/api"
TIMEOUT = 60


def _pdf_text(blob: bytes) -> str:
    """Extract concatenated text content of all pages via pypdf."""
    try:
        import pypdf, io as _io
        reader = pypdf.PdfReader(_io.BytesIO(blob))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        return f"<<pdf-extract-failed:{e}>>"


@pytest.fixture(scope="module")
def fresh_user():
    email = f"TEST_i111_{uuid.uuid4().hex[:10]}@test.com"
    r = requests.post(f"{API}/auth/register", json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter 111"}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    token = r.json().get("token") or r.json().get("access_token")
    assert token, r.text
    from ai_ready import accept_ai_notice
    accept_ai_notice(API, {"Authorization": f"Bearer {token}"})
    return {"email": email, "token": token}


@pytest.fixture(scope="module")
def auth(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}"}


# ---------- B1: Court-Order Notes PDF ----------
class TestCourtOrderNotesPdf:
    def test_court_notes_pdf_contains_expected_text(self, auth):
        # Save a plan with court_check ticks + professional_review ticks + note
        plan_body = {
            "answers": {},
            "notes": {"court_check": "Need to re-read Section 4 about holidays."},
            "checks": {
                "court_check": ["possession_time", "holidays"],
                "professional_review": ["custody_language", "safety_flags"],
            },
            "step": 0,
            "completed": False,
        }
        r = requests.put(f"{API}/parallel-parenting/me", json=plan_body, headers=auth, timeout=TIMEOUT)
        assert r.status_code == 200, r.text

        r = requests.post(f"{API}/parallel-parenting/court-notes/pdf", headers=auth, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        body = r.content
        assert body.startswith(b"%PDF-"), "not a PDF"
        text = _pdf_text(body)
        assert "Court-Order Notes" in text
        assert "Matches my order" in text
        assert "Still to check" in text
        # not-legal-advice note
        assert "legal advice" in text.lower()

    def test_court_notes_pdf_empty_plan_still_renders(self):
        # Fresh user with no plan: endpoint should still return a PDF with "None ticked yet."-style content
        email = f"TEST_i111_empty_{uuid.uuid4().hex[:8]}@test.com"
        r = requests.post(f"{API}/auth/register", json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Empty"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201)
        tok = r.json().get("token") or r.json().get("access_token")
        headers = {"Authorization": f"Bearer {tok}"}
        r = requests.post(f"{API}/parallel-parenting/court-notes/pdf", headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        text = _pdf_text(r.content)
        assert "Court-Order Notes" in text
        assert "None ticked yet" in text


# ---------- D1: Child-needs ack gating + draft/submit ----------
class TestChildNeedsAck:
    def test_put_without_ack_returns_422_for_fresh_user(self):
        email = f"TEST_i111_cn_{uuid.uuid4().hex[:8]}@test.com"
        r = requests.post(f"{API}/auth/register", json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "CN"}, timeout=TIMEOUT)
        tok = r.json().get("token") or r.json().get("access_token")
        headers = {"Authorization": f"Bearer {tok}"}

        # No acknowledged → 422
        payload = {"answers": {"edu_student": "Jane Doe"}, "acknowledged": False, "draft": False}
        r = requests.put(f"{API}/child-needs/me/educational", json=payload, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 422, r.text

        # With acknowledged + draft=true → saves as draft, no completed_at
        payload = {"answers": {"edu_student": "Jane Doe"}, "acknowledged": True, "draft": True}
        r = requests.put(f"{API}/child-needs/me/educational", json=payload, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        state = r.json()
        assert "educational" in state.get("drafts", {}), state
        assert "educational" not in state.get("completed_at", {}), state
        assert state.get("notice_ack_at")

        # Next save does NOT require acknowledged (already remembered)
        payload = {"answers": {"edu_student": "Jane Doe 2"}, "acknowledged": False, "draft": False}
        r = requests.put(f"{API}/child-needs/me/educational", json=payload, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        state = r.json()
        assert state["completed_at"].get("educational")
        assert "educational" not in state.get("drafts", {})  # draft cleared on submit


# ---------- D2: Child-needs PDF + Journey summary PDF contain notices ----------
class TestNoticesInPdfs:
    def test_child_needs_pdf_has_notices(self):
        body = {"parent_name": "Test Parent", "answers": {"educational": {"edu_student": "Jane Doe"}}}
        r = requests.post(f"{API}/child-needs/pdf", json=body, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        text = _pdf_text(r.content)
        assert "Notice of Confidentiality" in text
        assert "Health Information Privacy Notice" in text

    def test_journey_summary_pdf_has_notices(self, auth):
        r = requests.get(f"{API}/journey-summary/pdf", headers=auth, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        text = _pdf_text(r.content)
        assert "Notice of Confidentiality" in text
        assert "Health Information Privacy Notice" in text


# ---------- E1: journey-guide/child-needs/suggest ----------
class TestChildNeedsSuggest:
    def test_suggest_requires_auth(self):
        r = requests.post(
            f"{API}/journey-guide/child-needs/suggest",
            json={"category": "educational", "field_id": "edu_strengths", "draft": "", "answers": {}},
            timeout=TIMEOUT,
        )
        assert r.status_code in (401, 403)

    def test_suggest_404_for_select_or_help_false(self, auth):
        # edu_grade is a select → 404
        r = requests.post(
            f"{API}/journey-guide/child-needs/suggest",
            json={"category": "educational", "field_id": "edu_grade"},
            headers=auth, timeout=TIMEOUT,
        )
        assert r.status_code == 404, r.text
        # Unknown field → 404
        r = requests.post(
            f"{API}/journey-guide/child-needs/suggest",
            json={"category": "educational", "field_id": "not_a_real_field"},
            headers=auth, timeout=TIMEOUT,
        )
        assert r.status_code == 404

    def test_suggest_returns_text_for_valid_text_field(self, auth):
        r = requests.post(
            f"{API}/journey-guide/child-needs/suggest",
            json={"category": "educational", "field_id": "edu_strengths", "draft": "", "answers": {}},
            headers=auth, timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("suggestion"), str) and len(data["suggestion"]) > 0


# ---------- G1: Foundation builder PDF signatures ----------
class TestFoundationPdfSignatures:
    def test_pdf_with_esign(self):
        body = {
            "fields": {"parent_names": "Alex Doe & Jordan Doe", "children": "Sam, Age 8", "shared_values": "Kindness."},
            "esign_name": "Alex Doe",
        }
        r = requests.post(f"{API}/foundation-builder/pdf", json=body, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        text = _pdf_text(r.content)
        assert "Signatures" in text
        assert "Parent 1" in text and "Parent 2" in text
        assert "/s/ Alex Doe" in text
        # Honest note
        assert "legal" in text.lower()
        # Notary blocks (two)
        assert text.count("Notary acknowledgment") >= 2 or text.lower().count("notary") >= 2
        assert "Notary seal" in text

    def test_pdf_without_esign(self):
        body = {"fields": {"parent_names": "Alex & Jordan", "shared_values": "Love."}}
        r = requests.post(f"{API}/foundation-builder/pdf", json=body, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        text = _pdf_text(r.content)
        assert "/s/" not in text
        assert "Signatures" in text


# ---------- G2: Joint Agreement PDF via module (no active share needed) ----------
class TestJointAgreementPdfModule:
    def test_build_joint_agreement_pdf_rename_and_signatures(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from coparenting_alignment_sample import build_sample_payload
        from joint_agreement_pdf import build_joint_agreement_pdf

        payload = build_sample_payload()
        payload["esign_a"] = {"name": "Jane Doe", "at": "2026-10-09T14:10:00+00:00"}
        pdf_bytes = build_joint_agreement_pdf(payload)
        assert pdf_bytes.startswith(b"%PDF-")
        text = _pdf_text(pdf_bytes)
        assert "Co-Parenting Agreement" in text
        # Rename sanity: should not retain old header literal
        assert "Joint Alignment Report" not in text
        assert "Signatures" in text
        assert "/s/ Jane Doe" in text
        assert "Parent A" in text and "Parent B" in text
        assert "Notary" in text or "notary" in text

    def test_build_joint_agreement_pdf_no_esign(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from coparenting_alignment_sample import build_sample_payload
        from joint_agreement_pdf import build_joint_agreement_pdf

        payload = build_sample_payload()
        pdf_bytes = build_joint_agreement_pdf(payload)
        text = _pdf_text(pdf_bytes)
        assert "Co-Parenting Agreement" in text
        assert "/s/" not in text
        assert "Signatures" in text
