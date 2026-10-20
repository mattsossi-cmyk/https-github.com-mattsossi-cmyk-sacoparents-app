"""Part 3 spot-checks via the public preview URL (parent1): safety-step wording in PDFs, prep never returns safety text."""
import io
import os

import pytest
import requests
from dotenv import dotenv_values
from pypdf import PdfReader

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def pdf_text(b):
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)


@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{API}/auth/login", json={"email": "parent1@test.com", "password": "TestPass123!"}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# Complete report PDF wording
def test_complete_report_pdf_wording(h):
    r = requests.post(f"{API}/portal/complete-report-pdf", headers=h, json={}, timeout=90)
    assert r.status_code == 200, r.text[:300]
    t = pdf_text(r.content)
    assert "Safety step: not started" not in t
    assert ("Safety step: see SACOparentsAlign" in t) or ("Safety step: completed on SACOparentsAlign" in t)


# Court checklist PDF wording
def test_court_checklist_pdf_wording(h):
    r = requests.post(f"{API}/court-path/checklist/pdf", headers=h, json={}, timeout=90)
    assert r.status_code == 200, r.text[:300]
    t = pdf_text(r.content)
    assert "not started" not in t.lower() or "Safety step: not started" not in t


# Mediation prep GET has no safety_concerns key
def test_prep_never_returns_safety(h):
    r = requests.get(f"{API}/mediation/prep", headers=h, timeout=30)
    assert r.status_code == 200
    items = ((r.json() or {}).get("issues") or {}).get("items") or {}
    assert "safety_concerns" not in items


# Gate for parent1 (no old result) is clear-shaped
def test_gate_shape(h):
    r = requests.get(f"{API}/invites/coparent/gate", headers=h, timeout=30)
    assert r.status_code == 200
    assert "clear" in r.json()


# Old share token (no 'clean' claim) -> 410 via public URL
def test_old_share_token_410_public(h):
    import sys
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    from auth import create_share_token
    s = requests.get(f"{API}/mediation/summaries", headers=h, timeout=30).json()
    s = s if isinstance(s, list) else s.get("summaries", [])
    if not s:
        pytest.skip("no summary")
    me = requests.get(f"{API}/auth/me", headers=h, timeout=30).json()
    old = create_share_token("summary", s[0]["summary_id"], me.get("user_id") or me.get("user", {}).get("user_id"))
    r = requests.get(f"{API}/mediation/shared/{old}", timeout=30)
    assert r.status_code == 410
    assert "made before a privacy update" in r.json()["detail"]


# Old concerning result -> neutral gate + 403 compare via public URL; professional lift clears it
def test_gate_hold_and_lift_public():
    import sys
    sys.path.insert(0, "/app/backend")
    import tests.test_part3_privacy as p3
    a, ha, _ = p3.user()
    b, hb, b_email = p3.user()
    try:
        p3.old_result(a, 1)
        g = requests.get(f"{API}/invites/coparent/gate", headers=ha, timeout=30).json()
        assert g == {"clear": False, "code": "not_available", "message": p3.NOT_AVAILABLE}
        r = requests.post(f"{API}/snc2/compare/link", headers=ha, json={"email": b_email}, timeout=30)
        assert r.status_code == 403 and r.json()["detail"] == p3.NOT_AVAILABLE
        p3.case_for(a, b, set_by="default")
        assert requests.get(f"{API}/invites/coparent/gate", headers=ha, timeout=30).json()["clear"] is False
        p3.case_for(a, b, set_by="professional")
        assert requests.get(f"{API}/invites/coparent/gate", headers=ha, timeout=30).json() == {"clear": True, "code": "ok"}
    finally:
        db = p3.db
        db.safety_assessments.delete_many({"user_id": {"$in": [a, b]}})
        db[p3.cs.COLL].delete_many({"case_id": {"$in": p3._cases}})
        db[p3.cs.AUDIT].delete_many({"case_id": {"$in": p3._cases}})
        db.joint_alignment_cases.delete_many({"case_id": {"$in": p3._cases}})
        db.users.delete_many({"email": {"$in": p3._emails}})
