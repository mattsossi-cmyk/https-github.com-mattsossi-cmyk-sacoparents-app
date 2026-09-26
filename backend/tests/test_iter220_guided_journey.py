"""Iter220 — Guided Journey Chat wizard (POST /api/portal/guided-journey/step).

Covers:
  * Intro turn (step_index=-1) for each of the six topics returns the
    scripted intro + first question + correct total_steps + save_key.
  * A follow-up turn (step_index=0) with a parent_answer returns a
    coach_message + next_question and step_number advances.
  * Final turn (step_index = total-1) returns is_final=true, next_question=None.
  * Grey-rock voice: safety_flagged=true → coach reply is shorter/factual
    (deterministic fallback if LLM fails still respects tone).
  * Save key mapping for align_record topics carries a `category`.
  * Bad topic → 422 (pydantic pattern validation).
  * Rate-limit: 45 rapid requests → at least one 429 (per-IP quota 40/hr).
  * Regression on PDF endpoints still returning application/pdf.
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as _f:
        for _line in _f:
            if _line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = _line.split("=", 1)[1].strip().rstrip("/")
                break
API = f"{BASE_URL}/api"

TOPIC_TOTALS = {
    "foundation": 5,
    "safety": 3,
    "coparenting": 5,
    "medical": 4,
    "educational": 4,
    "psychological": 4,
}

TOPIC_SAVE_KEYS = {
    "foundation": "foundation_text",
    "safety": "safety_ack",
    "coparenting": "cop_assessment_note",
    "medical": "align_record",
    "educational": "align_record",
    "psychological": "align_record",
}

ALIGN_CATEGORIES = {
    "medical": "Medical",
    "educational": "Educational",
    "psychological": "Psychological",
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------------------------------------------------------------- intro turn
@pytest.mark.parametrize("topic", list(TOPIC_TOTALS.keys()))
def test_intro_turn_returns_scripted_intro_and_first_question(s, topic):
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={"topic": topic, "step_index": -1, "parent_answer": "", "safety_flagged": False},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["coach_message"], "intro coach_message empty"
    assert d["next_question"], "first question missing"
    assert d["step_number"] == 1
    assert d["total_steps"] == TOPIC_TOTALS[topic]
    assert d["is_final"] is False
    assert d["save_key"] == TOPIC_SAVE_KEYS[topic]
    if topic in ALIGN_CATEGORIES:
        assert d["category"] == ALIGN_CATEGORIES[topic]
    else:
        assert d.get("category") in (None, "")


# ---------------------------------------------------------------- follow-up turn
def test_followup_turn_advances_step(s):
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={
            "topic": "foundation",
            "step_index": 0,
            "parent_answer": "My son is 7, thriving at school and loves piano.",
            "safety_flagged": False,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["coach_message"], "coach reply empty on follow-up"
    assert d["next_question"], "expected next question (foundation has 5)"
    assert d["step_number"] == 2
    assert d["total_steps"] == 5
    assert d["is_final"] is False
    assert d["save_key"] == "foundation_text"


# ---------------------------------------------------------------- final turn
def test_final_turn_flags_is_final(s):
    # medical has 4 questions → last answered index is 3
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={
            "topic": "medical",
            "step_index": 3,
            "parent_answer": "No allergies, next check-up in June.",
            "safety_flagged": False,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_final"] is True
    assert d["next_question"] in (None, "")
    assert d["step_number"] == 4
    assert d["total_steps"] == 4
    assert d["save_key"] == "align_record"
    assert d["category"] == "Medical"


# ---------------------------------------------------------------- grey-rock
def test_greyrock_voice_when_safety_flagged(s):
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={
            "topic": "foundation",
            "step_index": 0,
            "parent_answer": "Feels tense.",
            "safety_flagged": True,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    text = (d["coach_message"] or "").lower()
    # Grey-rock coach must not use warm affirmations
    assert "thanks" not in text, f"grey-rock reply contains 'thanks': {text!r}"
    # And should stay short (under ~30 words per prompt / deterministic fallback)
    assert len(text.split()) <= 45, f"grey-rock reply too long: {len(text.split())} words"


# ---------------------------------------------------------------- validation
def test_bad_topic_returns_422(s):
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={"topic": "nope", "step_index": -1, "parent_answer": ""},
        timeout=10,
    )
    assert r.status_code in (400, 422), r.text


def test_step_index_out_of_bounds_still_ok_or_400(s):
    # step_index within pydantic bounds but beyond script length →
    # implementation should either return is_final=True with no next_q
    # or bubble up gracefully. Not a 500.
    r = s.post(
        f"{API}/portal/guided-journey/step",
        json={"topic": "safety", "step_index": 10, "parent_answer": "x"},
        timeout=30,
    )
    assert r.status_code in (200, 400, 422), r.text
    assert r.status_code != 500


# ---------------------------------------------------------------- rate limit
def test_rate_limit_kicks_in(s):
    # 40/hr per-IP quota → burst 45 requests, expect at least one 429
    hits_429 = 0
    for _ in range(45):
        r = s.post(
            f"{API}/portal/guided-journey/step",
            json={"topic": "safety", "step_index": -1, "parent_answer": ""},
            timeout=10,
        )
        if r.status_code == 429:
            hits_429 += 1
            break
    assert hits_429 >= 1, "expected at least one 429 within 45 rapid calls"


# ---------------------------------------------------------------- PDF regression
@pytest.mark.parametrize(
    "endpoint",
    [
        "/portal/foundation-pdf",
        "/portal/legal-report-pdf",
        "/portal/weekly-progress-pdf",
        "/portal/complete-report-pdf",
    ],
)
def test_pdf_endpoints_stream_pdf(s, endpoint):
    # Wait so previous rate-limit burst doesn't spill over (biff quota
    # is separate but the shared _rate_guard is generous — still safe).
    time.sleep(1)
    r = s.post(
        f"{API}{endpoint}",
        json={
            "foundation_text": "TEST guided journey regression",
            "align_records": [],
            "milestones": [],
            "safety_ack": {"flagged": False},
            "biff_message": "Test",
            "coparent_first_name": "Alex",
            "child_first_name": "Sam",
            "commitments": [],
            "reassessment": {},
            "safety_screening": {},
        },
        timeout=60,
    )
    assert r.status_code == 200, f"{endpoint} → {r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
