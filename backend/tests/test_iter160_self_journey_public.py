"""Iter160: Self Journey PDF + guide chat (safety_status) + calm mode, against the public preview URL."""
import io
import os
import re
import uuid

import pytest
import requests
from dotenv import dotenv_values

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _pdf_text(raw: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)


@pytest.fixture(scope="module")
def parent():
    email = f"test_sj160_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST Sj Parent",
                                                    "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


# PDF auth
def test_pdf_requires_auth():
    assert requests.get(f"{API}/self-journey/pdf").status_code == 401


# PDF content: 7 sections, approved foundation, no private notes, no safety pick
def test_pdf_content(parent):
    progress = {
        "maxStepReached": 7,
        "safety": {"status": "concern", "completedAt": "2026-01-01T00:00:00Z"},
        "situation": {"currentSituation": "PRIVATESITUATIONXYZ"},
        "coparenting": {"approach": "parallel", "agree": "PRIVATEAGREEXYZ", "disagree": ""},
        "childNeeds": {"opened": ["educational", "medical"]},
        "foundation": {"answers": {"values": "kindness"}, "draft": "Our child comes first in every choice.",
                       "approved": True, "approvedAt": "2026-01-02T00:00:00Z"},
        "mediation": {"issues": "PRIVATEMEDIATIONXYZ"},
    }
    assert parent.put(f"{API}/self-journey/me", json=progress).status_code == 200
    r = parent.get(f"{API}/self-journey/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert "SA_CoParents_Self_Journey.pdf" in r.headers.get("content-disposition", "")
    text = re.sub(r"\s+", " ", _pdf_text(r.content))
    for t in ["Parenting Situation Overview", "Self Assessment Reflections", "Co-Parenting Relationship",
              "Child's Identified Needs", "Foundation Statement", "Mediation Preparation & Options",
              "Next Steps & Available Resources"]:
        assert t in text, t
    assert "Our child comes first in every choice." in text
    for secret in ["PRIVATESITUATIONXYZ", "PRIVATEAGREEXYZ", "PRIVATEMEDIATIONXYZ"]:
        assert secret not in text
    assert "concern" not in text.lower()
    for num in ["210-733-8810", "210-631-0100", "210-533-2729", "1-800-799-7233"]:
        assert num in text


# Unapproved draft never printed
def test_pdf_unapproved_draft_hidden(parent):
    p = parent.get(f"{API}/self-journey/me").json()["progress"]
    p["foundation"] = {"answers": {}, "draft": "UNAPPROVEDDRAFTXYZ", "approved": False, "approvedAt": None}
    parent.put(f"{API}/self-journey/me", json=p)
    text = _pdf_text(parent.get(f"{API}/self-journey/pdf").content)
    assert "UNAPPROVEDDRAFTXYZ" not in text
    assert "Not approved yet" in text


# Guide chat: invalid safety_status rejected, concern reply works (multi-turn)
def test_chat_safety_status(parent):
    ack = parent.post(f"{API}/ai-notice/ack")
    assert ack.status_code == 200, ack.text
    bad = parent.post(f"{API}/journey-guide/self-journey/chat", json={"message": "hi", "safety_status": "safe"})
    assert bad.status_code == 422
    r = parent.post(f"{API}/journey-guide/self-journey/chat", json={
        "message": "Am I safe? Should I meet my ex in person to talk it through?", "section": "Safety",
        "safety_status": "concern", "safety_flagged": True}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["reply"] and d["session_id"]
    print("REPLY1:", d["reply"])
    r2 = parent.post(f"{API}/journey-guide/self-journey/chat", json={
        "message": "What about a joint session with a mediator together?", "session_id": d["session_id"],
        "section": "Mediation", "safety_status": "concern", "safety_flagged": True}, timeout=90)
    assert r2.status_code == 200, r2.text
    assert r2.json()["session_id"] == d["session_id"]
    print("REPLY2:", r2.json()["reply"])


# Calm mode toggle
def test_calm_mode(parent):
    r = parent.put(f"{API}/auth/calm-mode", json={"on": True})
    assert r.status_code == 200 and r.json()["calm_mode"] is True
    r = parent.put(f"{API}/auth/calm-mode", json={"on": False})
    assert r.status_code == 200 and r.json()["calm_mode"] is False


# Case settings for a fresh parent: no Align confirmation
def test_case_settings_fresh(parent):
    r = parent.get(f"{API}/case-settings")
    assert r.status_code == 200
    print("CASE_SETTINGS:", r.json())
    assert not r.json().get("setup_complete")
