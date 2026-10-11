"""Iter132 — Progress PDF, reminder settings, and completion alerts.

Covers:
  * GET /api/professional/court-codes/{case_id}/progress.pdf — JWT, owner-only, 1 page PDF.
  * GET /api/professional/joint-alignment/cases/{case_id}/progress.pdf — SA-DEMO01 for parent1.
  * GET/PUT /api/court-path/reminders — toggle persists; re-enable after unsubscribe.
  * Completion alert hook (foundation-builder save -> completion_alerts record).
"""
from __future__ import annotations

import asyncio
import io
import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

P1_EMAIL = "parent1@test.com"
P2_EMAIL = "parent2@test.com"
PWD = "TestPass123!"
SA_DEMO = "SA-DEMO01"


def _login(email: str, password: str = PWD) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pdf_info(data: bytes) -> dict:
    r = subprocess.run(["pdfinfo", "-"], input=data, capture_output=True, timeout=10)
    assert r.returncode == 0, r.stderr.decode()
    out = {}
    for line in r.stdout.decode().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _pdf_text(data: bytes) -> str:
    r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data, capture_output=True, timeout=10)
    assert r.returncode == 0, r.stderr.decode()
    return r.stdout.decode()


# ------------------------- Court code PDF -------------------------

@pytest.fixture(scope="module")
def p1_token() -> str:
    return _login(P1_EMAIL)


@pytest.fixture(scope="module")
def p2_token() -> str:
    return _login(P2_EMAIL)


@pytest.fixture(scope="module")
def owned_court_code(p1_token: str) -> str:
    """Create a transient court code owned by parent1; cleanup via revoke at module end."""
    label = f"TEST_iter132_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/professional/court-codes",
                      headers=_h(p1_token),
                      json={"label": label, "requested": ["foundation"], "valid_days": 30}, timeout=20)
    assert r.status_code == 200, r.text
    case_id = r.json()["case_id"]
    yield case_id
    try:
        requests.post(f"{API}/professional/court-codes/{case_id}/revoke", headers=_h(p1_token), timeout=10)
    except Exception:
        pass


def test_court_code_pdf_requires_auth():
    r = requests.get(f"{API}/professional/court-codes/anything/progress.pdf", timeout=10)
    assert r.status_code in (401, 403)


def test_court_code_pdf_owner_ok(p1_token: str, owned_court_code: str):
    r = requests.get(f"{API}/professional/court-codes/{owned_court_code}/progress.pdf",
                     headers=_h(p1_token), timeout=20)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert f"SA_CoParents_Progress_{owned_court_code}" in r.headers.get("content-disposition", "")
    info = _pdf_info(r.content)
    assert info.get("Pages") == "1", info
    text = _pdf_text(r.content)
    assert "Assessment Progress" in text
    assert f"Court code {owned_court_code}" in text
    assert "Active" in text
    assert "never shares" in text.lower() or "never shared" in text.lower()


def test_court_code_pdf_other_user_404(p2_token: str, owned_court_code: str):
    r = requests.get(f"{API}/professional/court-codes/{owned_court_code}/progress.pdf",
                     headers=_h(p2_token), timeout=10)
    assert r.status_code == 404


# ------------------------- Joint case PDF -------------------------

def test_joint_case_pdf_parent1(p1_token: str):
    r = requests.get(f"{API}/professional/joint-alignment/cases/{SA_DEMO}/progress.pdf",
                     headers=_h(p1_token), timeout=20)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    info = _pdf_info(r.content)
    assert info.get("Pages") == "1"
    text = _pdf_text(r.content)
    assert "Assessment Progress" in text
    assert SA_DEMO in text
    # Both seeded parents should appear
    assert "Sam Parent" in text
    assert "Riley Parent" in text
    assert "1 of 1 done" in text


def test_joint_case_pdf_other_user_404(p2_token: str):
    r = requests.get(f"{API}/professional/joint-alignment/cases/{SA_DEMO}/progress.pdf",
                     headers=_h(p2_token), timeout=10)
    assert r.status_code == 404


def test_joint_case_pdf_requires_auth():
    r = requests.get(f"{API}/professional/joint-alignment/cases/{SA_DEMO}/progress.pdf", timeout=10)
    assert r.status_code in (401, 403)


# ------------------------- Reminders toggle -------------------------

def test_reminders_requires_auth():
    r = requests.get(f"{API}/court-path/reminders", timeout=10)
    assert r.status_code in (401, 403)


def test_reminders_put_missing_body(p1_token: str):
    r = requests.put(f"{API}/court-path/reminders", headers=_h(p1_token), json={}, timeout=10)
    assert r.status_code == 422


