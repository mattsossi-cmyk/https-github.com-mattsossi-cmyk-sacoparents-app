"""Iteration 70 tests — Psychological Deep Dive v2 (Alignment Framework).

Mirrors the shape of test_iter67_edu_v2.py — same 5-part × 5-item ×
0-4 alignment scale, same three-band scoring, same legacy-wipe logic on
first load.
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


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


def _reset_psych():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["psych_deep_assessments"].delete_many({})
            await db["psych_deep_reports"].delete_many({})
        finally:
            c.close()
    _run(_r())


@pytest.fixture(autouse=True)
def _cleanup():
    _reset_psych()
    yield
    _reset_psych()


def _all_answers(value):
    from psych_deep_questions import all_item_keys
    return {k: value for k in all_item_keys()}


class TestSchema:
    def test_version_is_v2(self):
        from psych_deep_questions import DEEP_DIVE_VERSION
        assert DEEP_DIVE_VERSION.startswith("psych-deep-2.")

    def test_five_parts_five_items_each(self):
        from psych_deep_questions import public_schema
        parts = public_schema()["sections"]
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
        from psych_deep_questions import all_item_keys
        assert len(all_item_keys()) == 25


class TestValidateAnswer:
    @pytest.mark.parametrize("v", [0, 1, 2, 3, 4, "na"])
    def test_accepts_valid(self, v):
        from psych_deep_questions import validate_answer
        assert validate_answer("p1_q1", v)

    @pytest.mark.parametrize("v", [-1, 5, 10, "5", True, None, [], {}])
    def test_rejects_invalid(self, v):
        from psych_deep_questions import validate_answer
        assert not validate_answer("p1_q1", v)


class TestScoreDeepDive:
    def test_empty_is_unrated(self):
        from psych_deep_scoring import score_deep_dive
        s = score_deep_dive({})
        assert s["total"] == 0 and s["percent"] == 0
        assert s["band"] == "unrated"
        assert len(s["sections"]) == 5

    def test_all_fours_high(self):
        from psych_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(4))
        assert s["total"] == 100 and s["percent"] == 100
        assert s["band"] == "high"
        assert s["totals"]["strengths"] == 5

    def test_all_twos_boundary_low(self):
        from psych_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(2))
        assert s["percent"] == 50
        assert s["band"] == "low"

    def test_all_threes_moderate(self):
        from psych_deep_scoring import score_deep_dive
        s = score_deep_dive(_all_answers(3))
        assert s["percent"] == 75
        assert s["band"] == "moderate"

    def test_boundary_81_high(self):
        from psych_deep_scoring import score_deep_dive
        from psych_deep_questions import all_item_keys
        keys = all_item_keys()
        answers = {k: 0 for k in keys}
        for k in keys[:20]:
            answers[k] = 4
        answers[keys[20]] = 1
        s = score_deep_dive(answers)
        assert s["total"] == 81 and s["percent"] == 81
        assert s["band"] == "high"

    def test_na_prorated(self):
        from psych_deep_scoring import score_deep_dive
        from psych_deep_questions import all_item_keys
        keys = all_item_keys()
        answers = {}
        for i, k in enumerate(keys):
            answers[k] = 4 if i < 20 else "na"
        s = score_deep_dive(answers)
        assert s["answered"] == 20 and s["na"] == 5
        assert s["percent"] == 100 and s["band"] == "high"


class TestLegacyWipe:
    def test_v1_keys_dropped_on_me_load(self, p1_client):
        async def _seed():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                r = p1_client.get(f"{BASE_URL}/api/auth/me", timeout=15)
                uid = r.json()["user_id"]
                await c[DB_NAME]["psych_deep_assessments"].insert_one({
                    "user_id": uid,
                    "responses": {
                        "s1_diagnoses":  ["ADHD"],
                        "s6_attends_therapy": "Yes",
                        "p1_q1": 3,  # valid v2 answer stays
                    },
                    "completed": True,
                })
            finally:
                c.close()
        _run(_seed())

        r = p1_client.get(f"{BASE_URL}/api/psych-deep/me", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["has_assessment"] is True
        responses = body["assessment"]["responses"]
        assert "s1_diagnoses" not in responses
        assert "s6_attends_therapy" not in responses
        assert responses.get("p1_q1") == 3
        assert body["assessment"]["completed"] is False


class TestJourneyReport:
    def test_report_has_score_card(self):
        from psych_deep_journey import build_journey_report
        rpt = build_journey_report(
            parent_name="Sam", child_name="Riley",
            responses=_all_answers(4),
        )
        assert "score_card" in rpt
        assert rpt["score_card"]["percent"] == 100
        assert rpt["score_card"]["band"] == "high"
        assert len(rpt["support_summary"]["ratings"]) == 5
        assert all(r["rating"] == "Strong" for r in rpt["support_summary"]["ratings"])

    def test_action_plan_lists_lowest_first(self):
        from psych_deep_journey import build_journey_report
        from psych_deep_questions import all_item_keys
        answers = _all_answers(4)
        for k in all_item_keys():
            if k.startswith("p3_"):
                answers[k] = 0
        rpt = build_journey_report(
            parent_name="Sam", child_name="Riley", responses=answers,
        )
        first = rpt["action_plan"][0]["action"]
        assert "Therapy" in first  # Part 3 name

    def test_report_survives_empty(self):
        from psych_deep_journey import build_journey_report
        rpt = build_journey_report(
            parent_name=None, child_name=None, responses={},
        )
        assert rpt["score_card"]["band"] == "unrated"
        for key in ("cover", "overview", "score_card", "support_summary",
                    "alignment_areas", "attention_areas", "support_level",
                    "action_plan", "foundation_statement",
                    "final_summary", "disclaimer"):
            assert key in rpt
