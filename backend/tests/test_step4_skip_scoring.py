"""Step 4: "I'd rather not answer" is a plain skip. It never raises (or lowers) the level, never flags,
never blocks anything, and shows as "Skipped" in the PDF. The quick check stores the skip count."""
import io
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from safety_assessment_routes import SECTION_1_QUESTIONS, SECTION_2_QUESTIONS, AssessmentSubmit, score_assessment  # noqa: E402
from portal_routes import _sanitize_safety_ack  # noqa: E402

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
DANGER = ("s1_q1", "s1_q2", "s1_q11", "s1_q12", "s1_q13", "s1_q14", "s1_q15", "s1_q19", "s1_q20", "s1_q21", "s1_q25", "s1_q26")


def answers(s1=None, s2=None, child=None):
    a1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
    a2 = {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in SECTION_2_QUESTIONS}
    return AssessmentSubmit(section_1={**a1, **(s1 or {})}, section_2={**a2, **(s2 or {})}, child_experience=child or {})


def score(**kw):
    return score_assessment(answers(**kw))


def test_baseline_is_level_4():
    assert score()["level"] == 4


def test_no_skip_ever_changes_the_level():
    assert score(s1={q: "prefer_not" for q in DANGER})["level"] == 4
    assert score(s1={q["id"]: "prefer_not" for q in SECTION_1_QUESTIONS})["level"] == 4
    assert score(s2={q["id"]: "prefer_not" for q in SECTION_2_QUESTIONS})["level"] == 4
    assert score(child={"ce_q1": "prefer_not", "ce_q8": "prefer_not"})["level"] == 4
    assert score(s1={"s1_q1": "yes", "s1_q2": "prefer_not"})["level"] == score(s1={"s1_q1": "yes"})["level"]


def test_result_has_counts_and_no_floor():
    r = score(s1={"s1_q2": "prefer_not", "s1_q3": "prefer_not"}, s2={"s2_q1": "prefer_not"})
    assert r["declined_count"] == 3 and r["section_1_declined_count"] == 2 and "skip_floor_ids" not in r
    assert r["high_concern_hits"] == [] and r["coercive_hits"] == [] and r["section_1_yes_count"] == 0 and r["section_2_concern_count"] == 0


def test_extension_skip_is_not_counted_as_answered():
    from lens_extensions import analyse_child_experience
    assert analyse_child_experience({"ce_q3": "prefer_not"}) == analyse_child_experience({})


def test_quick_check_skip_count_is_stored_only_when_valid():
    base = {"cleared": True, "flagged": False, "date": "2026-10-19T00:00:00Z"}
    assert _sanitize_safety_ack({**base, "skipped": 2}) == {**base, "skipped": 2}
    for bad in (0, 4, "2", True, None):
        assert "skipped" not in _sanitize_safety_ack({**base, "skipped": bad})


def test_saved_result_pdf_says_skipped_and_invite_not_blocked():
    email = f"test_step4_{uuid.uuid4().hex[:8]}@example.com"
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Step Four", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = db.users.find_one({"email": email})["user_id"]
    try:
        r = httpx.post(f"{API}/safety-assessment", json=answers(s1={q: "prefer_not" for q in DANGER}).model_dump(), headers=h, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["result"]["level"] == 4
        pdf = httpx.get(f"{API}/safety-assessment/{r.json()['assessment_id']}/pdf", headers=h, timeout=90)
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        from pypdf import PdfReader
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages).upper()
        assert "SKIPPED" in text and "PREFER NOT TO ANSWER" not in text
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from self_assessment_reminders import is_safety_flagged

        async def flagged():
            c = AsyncIOMotorClient(os.environ["MONGO_URL"])
            try:
                return await is_safety_flagged(c[os.environ["DB_NAME"]], uid)
            finally:
                c.close()
        assert asyncio.run(flagged()) is False
    finally:
        db.safety_assessments.delete_many({"user_id": uid})
        db.users.delete_many({"user_id": uid})