def test_reminders_toggle_roundtrip():
    """Use a fresh user to avoid disrupting parent1/parent2."""
    email = f"TEST_iter132_rem_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": PWD, "name": "Rem User"}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]

    g = requests.get(f"{API}/court-path/reminders", headers=_h(tok), timeout=10)
    assert g.status_code == 200 and g.json() == {"enabled": True}

    off = requests.put(f"{API}/court-path/reminders", headers=_h(tok), json={"enabled": False}, timeout=10)
    assert off.status_code == 200
    g2 = requests.get(f"{API}/court-path/reminders", headers=_h(tok), timeout=10)
    assert g2.json() == {"enabled": False}

    on = requests.put(f"{API}/court-path/reminders", headers=_h(tok), json={"enabled": True}, timeout=10)
    assert on.status_code == 200
    g3 = requests.get(f"{API}/court-path/reminders", headers=_h(tok), timeout=10)
    assert g3.json() == {"enabled": True}


def test_reminders_reenable_after_unsubscribe():
    """Simulate email unsubscribe (sets reminders_off=True in DB), then PUT enabled:true re-enables."""
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _unsubscribe(uid: str) -> None:
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        await db.court_requested.update_one({"user_id": uid}, {"$set": {"reminders_off": True}}, upsert=True)
        client.close()

    email = f"TEST_iter132_unsub_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": PWD, "name": "Unsub User"}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    uid = r.json()["user"]["user_id"]

    asyncio.run(_unsubscribe(uid))
    g = requests.get(f"{API}/court-path/reminders", headers=_h(tok), timeout=10)
    assert g.json() == {"enabled": False}

    on = requests.put(f"{API}/court-path/reminders", headers=_h(tok), json={"enabled": True}, timeout=10)
    assert on.status_code == 200
    g2 = requests.get(f"{API}/court-path/reminders", headers=_h(tok), timeout=10)
    assert g2.json() == {"enabled": True}


# ------------------------- Completion alert hook -------------------------

def test_completion_alert_fires_once_on_foundation_save(p1_token: str):
    """Flow: parent1 creates in-app court code, fresh parent verifies, saves foundation — exactly one completion_alerts doc.

    A second save must NOT create another row.
    """
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _count(uid: str, case_id: str) -> list:
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        docs = await db.completion_alerts.find({"user_id": uid, "ref": case_id}, {"_id": 0}).to_list(None)
        client.close()
        return docs

    # 1. Pro creates a court code requesting only foundation.
    label = f"TEST_iter132_alert_{uuid.uuid4().hex[:6]}"
    cr = requests.post(f"{API}/professional/court-codes", headers=_h(p1_token),
                       json={"label": label, "requested": ["foundation"], "valid_days": 30}, timeout=20)
    assert cr.status_code == 200
    code = cr.json()["code"]
    case_id = cr.json()["case_id"]

    try:
        # 2. Fresh parent registers.
        pemail = f"TEST_iter132_pfam_{uuid.uuid4().hex[:8]}@test.com"
        rr = requests.post(f"{API}/auth/register",
                           json={"email": pemail, "password": PWD, "name": "Fam Parent"}, timeout=20)
        assert rr.status_code == 200, rr.text
        ptok = rr.json()["access_token"]
        puid = rr.json()["user"]["user_id"]

        # 3. Parent verifies code and sets portal state.
        v = requests.post(f"{API}/portal/court-keys/verify", headers=_h(ptok),
                          json={"key": code}, timeout=20)
        assert v.status_code == 200, v.text
        ps = requests.put(f"{API}/portal/state", headers=_h(ptok),
                          json={"court_key": case_id}, timeout=20)
        assert ps.status_code == 200, ps.text

        # 4. Parent saves foundation (completes it).
        fb = requests.put(f"{API}/foundation-builder/me", headers=_h(ptok),
                          json={"fields": {"vision": "A calm, child-focused home."}}, timeout=30)
        assert fb.status_code == 200, fb.text

        # 5. Give the fire-and-forget task up to ~5s to write.
        docs = []
        for _ in range(10):
            time.sleep(0.5)
            docs = asyncio.run(_count(puid, case_id))
            if docs:
                break
        assert len(docs) == 1, f"expected exactly one completion_alerts doc, got {docs}"
        doc = docs[0]
        assert doc["pro_user_id"]
        assert doc["status"] in ("sent", "failed", "skipped_no_email"), doc
        assert doc["ref"] == case_id
        assert doc["user_id"] == puid

        # 6. Save again — must not add a second record.
        fb2 = requests.put(f"{API}/foundation-builder/me", headers=_h(ptok),
                           json={"fields": {"vision": "Updated vision."}}, timeout=30)
        assert fb2.status_code == 200
        time.sleep(2.5)
        docs2 = asyncio.run(_count(puid, case_id))
        assert len(docs2) == 1, f"second save created extra alert: {docs2}"
    finally:
        # Clean the code
        requests.post(f"{API}/professional/court-codes/{case_id}/revoke",
                      headers=_h(p1_token), timeout=10)
