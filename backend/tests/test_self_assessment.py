import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import self_assessment_pdf  # noqa: E402
from self_assessment_routes import (  # noqa: E402
    CONTENT, QUESTION_KEYS, SADraft, band_for, compute_scores,
)

FRONTEND_COPY = Path("/app/frontend/src/pages/portal/selfAssessmentContent.json")


def test_frontend_backend_copy_in_lockstep():
    assert json.loads(FRONTEND_COPY.read_text(encoding="utf-8")) == CONTENT


def test_structure_matches_spec():
    assert len(CONTENT["sections"]) == 4
    assert all(len(s["questions"]) == 5 for s in CONTENT["sections"])
    assert [s["value"] for s in CONTENT["scale"]] == [1, 2, 3, 4, 5]
    assert len(CONTENT["reflection"]["questions"]) == 5


def test_scores_out_of_100():
    all_fives = {k: 5 for k in QUESTION_KEYS}
    res = compute_scores(all_fives)
    assert res["overall"] == 100 and set(res["sections"].values()) == {100}
    mixed = {**{k: 3 for k in QUESTION_KEYS}, "child_focus_1": 5}
    res = compute_scores(mixed)
    assert res["sections"]["child_focus"] == 68  # (5+3*4)=17 *4
    assert res["overall"] == 62  # 62 raw of 100
    assert compute_scores({})["overall"] == 0


def test_invalid_values_dropped():
    d = SADraft(answers={"child_focus_1": 3, "bogus_1": 4, "communication_2": 9},
                reflections={"going_better": "x", "nope": "y"})
    assert d.answers == {"child_focus_1": 3}
    assert d.reflections == {"going_better": "x"}


def test_bands_match_founder_ranges():
    assert band_for(100)["label"] == band_for(85)["label"] == "Consistent Strength"
    assert band_for(84)["label"] == "Growing Strength" and band_for(70)["label"] == "Growing Strength"
    assert band_for(69)["label"] == "Developing" and band_for(55)["label"] == "Developing"
    assert band_for(54)["label"] == "Building Foundations" and band_for(40)["label"] == "Building Foundations"
    assert band_for(39)["label"] == "Starting Point" and band_for(20)["label"] == "Starting Point"
    assert all(b.get("body") for b in CONTENT["bands"])


def test_reminder_due_logic():
    from datetime import datetime, timedelta, timezone
    from self_assessment_reminders import _due_kind, make_unsubscribe_token, read_unsubscribe_token
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert _due_kind(now - timedelta(days=41), {}, now) is None
    assert _due_kind(now - timedelta(days=42), {}, now) == "6w"
    assert _due_kind(now - timedelta(days=50), {"6w": now - timedelta(days=8)}, now) is None
    assert _due_kind(now - timedelta(days=56), {"6w": now - timedelta(days=14)}, now) == "8w"
    assert _due_kind(now - timedelta(days=70), {"6w": now - timedelta(days=3)}, now) is None
    assert _due_kind(now - timedelta(days=90), {"6w": now, "8w": now}, now) is None
    assert read_unsubscribe_token(make_unsubscribe_token("u1")) == "u1"
    assert read_unsubscribe_token("garbage") is None


def test_pdf_renders_with_history():
    def item(v, when):
        a = {k: v for k in QUESTION_KEYS}
        return {"completed_at": when, "parent_name": "Sam “SJ” Parent", "answers": a,
                "reflections": {"going_better": "Pickups — calmer"}, "goal": "Pause before replying",
                "scores": compute_scores(a)}
    history = [item(3, "2026-05-02T10:00:00+00:00"), item(4, "2026-07-02T10:00:00+00:00")]
    out = self_assessment_pdf.build_self_assessment_pdf(
        content=CONTENT, entry=history[-1], history=history, band_for=band_for
    )
    assert out[:4] == b"%PDF" and len(out) > 2000
    assert self_assessment_pdf.entry_label(history, 0) == "May 2026"
