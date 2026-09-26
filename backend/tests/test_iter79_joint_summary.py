"""Iter79 — Joint Records Ingestion in complete-report PDF + share complete
passphrase gate. Extends the iter78 suite with the new optional-auth
`joint_summary` path and its empty-state stub.
"""
from __future__ import annotations

import os
import re
import zlib
from datetime import datetime, timezone
from typing import Iterable

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Load backend .env so MONGO_URL / DB_NAME are available in the test env.
load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Pull rendered text from fpdf-produced PDF bytes.

    fpdf1/fpdf2 may compress content streams. Decompress every deflate
    stream and concatenate all `(text) Tj` tokens.
    """
    tokens: list[str] = []
    # Try decompress + fallback to raw. Iterate over each `stream ... endstream`.
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        raw = match.group(1)
        try:
            data = zlib.decompress(raw)
        except zlib.error:
            data = raw
        for tj in re.finditer(rb"\(((?:\\.|[^()\\])*)\)\s*Tj", data):
            token = tj.group(1)
            # Unescape common octal escapes.
            token = re.sub(rb"\\(\d{3})", lambda m: bytes([int(m.group(1), 8)]), token)
            token = token.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
            try:
                tokens.append(token.decode("latin-1", errors="ignore"))
            except Exception:
                pass
    return "\n".join(tokens)


def _all_in(needle_list: Iterable[str], hay: str) -> list[str]:
    return [n for n in needle_list if n.lower() not in hay.lower()]


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL, tz_aware=True)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module")
def auth_token():
    """Log in parent1@test.com, register on 401 fallback, return bearer token."""
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        rr = requests.post(
            f"{API}/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"},
            timeout=30,
        )
        if rr.status_code not in (200, 201):
            pytest.skip(f"cannot authenticate parent1: login={r.status_code} register={rr.status_code}")
        token = rr.json().get("access_token") or rr.json().get("token")
    else:
        token = r.json().get("access_token") or r.json().get("token")
    if not token:
        pytest.skip("no token returned by /auth/login")
    return token


@pytest.fixture(scope="module")
def user_id(auth_token):
    r = requests.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"/auth/me returned {r.status_code}")
    data = r.json()
    return data.get("user_id") or data.get("id") or data.get("_id")


# --------------------------------------------------------------------- #
# Item (A) — POST /api/portal/complete-report-pdf joint_summary path
# --------------------------------------------------------------------- #

def test_complete_report_unauth_shows_empty_joint_stub():
    r = requests.post(f"{API}/portal/complete-report-pdf", json={}, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF-")
    text = _extract_pdf_text(r.content)
    assert "Joint Alignment Summary" in text, f"missing heading; text={text[:400]}"
    assert "No joint alignment on file yet" in text
    # Sub-heading should NOT be present in the empty-state variant.
    assert "Shared Goals" not in text


def test_complete_report_auth_no_agreement_shows_empty_stub(auth_token, user_id, mongo_db):
    # Wipe any existing agreements docs for THIS user to ensure the fallback.
    mongo_db.agreements.delete_many({"user_id": user_id})
    r = requests.post(
        f"{API}/portal/complete-report-pdf",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    assert r.status_code == 200
    text = _extract_pdf_text(r.content)
    assert "Joint Alignment Summary" in text
    assert "No joint alignment on file yet" in text
    assert "Shared Goals" not in text


def test_complete_report_auth_with_seeded_agreement_renders_sections(
    auth_token, user_id, mongo_db
):
    mongo_db.agreements.delete_many({"user_id": user_id})
    now_iso = datetime.now(timezone.utc).isoformat()
    seed = {
        "user_id": user_id,
        "agreement_id": "TEST-ITER79",
        "generated_at": now_iso,
        "overview": "Sam and Riley agree to prioritise the child.",
        "shared_goals": ["Consistent bedtime", "Homework routine"],
        "communication": [
            {"agreement": "Use co-parenting app for scheduling"},
        ],
        "child_needs": [
            {"area": "Medical", "agreement": "Share pediatrician updates weekly"},
        ],
        "household_rules": [
            {"agreement": "No screens after 8pm at either home"},
        ],
        "priority_items": [
            {"agreement": "Finalise summer schedule by April"},
        ],
        "open_for_discussion": ["Holiday travel split"],
        "closing_note": "We commit to review this in 90 days.",
    }
    mongo_db.agreements.insert_one(dict(seed))
    try:
        r = requests.post(
            f"{API}/portal/complete-report-pdf",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        text = _extract_pdf_text(r.content)
        assert "Joint Alignment Summary" in text
        # Empty-state stub should NOT appear when we have data.
        assert "No joint alignment on file yet" not in text
        expected_headings = [
            "Shared Goals",
            "Communication",
            "Child Needs",
            "Household Rules",
            "Priority Items",
            "Open for Discussion",
        ]
        missing = _all_in(expected_headings, text)
        assert not missing, f"missing joint sub-headings: {missing}\nTEXT:\n{text}"
        # Bullet-prefixed item text
        assert "- Consistent bedtime" in text or "Consistent bedtime" in text
        assert "Use co-parenting app for scheduling" in text
        assert "Share pediatrician updates weekly" in text
        # Overview + closing note
        assert "Sam and Riley agree to prioritise the child." in text
        assert "We commit to review this in 90 days." in text
    finally:
        mongo_db.agreements.delete_many({"user_id": user_id, "agreement_id": "TEST-ITER79"})


def test_complete_report_auth_with_malformed_agreement_degrades(
    auth_token, user_id, mongo_db
):
    mongo_db.agreements.delete_many({"user_id": user_id})
    mongo_db.agreements.insert_one(
        {
            "user_id": user_id,
            "agreement_id": "TEST-ITER79-MALFORMED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "priority_items": [{"weird_key": "x"}, 42, None, "bare"],
            "shared_goals": None,
            "communication": "not-a-list",
        }
    )
    try:
        r = requests.post(
            f"{API}/portal/complete-report-pdf",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.content.startswith(b"%PDF-")
    finally:
        mongo_db.agreements.delete_many(
            {"user_id": user_id, "agreement_id": "TEST-ITER79-MALFORMED"}
        )


# --------------------------------------------------------------------- #
# Item (B) — share complete with passphrase + ttl_days=7
# --------------------------------------------------------------------- #

def test_share_complete_with_passphrase_and_ttl7():
    body = {
        "artefact_type": "complete",
        "payload": {"foundation_text": "Guarded complete report."},
        "passphrase": "demo42",
        "ttl_days": 7,
    }
    r = requests.post(f"{API}/portal/share", json=body, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("requires_passphrase") is True
    assert data.get("ttl_days") == 7
    share_id = data["share_id"]

    # No p → HTML gate
    r_gate = requests.get(f"{API}/portal/share/{share_id}.pdf", timeout=30)
    assert r_gate.status_code == 200
    assert "text/html" in r_gate.headers.get("content-type", "")

    # With correct p → PDF
    r_pdf = requests.get(f"{API}/portal/share/{share_id}.pdf?p=demo42", timeout=30)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"].startswith("application/pdf")
    assert r_pdf.content.startswith(b"%PDF-")
