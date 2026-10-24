"""Tests for AI Tip History in Self-Assessment PDF + Court Checklist (iteration 99)."""
from __future__ import annotations

import io
import re
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
P1 = {"email": "parent1@test.com", "password": "TestPass123!"}
P2 = {"email": "parent2@test.com", "password": "TestPass123!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def tok_p1():
    return _login(P1)


@pytest.fixture(scope="module")
def tok_p2():
    return _login(P2)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _pdf_text(blob: bytes) -> str:
    r = PdfReader(io.BytesIO(blob))
    return "\n".join(p.extract_text() or "" for p in r.pages)


# ---------------- framing storage ----------------
class TestFramingStorage:
    def test_framing_signed_in_stores_only_advice_and_suggested(self, tok_p2):
        secret = f"TEST_SECRET_MARKER_{uuid.uuid4().hex[:8]}"
        body = {"text": f"My ex said: {secret}. How should I reply?"}
        r = requests.post(f"{API}/self-assessment/ai/framing", json=body, headers=_h(tok_p2), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "advice" in data and "suggested" in data
        # Download PDF with empty history/entry (signed-in -> framing added)
        pdf_body = {
            "entry": {"completed_at": datetime.now(timezone.utc).isoformat(),
                      "parent_name": "Riley Parent", "answers": {}, "reflections": {}, "tips": {}, "goal": ""},
            "history": [],
        }
        pr = requests.post(f"{API}/self-assessment/pdf", json=pdf_body, headers=_h(tok_p2), timeout=60)
        assert pr.status_code == 200
        text = _pdf_text(pr.content)
        assert secret not in text, "User's framing input text leaked into PDF"
        assert "Ask AI for framing" in text

    def test_framing_anonymous_not_stored(self):
        r = requests.post(f"{API}/self-assessment/ai/framing",
                          json={"text": "Should I respond to a late pickup?"}, timeout=60)
        # AI features need a signed-in parent who accepted the AI notice: nothing is sent or stored for visitors.
        assert r.status_code == 401
        # And anon PDF has no framing rows
        pdf_body = {"entry": {"completed_at": datetime.now(timezone.utc).isoformat(),
                              "parent_name": "Anon", "answers": {}, "reflections": {}, "tips": {}, "goal": ""},
                    "history": []}
        pr = requests.post(f"{API}/self-assessment/pdf", json=pdf_body, timeout=60)
        assert pr.status_code == 200
        text = _pdf_text(pr.content)
        assert "Ask AI for framing" not in text


# ---------------- tip history in PDF ----------------
class TestTipHistoryPdf:
    def test_history_tips_render_newest_first_with_date_prefix(self, tok_p2):
        # Older entry (section tip) + newer entry (overall tip)
        older = {
            "completed_at": "2026-05-10T10:00:00+00:00",
            "parent_name": "Riley Parent",
            "answers": {}, "reflections": {},
            "tips": {"child_focus": "TEST_SECTION_TIP_CHILD"},
            "goal": "",
        }
        newer = {
            "completed_at": "2026-10-08T10:00:00+00:00",
            "parent_name": "Riley Parent",
            "answers": {}, "reflections": {},
            "tips": {"overall": "TEST_OVERALL_TIP_NEWER", "communication": "TEST_SECTION_TIP_COMM"},
            "goal": "",
        }
        body = {"entry": newer, "history": [older, newer]}
        r = requests.post(f"{API}/self-assessment/pdf", json=body, headers=_h(tok_p2), timeout=60)
        assert r.status_code == 200
        text = _pdf_text(r.content)
        assert "Your AI Tip History" in text
        assert "TEST_OVERALL_TIP_NEWER" in text
        assert "TEST_SECTION_TIP_CHILD" in text
        assert "TEST_SECTION_TIP_COMM" in text
        # Overall tip should be labelled 'Self-Assessment · Your results'
        assert "Your results" in text
        # Newest first: newer overall tip appears before older child-focus tip
        pos_new = text.find("TEST_OVERALL_TIP_NEWER")
        pos_old = text.find("TEST_SECTION_TIP_CHILD")
        assert 0 <= pos_new < pos_old
        # Within newer entry, overall tip comes before section tips
        pos_overall = text.find("TEST_OVERALL_TIP_NEWER")
        pos_comm = text.find("TEST_SECTION_TIP_COMM")
        assert 0 <= pos_overall < pos_comm
        # Date prefix like 'Oct 8, 2026'
        assert "Oct 8, 2026" in text
        assert "May 10, 2026" in text

    def test_pdf_no_tips_omits_section(self):
        body = {"entry": {"completed_at": "2026-01-01T00:00:00+00:00",
                          "parent_name": "Anon", "answers": {}, "reflections": {}, "tips": {}, "goal": ""},
                "history": []}
        r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
        assert r.status_code == 200
        text = _pdf_text(r.content)
        assert "Your AI Tip History" not in text
        # Old per-entry section replaced
        assert "Tips from your AI Guide" not in text


# ---------------- court checklist JSON ----------------
class TestCourtChecklistJson:
    def test_auth_required(self):
        r = requests.post(f"{API}/court-path/checklist", json={}, timeout=15)
        assert r.status_code == 401

    def test_checklist_shape_and_keys(self, tok_p2):
        r = requests.post(
            f"{API}/court-path/checklist",
            json={},
            headers=_h(tok_p2), timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 7
        assert len(data["items"]) == 7
        keys = [i["key"] for i in data["items"]]
        assert keys == ["case", "family_checkin", "card1", "card2", "card3", "card4", "biff"]
        for it in data["items"]:
            assert set(it.keys()) >= {"key", "label", "status", "detail", "hint"}
            assert it["status"] in {"done", "in_progress", "todo"}
        m = {i["key"]: i for i in data["items"]}
        assert m["family_checkin"]["label"] == "Safety First"
        assert m["family_checkin"]["status"] in {"done", "todo"}
        # case ref for parent2 (preseeded COURT-8842)
        assert "case_ref" in data

    def test_family_checkin_item_is_neutral(self, tok_p1):
        r = requests.post(f"{API}/court-path/checklist", json={}, headers=_h(tok_p1), timeout=20)
        assert r.status_code == 200
        item = next(i for i in r.json()["items"] if i["key"] == "family_checkin")
        assert item["detail"] in {"", "Done"}
        for word in ["flag", "unsafe", "risk", "screening"]:  # "Safety First" is the step's name
            assert word not in (item["detail"] + item["hint"] + item["label"]).lower()


# ---------------- court checklist PDF ----------------
class TestCourtChecklistPdf:
    def test_pdf_auth_required(self):
        r = requests.post(f"{API}/court-path/checklist/pdf", json={}, timeout=15)
        assert r.status_code == 401

    def test_pdf_structure(self, tok_p2):
        r = requests.post(
            f"{API}/court-path/checklist/pdf",
            json={},
            headers=_h(tok_p2), timeout=30,
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "SA_CoParents_Court_Checklist.pdf" in r.headers.get("content-disposition", "")
        reader = PdfReader(io.BytesIO(r.content))
        assert len(reader.pages) == 1, "Must be a one-page PDF"
        text = _pdf_text(r.content)
        assert "Court Path Checklist" in text
        assert re.search(r"\d+ of \d+ done", text)
        assert "What's left" in text or "Everything on this checklist is done" in text
        assert "Notes for my mediator meeting" in text
        assert "not a legal document" in text
        assert "Module A" not in text
        # Row labels (a parent with professional-requested items only sees case, check-in and those items)
        labels = ["Case code verified", "Safety step:"]  # the check-in row carries only the safety-step line
        if "asked for" not in text:
            labels += ["Self-Assessment", "Co-Parenting Relationship assessment", "Child Needs", "Foundation Statement",
                       "BIFF messages saved"]
        for label in labels:
            assert label in text, f"Missing row label: {label}"


# ---------------- regression: existing SA/framing endpoints ----------------
class TestRegression:
    def test_sa_history_still_works(self, tok_p2):
        r = requests.get(f"{API}/self-assessment/history", headers=_h(tok_p2), timeout=15)
        assert r.status_code == 200
        assert "entries" in r.json()

    def test_framing_endpoint_returns_shape(self, tok_p2):
        r = requests.post(f"{API}/self-assessment/ai/framing",
                          json={"text": "I want to send a short pickup logistics message."},
                          headers=_h(tok_p2), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "advice" in d and "suggested" in d


# ---------------- cleanup ----------------
@pytest.fixture(scope="session", autouse=True)
def _cleanup_framing_docs():
    """Remove any framing docs we created during this run."""
    yield
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _run():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            # Remove docs we created in the test session for parent2
            user = await db.users.find_one({"email": P2["email"]}, {"_id": 0, "user_id": 1})
            if user:
                await db.self_assessment_framing_tips.delete_many(
                    {"user_id": user["user_id"], "created_at": {"$gte": (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()}}
                )
            client.close()

        asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        print(f"cleanup skipped: {exc}")
