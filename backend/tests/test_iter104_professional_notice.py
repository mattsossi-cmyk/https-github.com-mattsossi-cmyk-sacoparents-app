"""Iter-104: Professional Notice gate (professionals only), versioned acceptance, admin log."""
import os
import uuid

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from professional_notice import NOTICE, PROFESSIONAL_NOTICE_VERSION  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"


def _register(role):
    s = requests.Session()
    e = f"t_pn_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Notice QA", "email": e, "password": "testpass123", "role": role, "agreements_accepted": True, "organization": "QA", "pro_role": "Mediator"})
    assert r.status_code in (200, 201), r.text
    return s


def test_text_is_verbatim():
    assert NOTICE["tagline"] == "Start With Safety. Alignment Before Agreement."
    assert NOTICE["principle"] == "AI Structures Data. Professionals Evaluate. Courts Decide."
    assert [p["heading"] for p in NOTICE["points"]] == ["Confidentiality", "Family Violence and Safety", "Separate Parent Perspectives", "Artificial Intelligence", "Professional Responsibility", "Court Reports"]
    assert NOTICE["checkbox"].startswith("By continuing, I acknowledge that SA CoParents Align is a professional support tool")


def test_professional_gate_and_accept():
    s = _register("professional")
    g = s.get(f"{API}/professional-notice").json()
    assert g["needs_acceptance"] is True and g["notice"]["version"] == PROFESSIONAL_NOTICE_VERSION
    assert s.get(f"{API}/auth/me").json()["professional_notice_version"] is None
    assert s.post(f"{API}/professional-notice/accept", json={"version": PROFESSIONAL_NOTICE_VERSION, "acknowledged": False}).status_code == 400
    assert s.post(f"{API}/professional-notice/accept", json={"version": "old", "acknowledged": True}).status_code == 409
    r = s.post(f"{API}/professional-notice/accept", json={"version": PROFESSIONAL_NOTICE_VERSION, "acknowledged": True})
    assert r.status_code == 200 and r.json()["version"] == PROFESSIONAL_NOTICE_VERSION
    assert s.get(f"{API}/professional-notice").json()["needs_acceptance"] is False
    assert s.get(f"{API}/auth/me").json()["professional_notice_version"] == PROFESSIONAL_NOTICE_VERSION


def test_parent_not_gated():
    from casekit import completed_case
    _pro, pa, _pb, _d, _ = completed_case(API)
    assert pa.get(f"{API}/professional-notice").json()["needs_acceptance"] is False
    assert pa.get(f"{API}/admin/professional-notice/acceptances").status_code == 403
