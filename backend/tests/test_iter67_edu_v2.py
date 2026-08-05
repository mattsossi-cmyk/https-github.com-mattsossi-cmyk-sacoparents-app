"""Iteration 67 tests — Educational Deep Dive v2 (Special-Ed / ADHD).

The old 12-section 60-item diagnostic was replaced with a 25-item
5-part alignment scorer (0-4 likert, /100 total, three interpretation
bands). This suite covers:

* Schema shape (5 sections, 5 items each, all alignment likert).
* validate_answer accepts 0-4 + "na" and rejects everything else.
* score_deep_dive:
    - empty responses → percent=0, band="unrated".
    - all-4 responses → 100/100, band="high".
    - all-2 responses → 50/100, band="low" (boundary).
    - all-3 responses → 75/100, band="moderate".
    - all-4 responses with 5 N/A → still 100% (pro-rated).
    - Band-boundary tests at 51 and 81.
* Legacy v1 answers (`s1_school_setting`, etc.) are silently wiped on
  first GET /edu-deep/me so the new schema doesn't crash.
* build_journey_report returns the v2 score_card block and does not
  reference retired v1 keys.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1,
    _client, _ensure_account, _run,
    MONGO_URL, DB_NAME,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


def _reset_edu():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["edu_deep_assessments"].delete_many({})
            await db["edu_deep_reports"].delete_many({})
        finally:
            c.close()
    _run(_r())


@pytest.fixture(autouse=True)
def _cleanup():
    _reset_edu()
    yield
    _reset_edu()


def _all_answers(value):
    """Every v2 key mapped to the same answer — handy for whole-form fills."""
    from edu_deep_questions import all_item_keys
    return {k: value for k in all_item_keys()}


# ---------------------------------------------------------------------------
# 1. Schema
# ---------------------------------------------------------------------------
class TestSchema:

    def test_version_is_v2(self):
        from edu_deep_questions import DEEP_DIVE_VERSION
        assert DEEP_DIVE_VERSION.startswith("edu-deep-2.")

    def test_five_parts_five_items_each(self):
        from edu_deep_questions import public_schema
        schema = public_schema()
        parts = schema["sections"]
        assert len(parts) == 5
        for idx, part in enumerate(parts, start=1):
            assert part["number"] == idx
            assert part["id"] == f"p{idx}"
            assert len(part["items"]) == 5
            for item in part["items"]:
                assert item["type"] == "alignment"
                assert item["scale"] == [0, 1, 2, 3, 4]
                assert item["allow_na"] is True

    def test_total_items_is_25(self):
        from edu_deep_questions import all_item_keys
        assert len(all_item_keys()) == 25


# ---------------------------------------------------------------------------
# 2. validate_answer
# ---------------------------------------------------------------------------
class TestValidateAnswer:

    @pytest.mark.parametrize("v", [0, 1, 2, 3, 4, "na"])
    def test_accepts_valid(self, v):
        from edu_deep_questions import validate_answer
        assert validate_answer("p1_q1", v)

    @pytest.mark.parametrize("v", [-1, 5, 10, "5", True, False, None,
                                    [], {}, "yes"])
    def test_rejects_invalid(self, v):
        from edu_deep_questions import validate_answer
        assert not validate_answer("p1_q1", v)

    def test_unknown_key_rejected(self):
        from edu_deep_questions import validate_answer
        assert not validate_answer("s1_school_setting", 3)
        assert not validate_answer("p9_q99", 3)


# ---------------------------------------------------------------------------
# 3. score_deep_dive
# ---------------------------------------------------------------------------
class TestScoreDeepDive:

    def test_empty_is_unrated(self):
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive({})
        assert s["total"] == 0
        assert s["percent"] == 0
        assert s["band"] == "unrated"
        assert s["answered"] == 0
        assert len(s["sections"]) == 5

    def test_all_fours_is_100_percent_high(self):
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(4))
        assert s["total"] == 100
        assert s["percent"] == 100
        assert s["band"] == "high"
        assert s["band_label"] == "High Alignment"
        assert s["answered"] == 25
        # Every section should be 100% and "high"
        for row in s["sections"]:
            assert row["percent"] == 100
            assert row["band"] == "high"

    def test_all_zeros_is_zero_percent_low(self):
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(0))
        assert s["total"] == 0
        assert s["percent"] == 0
        assert s["band"] == "low"
        assert s["band_label"] == "Low Alignment"
        assert s["answered"] == 25  # 0 counts as answered

    def test_all_twos_boundary_50_is_low(self):
        """0-50 = Low. Exactly 50 must land in Low."""
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(2))
        assert s["percent"] == 50
        assert s["band"] == "low"

    def test_all_threes_75_percent_is_moderate(self):
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(3))
        assert s["percent"] == 75
        assert s["band"] == "moderate"
        assert s["band_label"] == "Moderate Alignment"

    def test_moderate_boundary_51_is_moderate(self):
        """51-80 = Moderate. A hand-crafted 51%. 25 items × 4 = 100 max.
        20 fours + 5 zeros = 80/100 = 80% (still moderate). Grab a mix
        that lands exactly at 51%.
        20 items at 2 + 5 items at 4 = 40+20 = 60 out of 100 = 60%.
        Let's target 51%: 51/100 with 25 items × 4 = 100 max. Need total=51.
        e.g. 12 fours + 1 three + 12 zeros: 48+3 = 51.
        """
        from edu_deep_scoring import score_deep_dive
        from edu_deep_questions import all_item_keys
        keys = all_item_keys()
        answers = {k: 0 for k in keys}
        for k in keys[:12]:
            answers[k] = 4
        answers[keys[12]] = 3
        s = score_deep_dive(answers)
        assert s["total"] == 51
        assert s["percent"] == 51
        assert s["band"] == "moderate"

    def test_high_boundary_81_is_high(self):
        """81-100 = High. 20 fours + 1 one + 4 zeros = 81/100 = 81%."""
        from edu_deep_scoring import score_deep_dive
        from edu_deep_questions import all_item_keys
        keys = all_item_keys()
        answers = {k: 0 for k in keys}
        for k in keys[:20]:
            answers[k] = 4
        answers[keys[20]] = 1
        s = score_deep_dive(answers)
        assert s["total"] == 81
        assert s["percent"] == 81
        assert s["band"] == "high"

    def test_na_is_prorated_not_penalised(self):
        """20 items at 4 + 5 N/A should still be 100% (20/20 possible)."""
        from edu_deep_scoring import score_deep_dive
        from edu_deep_questions import all_item_keys
        keys = all_item_keys()
        answers = {}
        for i, k in enumerate(keys):
            answers[k] = 4 if i < 20 else "na"
        s = score_deep_dive(answers)
        assert s["answered"] == 20
        assert s["na"] == 5
        assert s["total"] == 80
        assert s["possible"] == 80
        assert s["percent"] == 100
        assert s["band"] == "high"

    def test_backwards_compat_shape(self):
        """Downstream code still gets `sections`, `totals`, `is_texas`."""
        from edu_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(4))
        assert "sections" in s
        assert "totals" in s
        assert "is_texas" in s
        assert s["totals"]["strengths"] == 5
        assert s["totals"]["flagged"] == 0

    def test_next_steps_present_per_band(self):
        from edu_deep_scoring import score_deep_dive
        for value, expected_band in [(0, "low"), (2, "low"),
                                      (3, "moderate"), (4, "high")]:
            s = score_deep_dive(_all_answers(value))
            assert s["band"] == expected_band
            assert isinstance(s["next_steps"], list)
            assert s["next_steps"], f"Band {expected_band} must have next steps"


# ---------------------------------------------------------------------------
# 4. Legacy answers are silently wiped on load
# ---------------------------------------------------------------------------
class TestLegacyWipe:

    def test_v1_keys_are_dropped_on_me_load(self, p1_client):
        """Seed an assessment doc with old v1 keys, then hit /edu-deep/me
        and confirm they're stripped and completed=False."""
        # Save an v1-style answer via internal Mongo (bypasses validation)
        async def _seed():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                r = p1_client.get(f"{BASE_URL}/api/auth/me", timeout=15)
                uid = r.json()["user_id"]
                await c[DB_NAME]["edu_deep_assessments"].insert_one({
                    "user_id": uid,
                    "responses": {
                        "s1_school_setting": "Public School",
                        "s4_has_iep": "Yes",
                        "p1_q1": 3,   # a valid v2 answer stays
                    },
                    "completed": True,
                })
            finally:
                c.close()
        _run(_seed())

        r = p1_client.get(f"{BASE_URL}/api/edu-deep/me", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["has_assessment"] is True
        responses = body["assessment"]["responses"]
        assert "s1_school_setting" not in responses
        assert "s4_has_iep" not in responses
        assert responses.get("p1_q1") == 3
        # `completed` must be reset because a partial legacy state was dropped
        assert body["assessment"]["completed"] is False


# ---------------------------------------------------------------------------
# 5. Journey report is v2-shaped and doesn't blow up
# ---------------------------------------------------------------------------
class TestJourneyReport:

    def test_report_carries_score_card(self):
        from edu_deep_journey import build_journey_report
        rpt = build_journey_report(
            parent_name="Sam",
            child_name="Riley",
            responses=_all_answers(4),
        )
        assert "score_card" in rpt
        assert rpt["score_card"]["percent"] == 100
        assert rpt["score_card"]["band"] == "high"
        # Support summary still has 5 ratings so the existing React
        # ratings section keeps rendering.
        assert len(rpt["support_summary"]["ratings"]) == 5
        assert all(r["rating"] == "Strong"
                   for r in rpt["support_summary"]["ratings"])

    def test_report_action_plan_lists_lowest_first(self):
        from edu_deep_journey import build_journey_report
        from edu_deep_questions import all_item_keys
        # Make p3 the weakest: all 4s except p3 items = 0
        answers = _all_answers(4)
        for k in all_item_keys():
            if k.startswith("p3_"):
                answers[k] = 0
        rpt = build_journey_report(
            parent_name="Sam", child_name="Riley", responses=answers,
        )
        first_action = rpt["action_plan"][0]["action"]
        assert "IEP & ARD" in first_action

    def test_report_survives_empty_responses(self):
        from edu_deep_journey import build_journey_report
        rpt = build_journey_report(
            parent_name=None, child_name=None, responses={},
        )
        assert rpt["score_card"]["band"] == "unrated"
        # Should render without crashing — every top-level key present
        for key in ("cover", "overview", "score_card", "support_summary",
                    "alignment_areas", "attention_areas", "support_level",
                    "practical_options", "action_plan",
                    "foundation_statement", "final_summary", "disclaimer"):
            assert key in rpt
