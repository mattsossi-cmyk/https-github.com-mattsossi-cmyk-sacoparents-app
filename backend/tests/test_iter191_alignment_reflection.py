"""Iter 191 — Alignment Reflection Prompts (Phase 1).

Verifies:
  * Questions module surfaces 6 prompts for the co_parenting subject
    in the sacoparentsalign-locked order.
  * Analysis engine produces the "Both parents mentioned 'X'" bullets
    for realistic answers, and gracefully handles empty / partial data.
  * API endpoints CRUD reflections behind auth and never leak one
    parent's answers to the other before both have saved.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alignment_reflection_questions import (  # noqa: E402
    CO_PARENTING_PROMPTS,
    PROMPT_CONCERNS,
    PROMPT_DESIRED_IMPROVEMENTS,
    PROMPT_OPTIONS,
    PROMPT_OTHER_PARENT_CONCERNS,
    PROMPT_PRIMARY_NEED,
    PROMPT_WHATS_WORKING,
    SUBJECT_CO_PARENTING,
    is_known_subject,
    prompt_ids_for,
    prompts_for,
)
from alignment_reflection_analysis import analyse_reflections  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
BASE_URL = ""


# ---------------------------------------------------------------------------
# Question bank contract.
# ---------------------------------------------------------------------------

def test_co_parenting_has_six_prompts_in_locked_order():
    """The 6 prompts and their order are a hard contract — the form,
    the analysis engine, and the report all depend on this shape."""
    ids = prompt_ids_for(SUBJECT_CO_PARENTING)
    assert ids == [
        PROMPT_PRIMARY_NEED,
        PROMPT_WHATS_WORKING,
        PROMPT_CONCERNS,
        PROMPT_DESIRED_IMPROVEMENTS,
        PROMPT_OPTIONS,
        PROMPT_OTHER_PARENT_CONCERNS,
    ]


def test_every_prompt_carries_the_expected_metadata():
    """Each prompt must have label / prompt / placeholder / help /
    max_length so the frontend renders a consistent form. Missing any
    of these on a new subject would ship a broken UI."""
    required = {"id", "label", "prompt", "placeholder", "help", "max_length"}
    for p in CO_PARENTING_PROMPTS:
        assert required <= set(p.keys()), f"Missing keys on prompt {p.get('id')}"
        assert p["max_length"] == 600


def test_is_known_subject_gates_unknown_subjects():
    assert is_known_subject(SUBJECT_CO_PARENTING) is True
    assert is_known_subject("family-violence-safety-not-implemented-yet") is False


# ---------------------------------------------------------------------------
# Analysis engine — behaviour spec.
# ---------------------------------------------------------------------------

def _canonical_pair():
    """Two parents with realistic sacoparentsalign-style answers."""
    a = {
        "primary_need":          "Consistent expectations across both homes.",
        "whats_working":         "Bedtime routine is finally solid in both places.",
        "concerns":              "Screen-time rules change without discussion.",
        "desired_improvements":  "More consistent bedtimes and homework routines.",
        "options":               "A shared calendar and monthly check-ins.",
        "other_parent_concerns": "They probably worry about Maya being tired at school.",
    }
    b = {
        "primary_need":          "Consistent expectations between both homes for our child.",
        "whats_working":         "The bedtime routine works well with Maya.",
        "concerns":              "Rigid schedule is hard when family events come up on weekends.",
        "desired_improvements":  "Consistent bedtimes and predictable transitions.",
        "options":               "Shared calendar with a monthly check-in call.",
        "other_parent_concerns": "Worried about Maya feeling shuffled between homes.",
    }
    return a, b


def test_analysis_produces_shared_bullets_for_overlapping_answers():
    a, b = _canonical_pair()
    res = analyse_reflections(a, b, child_name="Maya")
    labels = {row["prompt_label"]: row["shared_phrase"] for row in res["both_parents_mentioned"]}

    # Primary need overlap should mention "consistent" and "expectations".
    assert "consistent" in labels["Your child's primary need"]
    assert "expectations" in labels["Your child's primary need"]

    # What's working overlaps on "bedtime, routine".
    assert "bedtime" in labels["What's already working"]
    assert "routine" in labels["What's already working"]

    # Options overlaps on "calendar, monthly, shared".
    assert "calendar" in labels["Options you would consider"]
    assert "monthly" in labels["Options you would consider"]


def test_analysis_skips_bullets_when_no_shared_keyword():
    """The concerns row in the canonical pair has NO shared meaningful
    tokens (both answers describe different things). The analysis
    must NOT invent a fake overlap."""
    a, b = _canonical_pair()
    res = analyse_reflections(a, b, child_name="Maya")
    labels = {row["prompt_label"] for row in res["both_parents_mentioned"]}
    # "Your concerns" is present because "screen-time rules change" and
    # "rigid schedule is hard" share no meaningful token — verify the
    # bullet is NOT in the shared list.
    assert "Your concerns" not in labels


def test_analysis_strips_child_name_from_shared_bullets():
    """The child's name is stripped so we never emit filler bullets
    like 'Both parents mentioned Maya when describing...'"""
    a = {"primary_need": "Maya needs consistent bedtime."}
    b = {"primary_need": "Consistent bedtime for Maya."}
    res = analyse_reflections(a, b, child_name="Maya")
    phrase = res["both_parents_mentioned"][0]["shared_phrase"]
    assert "maya" not in phrase.lower()
    assert "consistent" in phrase.lower()
    assert "bedtime" in phrase.lower()


def test_analysis_surfaces_short_answers_verbatim():
    """Answers of ≤3 words ARE the keyword — verbatim short answer
    when both parents write the same short thing."""
    a = {"primary_need": "Predictability"}
    b = {"primary_need": "predictability"}
    res = analyse_reflections(a, b)
    assert res["both_parents_mentioned"][0]["shared_phrase"] == "predictability"


def test_analysis_handles_empty_or_partial_answers():
    """Missing / empty answers must not raise. Perspectives-differ
    still includes rows where only ONE parent answered."""
    a = {"primary_need": "Predictability"}
    b: Dict[str, str] = {}
    res = analyse_reflections(a, b)
    # No shared bullets because parent B never answered.
    assert res["both_parents_mentioned"] == []
    # But the differ row surfaces parent A's answer.
    assert len(res["perspectives_differ"]) == 1
    assert res["perspectives_differ"][0]["parent_a_quote"] == "Predictability"
    assert res["perspectives_differ"][0]["parent_b_quote"] == ""


def test_analysis_derives_child_needs_from_primary_and_improvements():
    a, b = _canonical_pair()
    res = analyse_reflections(a, b, child_name="Maya")
    needs = [n.lower() for n in res["reflection_child_needs"]]
    assert any("consistent" in n for n in needs)
    assert any("bedtimes" in n or "bedtime" in n for n in needs)


# ---------------------------------------------------------------------------
# API contract — schema + CRUD + compare.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Same pattern as iter135 — restore a fresh Mongo binding on
    app.state.db in case a prior test module stubbed it out."""
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe_iter191_rows():
    """Clean up rows from prior runs so CRUD tests start from zero."""
    import asyncio
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            emails = [
                "iter191_a@test.com", "iter191_b@test.com",
                "iter191_alone@test.com",
            ]
            users = await db.users.find(
                {"email": {"$in": emails}}, {"user_id": 1}
            ).to_list(None)
            uids = [u["user_id"] for u in users]
            if uids:
                await db.alignment_reflections.delete_many({"user_id": {"$in": uids}})
        finally:
            c.close()
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        loop.run_until_complete(_run())
        loop.close()
    except Exception:  # noqa: BLE001
        pass
    yield


