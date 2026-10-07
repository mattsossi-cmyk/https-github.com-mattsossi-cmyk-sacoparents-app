import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import self_assessment_pdf  # noqa: E402
from self_assessment_routes import CONTENT, SAState, compute_scores  # noqa: E402

FRONTEND_COPY = Path("/app/frontend/src/pages/portal/selfAssessmentContent.json")


def test_frontend_backend_copy_in_lockstep():
    assert json.loads(FRONTEND_COPY.read_text(encoding="utf-8")) == CONTENT


def test_scores_and_tiers():
    assert compute_scores({})["tier"] is None
    assert compute_scores({"A1": 4, "A2": 3})["tier"] is None
    all_fours = {f"{s['key']}{i + 1}": 4 for s in CONTENT["sections"] for i in range(5)}
    res = compute_scores(all_fours)
    assert res["total"] == 120 and res["max"] == 120
    assert res["tier"]["title"].startswith("96")
    assert compute_scores({k: 2 for k in all_fours})["tier"]["title"].startswith("56")


def test_invalid_answers_are_dropped():
    state = SAState(answers={"A1": 3, "Z9": 4, "B2": 7})
    assert state.answers == {"A1": 3}


def test_pdf_renders():
    state = SAState(
        meta={"parent_name": "Jordan “JJ” Lee", "child": "Emma (8)"},
        answers={"A1": 4, "F5": 1},
        foundation={"going_well": ["School pickups — on time", "", ""], "shared_goals": "Stability"},
    ).model_dump()
    out = self_assessment_pdf.build_self_assessment_pdf(
        content=CONTENT, state=state, scores=compute_scores(state["answers"])
    )
    assert out[:4] == b"%PDF" and len(out) > 2000
