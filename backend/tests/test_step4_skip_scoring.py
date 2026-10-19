"""Step 4: "I'd rather not answer" is a skip, never a concern, except a skip on an immediate-danger,
physical/sexual-harm or harm-to-children question makes the result at least Amber (Level 2)."""
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

from safety_assessment_routes import (  # noqa: E402
    SECTION_1_QUESTIONS, SECTION_2_QUESTIONS, SKIP_FLOOR_S1_IDS, AssessmentSubmit, score_assessment,
)

API = "http://localhost:8001/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def answers(s1=None, s2=None, child=None):
    a1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
    a2 = {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in SECTION_2_QUESTIONS}
    return AssessmentSubmit(section_1={**a1, **(s1 or {})}, section_2={**a2, **(s2 or {})}, child_experience=child or {})


def level(**kw):
    return score_assessment(answers(**kw))["level"]


def test_baseline_is_level_4():
    assert level() == 4


def test_ordinary_skips_never_raise():
    assert level(s1={"s1_q3": "prefer_not", "s1_q6": "prefer_not", "s1_q27": "prefer_not"}) == 4
    assert level(s2={q["id"]: "prefer_not" for q in SECTION_2_QUESTIONS}) == 4
    assert level(child={"ce_q3": "prefer_not", "ce_q6": "prefer_not"}) == 4


def test_skip_on_danger_or_harm_question_is_at_least_amber():
    for qid in sorted(SKIP_FLOOR_S1_IDS):
        r = score_assessment(answers(s1={qid: "prefer_not"}))
        assert r["level"] == 2 and r["skip_floor_ids"] == [qid], qid
    for qid in ("ce_q1", "ce_q8"):
        assert level(child={qid: "prefer_not"}) == 2


def test_floor_never_lowers_a_red_result():
    assert level(s1={"s1_q1": "yes", "s1_q2": "prefer_not"}) == 1


def test_unsure_unchanged_and_counts_reported():
    assert level(s1={"s1_q2": "unsure"}) == 4
    r = score_assessment(answers(s1={"s1_q2": "prefer_not", "s1_q3": "prefer_not"}, s2={"s2_q1": "prefer_not"}))
    assert r["declined_count"] == 3 and r["section_1_declined_count"] == 2


def test_extension_skip_is_not_counted_as_answered():
    from lens_extensions import analyse_child_experience
    skipped = analyse_child_experience({"ce_q3": "prefer_not"})
    blank = analyse_child_experience({})
    assert skipped == blank


def test_saved_result_and_pdf_show_prefer_not():
    email = f"test_step4_{uuid.uuid4().hex[:8]}@example.com"
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Step Four",
                                                 "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=20)
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    body = answers(s1={"s1_q13": "prefer_not"}).model_dump()
    try:
        r = httpx.post(f"{API}/safety-assessment", json=body, headers=h, timeout=60)
        assert r.status_code == 200, r.text
        res = r.json()["result"]
        assert res["level"] == 2 and res["skip_floor_ids"] == ["s1_q13"] and res["section_1_declined_count"] == 1
        pdf = httpx.get(f"{API}/safety-assessment/{r.json()['assessment_id']}/pdf", headers=h, timeout=60)
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        from pypdf import PdfReader
        text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages).upper()
        assert "PREFER NOT TO ANSWER" in text
    finally:
        uid = db.users.find_one({"email": email})["user_id"]
        db.safety_assessments.delete_many({"user_id": uid})
        db.users.delete_many({"user_id": uid})