def _register(client: TestClient, email: str, name: str, password: str = "TestPass191!"):
    """Register (or log in if exists) and return the auth cookie jar."""
    r = client.post(
        f"{BASE_URL}/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": password, "name": name},
    )
    if r.status_code == 400:  # already registered
        r = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
        )
    assert r.status_code == 200, r.text
    token = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def test_api_returns_schema_without_auth(client):
    r = client.get(f"{BASE_URL}/api/alignment-reflection/schema/co_parenting")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "co_parenting"
    assert len(body["prompts"]) == 6


def test_api_rejects_unknown_subject(client):
    r = client.get(f"{BASE_URL}/api/alignment-reflection/schema/imaginary-subject")
    assert r.status_code == 404


def test_api_crud_roundtrip(client):
    hdrs = _register(client, "iter191_a@test.com", "Parent A Iter191")

    # Initially empty for this user.
    r = client.get(f"{BASE_URL}/api/alignment-reflection/co_parenting/mine", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["answers"] == {}

    # Save some answers.
    r = client.put(
        f"{BASE_URL}/api/alignment-reflection/co_parenting",
        headers=hdrs,
        json={"answers": {
            "primary_need": "Predictable structure",
            "whats_working": "Bedtime routine",
            "stray_key_that_should_be_dropped": "malicious",
        }},
    )
    assert r.status_code == 200
    # Extra keys are dropped, so answered_count is 2.
    assert r.json()["answered_count"] == 2

    r = client.get(f"{BASE_URL}/api/alignment-reflection/co_parenting/mine", headers=hdrs)
    assert r.status_code == 200
    answers = r.json()["answers"]
    assert answers["primary_need"] == "Predictable structure"
    assert answers["whats_working"] == "Bedtime routine"
    assert "stray_key_that_should_be_dropped" not in answers


def test_compare_waits_when_coparent_has_not_answered_yet(client):
    """When only one parent has saved, compare returns
    waiting_on_coparent — never leaks Parent A's answers to Parent B
    if Parent B has not opted in yet."""
    a_hdrs = _register(client, "iter191_a@test.com", "Parent A Iter191")
    _register(client, "iter191_b@test.com", "Parent B Iter191")

    client.put(
        f"{BASE_URL}/api/alignment-reflection/co_parenting",
        headers=a_hdrs,
        json={"answers": {"primary_need": "Predictable structure"}},
    )

    r = client.post(
        f"{BASE_URL}/api/alignment-reflection/co_parenting/compare",
        headers=a_hdrs,
        json={"coparent_email": "iter191_b@test.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "waiting_on_coparent"
    assert body["coparent"]["email"] == "iter191_b@test.com"
    # Critical: parent B's answers slot is NOT present in this response
    # — waiting states never expose partial cross-parent data.
    assert "coparent_answers" not in body
    assert "analysis" not in body


def test_compare_returns_analysis_when_both_have_answered(client):
    a_hdrs = _register(client, "iter191_a@test.com", "Parent A Iter191")
    b_hdrs = _register(client, "iter191_b@test.com", "Parent B Iter191")

    client.put(
        f"{BASE_URL}/api/alignment-reflection/co_parenting",
        headers=a_hdrs,
        json={"answers": {"primary_need": "Consistent expectations across both homes."}},
    )
    client.put(
        f"{BASE_URL}/api/alignment-reflection/co_parenting",
        headers=b_hdrs,
        json={"answers": {"primary_need": "Consistent expectations between homes."}},
    )

    r = client.post(
        f"{BASE_URL}/api/alignment-reflection/co_parenting/compare",
        headers=a_hdrs,
        json={"coparent_email": "iter191_b@test.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    both_labels = [row["prompt_label"] for row in body["analysis"]["both_parents_mentioned"]]
    assert "Your child's primary need" in both_labels


def test_compare_409_when_caller_has_not_answered(client):
    """Caller hitting compare BEFORE saving their own answers must
    get a 409 — never leak the co-parent's answers to a caller who
    has not reciprocated."""
    a_hdrs = _register(client, "iter191_alone@test.com", "Solo Iter191")
    _register(client, "iter191_b@test.com", "Parent B Iter191")
    # Solo has NOT saved anything. B has (from previous test).

    r = client.post(
        f"{BASE_URL}/api/alignment-reflection/co_parenting/compare",
        headers=a_hdrs,
        json={"coparent_email": "iter191_b@test.com"},
    )
    assert r.status_code == 409
    assert "Complete your Alignment Reflection" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Integration — reflections flow through into `build_joint_agreement`'s
# alignment_report block and land on the rendered PDF.
# ---------------------------------------------------------------------------

def test_build_joint_agreement_surfaces_reflection_analysis():
    """When both parents' reflection answers are passed in, the
    alignment_report gains a `reflection_analysis` block with the
    shared-phrase bullets. When only one side submits, the block is
    NOT emitted (dual-consent guardrail)."""
    from joint_agreement import build_joint_agreement

    agr = {"agreement_id": "a", "generated_at": "2026-09-14T00:00:00Z"}
    r_a = {
        "primary_need": "Consistent expectations across both homes.",
        "options":      "A shared calendar and monthly check-ins.",
    }
    r_b = {
        "primary_need": "Consistent expectations between both homes.",
        "options":      "Shared calendar with monthly check-in call.",
    }

    with_both = build_joint_agreement(
        share_id="sh_r", parent_a_name="Alex", parent_b_name="Sam",
        agreement_a=agr, agreement_b=agr,
        reflections_a=r_a, reflections_b=r_b,
    )
    assert "reflection_analysis" in with_both["alignment_report"]
    labels = [row["prompt_label"] for row in with_both["alignment_report"]["reflection_analysis"]["both_parents_mentioned"]]
    assert "Your child's primary need" in labels
    assert "Options you would consider" in labels

    only_one = build_joint_agreement(
        share_id="sh_r", parent_a_name="Alex", parent_b_name="Sam",
        agreement_a=agr, agreement_b=agr,
        reflections_a=r_a, reflections_b={},
    )
    # Dual-consent guardrail: no leak of A's answers when B hasn't submitted.
    assert "reflection_analysis" not in only_one["alignment_report"]


def test_pdf_renders_reflection_shared_bullets_when_both_submitted():
    """The rendered PDF must include the "Both parents mentioned 'X'"
    bullet on the same page as SS2 when both parents completed the
    reflection. This is the primary product moment — the report reads
    like sacoparentsalign's sample only when this section lands."""
    import io
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    from joint_agreement import build_joint_agreement
    from joint_agreement_pdf import build_joint_agreement_pdf

    agr = {"agreement_id": "a", "generated_at": "2026-09-14T00:00:00Z"}
    r_a = {"primary_need": "Consistent expectations across both homes."}
    r_b = {"primary_need": "Consistent expectations between homes."}

    payload = build_joint_agreement(
        share_id="sh_r", parent_a_name="Alex", parent_b_name="Sam",
        agreement_a=agr, agreement_b=agr,
        reflections_a=r_a, reflections_b=r_b,
    )
    pdf_bytes = build_joint_agreement_pdf(payload)
    r = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((p.extract_text() or "") for p in r.pages)
    assert "Shared themes from your reflection prompts" in text
    assert "Both parents mentioned" in text
    # Verbatim per-prompt quotes on SS3.
    assert "Reflection quotes" in text
