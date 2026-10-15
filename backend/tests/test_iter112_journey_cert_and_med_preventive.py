"""Iteration 112 — Self Journey Certificate + Steps-celebrated + Medical preventive field.

Covers:
- POST /api/journey-summary/certificate as journey6@test.com returns landscape Letter PDF
  with CERTIFICATE OF COMPLETION, the given name, 'Finished on', all 6 step titles,
  and the honest 'not a court-approved parenting course certificate and not legal advice' note.
- Certificate as parent1@test.com (partial progress) → 422 listing missing steps.
- Whitespace-only name → 422; no auth → 401.
- GET/POST /api/journey-summary/steps-celebrated flow (false→true).
- /api/child-needs/content exposes 7 medical fields incl. optional med_preventive.
- PUT /api/child-needs/me/medical with med_preventive persists via GET.
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
    with open("/app/frontend/.env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")


BASE_URL = _base()
API = f"{BASE_URL}/api"
TIMEOUT = 60


def _login(email: str, password: str = "TestPass123!") -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, r.text
    return tok


def _pdf_text(blob: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(blob))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        return f"<<pdf-extract-failed:{e}>>"


def _pdf_pages_and_orientation(blob: bytes):
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(blob))
    pages = reader.pages
    page = pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)
    return len(pages), (w, h)


@pytest.fixture(scope="module")
def journey6_auth():
    tok = _login("journey6@test.com")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def parent1_auth():
    tok = _login("parent1@test.com")
    return {"Authorization": f"Bearer {tok}"}


# ---------- Certificate: happy path (journey6 — all 6 done) ----------
class TestCertificateHappy:
    def test_certificate_pdf_as_journey6(self, journey6_auth):
        name = "Jordan Six Example"
        r = requests.post(
            f"{API}/journey-summary/certificate", json={"name": name}, headers=journey6_auth, timeout=TIMEOUT
        )
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        body = r.content
        assert body.startswith(b"%PDF-")

        # One page, landscape (w > h), ~Letter (11in x 8.5in → 792 x 612 pt)
        n_pages, (w, h) = _pdf_pages_and_orientation(body)
        assert n_pages == 1, f"expected 1 page, got {n_pages}"
        assert w > h, f"expected landscape, got w={w} h={h}"
        # Letter in points: 792 x 612 (allow 2pt tolerance)
        assert abs(w - 792) < 3 and abs(h - 612) < 3, f"not Letter landscape: {w}x{h}"

        text = _pdf_text(body)
        assert "CERTIFICATE OF COMPLETION" in text
        assert name in text
        assert "Finished on" in text
        for step in [
            "Self-Assessment",
            "Co-Parenting Assessment",
            "Your Child's Specific Needs",
            "Foundation Statement",
            "Parallel Parenting Plan",
            "Communication Builder",
        ]:
            assert step in text, f"missing step title in cert: {step}"
        # Honest note — PDF may wrap "legal advice" across a line break
        low = " ".join(text.lower().split())
        assert "not a court-approved parenting course certificate" in low
        assert "not legal advice" in low


# ---------- Certificate: validation errors ----------
class TestCertificateValidation:
    def test_no_auth_returns_401(self):
        r = requests.post(f"{API}/journey-summary/certificate", json={"name": "Nope"}, timeout=TIMEOUT)
        assert r.status_code in (401, 403), r.text

    def test_whitespace_name_returns_422(self, journey6_auth):
        r = requests.post(
            f"{API}/journey-summary/certificate", json={"name": "   "}, headers=journey6_auth, timeout=TIMEOUT
        )
        # Either Pydantic min_length=1 after strip (422) or server strip + 422
        assert r.status_code == 422, r.text

    def test_parent1_missing_steps_returns_422(self, parent1_auth):
        r = requests.post(
            f"{API}/journey-summary/certificate", json={"name": "Sam Parent"}, headers=parent1_auth, timeout=TIMEOUT
        )
        assert r.status_code == 422, r.text
        detail = (r.json().get("detail") or "").lower() if isinstance(r.json(), dict) else ""
        # Should mention at least one missing step name from parent1's known gaps:
        # Psychological (child-needs), Parallel Parenting, or Communication Builder
        assert any(
            tok in detail for tok in ("psycholog", "specific needs", "parallel parenting", "communication builder")
        ), r.text


# ---------- Steps-celebrated flow (use a fresh user to avoid flipping journey6/parent1 state) ----------
class TestStepsCelebratedFlow:
    def test_get_post_get_flow(self):
        email = f"TEST_i112_sc_{uuid.uuid4().hex[:8]}@test.com"
        r = requests.post(
            f"{API}/auth/register",
            json={"email": email, "password": "TestPass123!", "name": "Steps Celeb"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        tok = r.json().get("token") or r.json().get("access_token")
        headers = {"Authorization": f"Bearer {tok}"}

        # GET: initially false
        r = requests.get(f"{API}/journey-summary/steps-celebrated", headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json() == {"celebrated": False}

        # POST: marks true
        r = requests.post(f"{API}/journey-summary/steps-celebrated", headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json() == {"celebrated": True}

        # GET again: true
        r = requests.get(f"{API}/journey-summary/steps-celebrated", headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json() == {"celebrated": True}


# ---------- Child needs: medical has 7 fields incl. optional med_preventive ----------
class TestMedicalPreventiveField:
    def test_content_has_med_preventive(self):
        """Read content from the backend JSON file (there is no /content endpoint;
        frontend/backend JSONs are mirror-synced per the review request)."""
        import json
        with open("/app/backend/child_needs_content.json", "r", encoding="utf-8") as f:
            content = json.load(f)
        # Also verify the frontend mirror equals the backend content
        with open("/app/frontend/src/pages/portal/childNeedsContent.json", "r", encoding="utf-8") as f:
            fe_content = json.load(f)
        assert content == fe_content, "frontend childNeedsContent.json diverges from backend child_needs_content.json"

        medical = None
        # Try multiple shapes to locate medical
        if isinstance(content, dict):
            if "medical" in content:
                medical = content["medical"]
            elif "categories" in content:
                for cat in content["categories"]:
                    if cat.get("key") == "medical" or cat.get("id") == "medical":
                        medical = cat
                        break
        assert medical, f"could not locate 'medical' in content JSON; top keys: {list(content.keys())}"

        fields = []

        def _collect(obj):
            if isinstance(obj, dict):
                if "id" in obj and "type" in obj:
                    fields.append(obj)
                for v in obj.values():
                    _collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    _collect(item)

        _collect(medical)
        ids = [f["id"] for f in fields]
        expected = {"med_provider", "med_prescriptions", "med_conditions", "med_allergies", "med_preventive"}
        missing = expected - set(ids)
        assert not missing, f"missing medical fields: {missing}; got {ids}"
        assert len(ids) == 7, f"expected 7 medical fields, got {len(ids)}: {ids}"

        prev = next(f for f in fields if f["id"] == "med_preventive")
        assert prev.get("type") == "textarea"
        assert not prev.get("required", False), f"med_preventive should be optional, got {prev}"

    def test_put_medical_with_preventive_persists(self):
        email = f"TEST_i112_med_{uuid.uuid4().hex[:8]}@test.com"
        r = requests.post(
            f"{API}/auth/register",
            json={"email": email, "password": "TestPass123!", "name": "Med Test"},
            timeout=TIMEOUT,
        )
        tok = r.json().get("token") or r.json().get("access_token")
        headers = {"Authorization": f"Bearer {tok}"}

        preventive_text = "TEST_i112 Yearly check-up in August; dentist every 6 months."
        payload = {
            "answers": {
                "med_provider": "Dr. Who",
                "med_prescriptions": "None",
                "med_conditions": "None",
                "med_allergies": "None",
                "med_preventive": preventive_text,
            },
            "acknowledged": True,
            "draft": True,
        }
        r = requests.put(f"{API}/child-needs/me/medical", json=payload, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text

        # GET to verify
        r = requests.get(f"{API}/child-needs/me", headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        state = r.json()
        # Draft shape: drafts.<cat> is the flat answers dict
        draft = (state.get("drafts") or {}).get("medical") or {}
        assert draft.get("med_preventive") == preventive_text, state

        # Submit (draft=False) and verify preventive still there under answers.medical
        payload["draft"] = False
        r = requests.put(f"{API}/child-needs/me/medical", json=payload, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = requests.get(f"{API}/child-needs/me", headers=headers, timeout=TIMEOUT)
        state = r.json()
        answers = (state.get("answers") or {}).get("medical") or {}
        assert answers.get("med_preventive") == preventive_text, state
        assert (state.get("completed_at") or {}).get("medical"), state
