"""Iter-116: Google linked badge/unlink; AI-assistance line on the court packet transmittal."""
import os

import pymongo
import pymupdf
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402

import court_packets as cp  # noqa: E402
from pdf_report import build_transmittal_pdf  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_google_linked_badge_field_and_unlink():
    pro, pa, pb, rid = _case()
    uid = pro.get(f"{API}/auth/me").json()["id"]
    assert pro.get(f"{API}/auth/me").json()["google_linked_at"] is None
    _db.users.update_one({"_id": uid}, {"$set": {"google_linked_at": "2026-10-17T00:00:00+00:00", "google_picture": ""}})
    assert pro.get(f"{API}/auth/me").json()["google_linked_at"].startswith("2026-10-17")
    r = pro.delete(f"{API}/auth/google/link")
    assert r.status_code == 200 and r.json()["ok"]
    assert pro.get(f"{API}/auth/me").json()["google_linked_at"] is None
    assert requests.delete(f"{API}/auth/google/link").status_code == 401
    assert "google-linked-badge" in open("/app/frontend/src/components/ProContactCard.jsx").read()


def test_transmittal_ai_disclosure_lists_exact_models_or_none():
    assert cp._ai_disclosure({}).startswith("AI drafting assistance: none")
    text = cp._ai_disclosure({"ai_joint_draft": {"status": "approved", "model": "Gemini 3.1 Pro"}, "agreement_ai": {"sections": {"x": 1}, "model": "gpt-5.4-mini"},
                              "ai_drafts": {"joint_notes": {"model": "Claude Sonnet 5.5"}, "goals": {"model": "GPT-5.5"}}})
    assert "Claude Sonnet 5.5" in text and "GPT-5.5" in text and "Gemini 3.1 Pro" in text and "gpt-5.4-mini" in text and "approved by the transmitting professional" in text
    assert "no finding or recommendation" in text
    assert cp._ai_disclosure({"ai_joint_draft": {"status": "draft", "model": "Gemini 3.1 Pro"}}).startswith("AI drafting assistance: none")  # unapproved draft not disclosed as used
    pdf = build_transmittal_pdf({"id": "abcdef1234", "professional": {"name": "Pro"}, "judge_name": "J", "judge_email": "j@x", "created_at": "2026-10-17T00:00:00+00:00", "expires_at": "2026-11-17T00:00:00+00:00",
                                 "enclosures": ["Professional Report"], "events": [], "ai_disclosure": text})
    out = "\n".join(p.get_text() for p in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "AI drafting assistance" in out and "Claude Sonnet 5.5" in out
