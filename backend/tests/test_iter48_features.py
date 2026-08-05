"""Iteration 48 backend tests — Educational Assessment Alignment Report.

Two things being verified here:

1. `deep_dive_comparison_core._extract_alignment_lists` produces three
   mediation-ready lists (shared_priorities, discussion_points,
   mediation_questions) from the section-by-section comparison, obeying
   every case (a-h) enumerated in the review request.

2. Only the Educational Deep Dive PDF is rebranded to
   "Educational Assessment Alignment Report" — psych & med PDFs stay on
   their prior filenames + titles.

We reuse the iter-46/47 seed harness style so this file cleans up any
data it created via an autouse teardown.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

# Make backend importable when pytest is run from /app/backend/tests/
sys.path.insert(0, "/app/backend")

from deep_dive_comparison_core import (  # noqa: E402
    _extract_alignment_lists,
    build_comparison_from_spec,
)


# ---------------------------------------------------------------------------
# ENV
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _read_env(key):
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


MONGO_URL = _read_env("MONGO_URL")
DB_NAME = _read_env("DB_NAME")

PARENT1 = {"email": "parent1@test.com", "password": "TestPass123!", "name": "Sam Parent"}
PARENT2 = {"email": "parent2@test.com", "password": "TestPass123!", "name": "Riley Parent"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_account(creds):
    requests.post(f"{BASE_URL}/api/auth/register", json={
        **creds, "children": [], "custody_situation": "50/50 shared",
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": creds["email"], "password": creds["password"],
    }, timeout=30)
    assert r.status_code == 200, f"login {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _client(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"})
    return s


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Fabricated section/item builders
# ---------------------------------------------------------------------------
def _sections(items):
    """Wrap a list of (section_id, item_dict) tuples into the DeepDive shape."""
    grouped = {}
    for sec_id, sec_num, sec_name, item in items:
        grouped.setdefault((sec_id, sec_num, sec_name), []).append(item)
    return [
        {"id": sid, "number": num, "name": name, "items": its}
        for (sid, num, name), its in grouped.items()
    ]


def _likert_item(iid, prompt, a, b):
    from deep_dive_comparison_core import _compare_likert
    return {"id": iid, "type": "likert", "prompt": prompt, **_compare_likert(a, b)}


def _single_item(iid, prompt, a, b):
    from deep_dive_comparison_core import _compare_single
    return {"id": iid, "type": "single", "prompt": prompt, **_compare_single(a, b)}


def _multi_item(iid, prompt, a, b):
    from deep_dive_comparison_core import _compare_multi
    return {"id": iid, "type": "multi", "prompt": prompt, **_compare_multi(a, b)}


# ===========================================================================
# UNIT TESTS: _extract_alignment_lists
# ===========================================================================
class TestExtractAlignmentLists:
    """All 8 cases (a-h) from the iter-48 review request."""

    # ----- (a) both parents scored a likert ≥ 4 → shared_priorities ---------
    def test_a_likert_both_high_becomes_shared_priority(self):
        secs = _sections([
            ("s2", 2, "Parent-Teacher Communication",
             _likert_item("discuss_goals", "Educational goals discussed.", 5, 4)),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["shared_priorities"]) == 1
        row = out["shared_priorities"][0]
        assert row["section_id"] == "s2"
        assert row["item_id"] == "discuss_goals"
        assert row["parent_a_value"] == 5 and row["parent_b_value"] == 4
        # `reason` must mention the two scores (case a)
        assert "4" in row["reason"] and "5" in row["reason"]
        assert out["discussion_points"] == []
        assert out["mediation_questions"] == []

    # ----- (b) multi with 2+ overlap → shared_priorities --------------------
    def test_b_multi_two_plus_overlap_becomes_shared_priority(self):
        secs = _sections([
            ("s1", 1, "Educational Profile",
             _multi_item("concerns", "Concerns?", ["Reading", "Math", "Attention"],
                         ["Reading", "Math", "Behaviour"])),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["shared_priorities"]) == 1
        row = out["shared_priorities"][0]
        assert row["item_id"] == "concerns"
        assert set(row["both"]) == {"Math", "Reading"}
        # reason should surface the overlap list (case b)
        assert "Math" in row["reason"] and "Reading" in row["reason"]

    def test_b2_multi_single_overlap_not_shared(self):
        """A single overlap alone is NOT a shared priority (needs 2+)."""
        secs = _sections([
            ("s1", 1, "Educational Profile",
             _multi_item("concerns", "Concerns?", ["Reading", "Math"], ["Reading", "Behaviour"])),
        ])
        out = _extract_alignment_lists(secs)
        assert out["shared_priorities"] == []

    # ----- (c) likert gap==2 (close) → discussion_points --------------------
    def test_c_likert_close_becomes_discussion_point(self):
        secs = _sections([
            ("s2", 2, "Parent-Teacher Communication",
             _likert_item("discuss_goals", "Educational goals discussed.", 5, 3)),
        ])
        out = _extract_alignment_lists(secs)
        # a=5, b=3 → both ≥ ... wait, b=3 (<4) so NOT a shared priority
        assert out["shared_priorities"] == []
        assert len(out["discussion_points"]) == 1
        row = out["discussion_points"][0]
        assert row["alignment"] == "close"
        assert row["gap"] == 2
        assert row["parent_a_value"] == 5 and row["parent_b_value"] == 3

    # ----- (d) one_only alignment → discussion_points -----------------------
    def test_d_one_only_becomes_discussion_point(self):
        secs = _sections([
            ("s2", 2, "Parent-Teacher Communication",
             _single_item("both_can_attend", "Can both parents attend?", "Yes", None)),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["discussion_points"]) == 1
        row = out["discussion_points"][0]
        assert row["alignment"] == "one_only"
        assert row["item_id"] == "both_can_attend"

    # ----- (e) likert gap>2 (divergent) → mediation_questions --------------
    def test_e_likert_divergent_becomes_mediation_question(self):
        secs = _sections([
            ("s2", 2, "Parent-Teacher Communication",
             _likert_item("discuss_goals", "Educational goals discussed.", 5, 1)),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["mediation_questions"]) == 1
        row = out["mediation_questions"][0]
        assert row["alignment"] == "divergent"
        assert row["gap"] == 4
        assert row["question"].startswith("How will we align on:")
        assert "Educational goals discussed." in row["question"]

    # ----- (f) single divergent → mediation_questions ("You chose different...")
    def test_f_single_divergent_becomes_mediation_question(self):
        secs = _sections([
            ("s2", 2, "Parent-Teacher Communication",
             _single_item("how_often_attend", "How often do you attend?", "Always", "Rarely")),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["mediation_questions"]) == 1
        row = out["mediation_questions"][0]
        assert row["question"].startswith("You chose different answers to:")
        assert "How often do you attend?" in row["question"]

    # ----- (g) multi divergent → mediation_questions ("Which of these..." ) --
    def test_g_multi_divergent_becomes_mediation_question(self):
        secs = _sections([
            ("s1", 1, "Educational Profile",
             _multi_item("concerns", "Concerns?", ["Reading"], ["Behaviour", "Sleep"])),
        ])
        out = _extract_alignment_lists(secs)
        assert len(out["mediation_questions"]) == 1
        row = out["mediation_questions"][0]
        assert row["question"].startswith(
            "Which of these options do we both commit to on:"
        )
        assert "Concerns?" in row["question"]
        assert row["only_parent_a"] == ["Reading"]
        assert row["only_parent_b"] == ["Behaviour", "Sleep"]

    # ----- (h) each list capped at 8 ----------------------------------------
    def test_h_lists_capped_at_eight(self):
        shared_items = []
        discuss_items = []
        mediate_items = []
        # 10 shared (likert both=5)
        for i in range(10):
            shared_items.append(("s_shared", 2, "Shared",
                                 _likert_item(f"item{i}", f"P{i}", 5, 5)))
        # 10 close discussion (gap 2)
        for i in range(10):
            discuss_items.append(("s_close", 3, "Close",
                                  _likert_item(f"itemC{i}", f"C{i}", 5, 3)))
        # 10 divergent mediation (gap 4)
        for i in range(10):
            mediate_items.append(("s_div", 4, "Div",
                                  _likert_item(f"itemD{i}", f"D{i}", 5, 1)))
        secs = _sections(shared_items + discuss_items + mediate_items)
        out = _extract_alignment_lists(secs)
        assert len(out["shared_priorities"]) == 8
        assert len(out["discussion_points"]) == 8
        assert len(out["mediation_questions"]) == 8


# ===========================================================================
# UNIT TEST: build_comparison_from_spec surfaces the three lists
# ===========================================================================
class TestBuildComparisonExposesLists:
    def test_payload_contains_three_new_fields(self):
        sections_spec = [{
            "id": "s2", "number": 2, "name": "Parent-Teacher Communication",
            "items": {
                "discuss_goals": {"type": "likert", "prompt": "Goals discussed."},
                "how_often_attend": {"type": "single", "prompt": "How often?",
                                     "options": ["Always", "Rarely"]},
            },
        }]
        a = {"s2_discuss_goals": 5, "s2_how_often_attend": "Always"}
        b = {"s2_discuss_goals": 4, "s2_how_often_attend": "Rarely"}
        payload = build_comparison_from_spec(
            sections_spec=sections_spec,
            assessment_version="test",
            product_name="Educational Needs Deep Dive",
            parent_a_name="Sam", parent_b_name="Riley",
            a_answers=a, b_answers=b,
        )
        for key in ("shared_priorities", "discussion_points", "mediation_questions"):
            assert key in payload, f"missing {key} in payload"
            assert isinstance(payload[key], list)
        # likert (5,4) both>=4 → shared priority
        assert any(r["item_id"] == "discuss_goals" for r in payload["shared_priorities"])
        # single divergent → mediation
        assert any(r["item_id"] == "how_often_attend" for r in payload["mediation_questions"])


# ===========================================================================
# API INTEGRATION: Educational rename + payload keys + PDF filename
# ===========================================================================
PATHWAYS_ALL = [
    ("edu-deep",   "edu_deep_share_",   "edu_deep_assessments",   "edu_deep_shares"),
    ("psych-deep", "psych_deep_share_", "psych_deep_assessments", "psych_deep_shares"),
    ("med-deep",   "med_deep_share_",   "med_deep_assessments",   "med_deep_shares"),
]


def _post_safety_level_4(client):
    payload = {"section_1": {}, "section_2": {"s2_q%d" % i: "yes" for i in range(1, 12)}}
    payload["section_2"]["s2_q8"] = "no"
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text


def _all_schema_keys(client, prefix):
    r = client.get(f"{BASE_URL}/api/{prefix}/schema", timeout=30)
    assert r.status_code == 200
    schema = r.json()
    answers_a, answers_b = {}, {}
    for s in schema.get("sections", []):
        if s.get("texas_only"):
            continue
        sid = s.get("id")
        for item in s.get("items", []):
            key = f"{sid}_{item['id']}"
            if item.get("type") in ("likert", "alignment"):
                # Use the item's declared scale max; fall back to 5 for v1.
                scale = item.get("scale") or [1, 2, 3, 4, 5]
                top = max(scale) if scale else 5
                answers_a[key] = top
                answers_b[key] = top   # identical → shared priorities everywhere
            elif item.get("type") == "single":
                opts = item.get("options") or []
                if opts:
                    answers_a[key] = opts[0]
                    answers_b[key] = opts[0]
    return answers_a, answers_b


def _bulk_and_complete(client, prefix, answers):
    r = client.post(f"{BASE_URL}/api/{prefix}/answers/bulk",
                    json={"answers": answers}, timeout=30)
    assert r.status_code == 200, r.text
    r = client.post(f"{BASE_URL}/api/{prefix}/complete", timeout=30)
    assert r.status_code == 200, r.text


def _revoke_all(client):
    for prefix, _sp, _ac, _sc in PATHWAYS_ALL:
        r = client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        if r.status_code != 200:
            continue
        for share in r.json().get("shares", []):
            if share.get("status") != "revoked":
                client.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")


async def _cleanup_snapshots():
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        share_ids = []
        for _pref, _sp, _ac, sc in PATHWAYS_ALL:
            async for s in db[sc].find({}, {"_id": 0, "share_id": 1}):
                share_ids.append(s["share_id"])
        if share_ids:
            await db["deep_dive_compare_snapshots"].delete_many(
                {"share_id": {"$in": share_ids}}
            )
    finally:
        client.close()


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


@pytest.fixture
def p2_client(p2_token):
    return _client(p2_token)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(p1_token, p2_token):
    """Ensure a clean slate before/after all tests in this module."""
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    _run(_cleanup_snapshots())
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    _run(_cleanup_snapshots())


def _fresh_consented_share(p1c, p2c, prefix):
    _post_safety_level_4(p1c)
    _post_safety_level_4(p2c)
    ans_a, ans_b = _all_schema_keys(p1c, prefix)
    _bulk_and_complete(p1c, prefix, ans_a)
    _bulk_and_complete(p2c, prefix, ans_b)

    r = p1c.post(f"{BASE_URL}/api/{prefix}/compare/link",
                 json={"email": PARENT2["email"]})
    assert r.status_code == 200, r.text
    share_id = r.json()["share"]["share_id"]
    cr = p2c.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/consent",
                  json={"consent": True})
    assert cr.status_code == 200, cr.text
    return share_id


class TestComparisonPayloadHasLists:
    """End-to-end: seed identical answers → hit /compare/{id} → payload
    should carry all three new lists. Identical answers means most items
    become shared_priorities."""

    @pytest.mark.parametrize("prefix,_sp,_ac,_sc", PATHWAYS_ALL)
    def test_compare_payload_contains_three_lists(
        self, p1_client, p2_client, prefix, _sp, _ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)
        r = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}", timeout=30)
        assert r.status_code == 200, r.text
        cmp = (r.json().get("comparison") or {})
        for key in ("shared_priorities", "discussion_points", "mediation_questions"):
            assert key in cmp, f"{prefix}: missing {key} in payload"
            assert isinstance(cmp[key], list), f"{prefix}: {key} not a list"
        # Cap holds at 8 across the board
        for key in ("shared_priorities", "discussion_points", "mediation_questions"):
            assert len(cmp[key]) <= 8, f"{prefix}: {key} exceeded cap ({len(cmp[key])})"
        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


class TestEducationalPDFRename:
    """PDF filename prefixes for all three Check-In Reports."""

    EXPECTED_PREFIX = {
        "edu-deep":   "Coparenting_Education_CheckIn_Summary_",
        "psych-deep": "Checkin_Psychological_Needs_Report_",
        "med-deep":   "Checkin_Medical_Needs_Report_",
    }

    @pytest.mark.parametrize("prefix,_sp,_ac,_sc", PATHWAYS_ALL)
    def test_pdf_filename_matches_pathway(
        self, p1_client, p2_client, prefix, _sp, _ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)
        # Must view once to snapshot before requesting PDF (some paths gate on it,
        # but /pdf works after consent too — call anyway for safety).
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}", timeout=30)
        r = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/pdf", timeout=60)
        assert r.status_code == 200, r.text[:400]
        cd = r.headers.get("Content-Disposition", "")
        expected = self.EXPECTED_PREFIX[prefix]
        assert expected in cd, f"{prefix}: expected prefix '{expected}' in Content-Disposition, got: {cd}"
        # And PDF payload signature
        assert r.content[:4] == b"%PDF", f"{prefix}: response is not a PDF"
        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")
