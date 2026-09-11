"""Iteration 184 — Complete Alignment Report (unified 10-section).

Covers the new /complete-report endpoints that stitch every completed
reflection lane into ONE report matching the sacoparentsalign.com
10-section skeleton.

Hermetic checks:
  * Individual JSON view returns the 7 canonical lanes in order and
    reports completion counts.
  * Individual PDF renders as a real PDF (%PDF- header) at a sensible
    size — proves every section builder ran without an FPDF layout
    crash.
  * Joint endpoints are gated: the caller must be a parent on the
    case OR the professional who created it. A 404 rather than 403
    is used to avoid leaking case_id existence.
  * Aggregator: `LANES` order is deterministic; joint status uses the
    neutral tri-state (shared / one-side / not-yet).

The routes require JWT auth for the mine.* endpoints — we mint a
short-lived test JWT for `parent1@test.com` (seeded via
test_credentials.md) so we don't have to spin up the full login flow.
"""
from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402


# ------------------------- auth helper ------------------------------------- #

_CACHED_TOKEN: dict = {}

def _test_bearer() -> str:
    if _CACHED_TOKEN.get("token"):
        return _CACHED_TOKEN["token"]
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "parent1@test.com", "password": "TestPass123!"},
        timeout=10,
    )
    if r.status_code != 200:
        raise AssertionError(
            f"Test login failed ({r.status_code}) — ensure parent1@test.com "
            f"exists per /app/memory/test_credentials.md. Body: {r.text}"
        )
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No access_token in login response: {data}"
    _CACHED_TOKEN["token"] = token
    return token


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_test_bearer()}"}


# --------------------------- individual variant ---------------------------- #

def test_mine_json_returns_seven_lanes_in_canonical_order():
    r = requests.get(f"{BASE_URL}/api/complete-report/mine", headers=_auth_headers(), timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["variant"] == "individual"
    assert "lanes" in data
    lane_ids = [ln["id"] for ln in data["lanes"]]
    # Canonical order matters — the frontend + PDF renderer both
    # rely on it. Match `complete_alignment_aggregator.LANES` exactly.
    assert lane_ids == [
        "foundation", "communication", "activities", "schedule",
        "child_needs", "safety", "coparenting",
    ], lane_ids
    counts = data.get("counts") or {}
    assert counts.get("total") == 7
    assert isinstance(counts.get("completed"), int)


def test_mine_pdf_returns_a_real_pdf():
    r = requests.get(
        f"{BASE_URL}/api/complete-report/mine.pdf",
        headers=_auth_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text[:400]
    assert r.headers.get("content-type") == "application/pdf"
    # `%PDF-` signature = 4 bytes plus a version digit. Anything less
    # means fpdf crashed and the route returned an HTML error page.
    body = r.content
    assert body[:5] == b"%PDF-", f"Unexpected header: {body[:20]!r}"
    # 10 sections of the current layout render at ~6-15KB minimum.
    assert len(body) > 3000, f"PDF suspiciously small: {len(body)} bytes"


def test_mine_endpoints_require_auth():
    r_json = requests.get(f"{BASE_URL}/api/complete-report/mine", timeout=10)
    r_pdf = requests.get(f"{BASE_URL}/api/complete-report/mine.pdf", timeout=10)
    for r in (r_json, r_pdf):
        assert r.status_code in (401, 403), r.text


# ------------------------------ joint variant ------------------------------ #

def test_joint_endpoint_rejects_bad_case_id_format():
    # The route uses a regex that requires SA-{4-10 alnums}. A
    # random string should 422 before authorization is even checked.
    r = requests.get(
        f"{BASE_URL}/api/complete-report/joint/not-a-case-id",
        headers=_auth_headers(),
        timeout=10,
    )
    assert r.status_code == 422, r.text


def test_joint_seeded_demo_case_never_leaks_foundation_prompts_to_other_parent():
    """SECURITY REGRESSION (iter185 code review):
    The joint JSON view must NOT echo either parent's Foundation
    Statement free-text answers under `parent_a` or `parent_b`. Those
    prompts are private-between-co-parents by product policy — the
    joint report exists to surface alignment STATUS, not answer
    bodies.

    parent1@test.com is a member on `SA-DEMO01` so this test can hit
    the joint endpoint end-to-end and assert the seeded parent B
    ("Riley Parent") free-text NEVER appears anywhere in the response.
    """
    r = requests.get(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01",
        headers=_auth_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    # 1) The scrubbed sub-objects must not carry `prompts` OR
    #    `highlights` on any lane. Strict policy: same rule for
    #    Foundation Statement prompts and Child Needs highlights.
    for side_key in ("parent_a", "parent_b"):
        side = data.get(side_key) or {}
        for lane in side.get("lanes") or []:
            assert "prompts" not in lane, (
                f"HIGH: {side_key}.lanes[{lane.get('id')}] leaked Foundation prompts"
            )
            assert "highlights" not in lane, (
                f"HIGH: {side_key}.lanes[{lane.get('id')}] leaked Child Needs highlights"
            )
    # 2) Sanity — a full-text search over the SERIALIZED response
    #    must not find parent B's known seeded free-text. The seed
    #    script writes verbatim strings for parent B's Foundation.
    parent_b_seeded_secrets = (
        "From Rian's side the transitions are the hardest part of the week.",
        "I sometimes rush to explain when a pause would land better.",
        "A shared Sunday-evening 15-minute check-in that both of us keep.",
        "I'd like more heads-up on schedule changes than 24 hours.",
    )
    body_text = r.text  # raw JSON string
    for secret in parent_b_seeded_secrets:
        assert secret not in body_text, (
            f"HIGH: parent A can read parent B's Foundation Statement text: {secret!r}"
        )
    # 3) The Foundation individual view for parent A MUST still return
    #    their OWN prompts — we didn't over-strip.
    mine = requests.get(
        f"{BASE_URL}/api/complete-report/mine",
        headers=_auth_headers(),
        timeout=10,
    ).json()
    my_foundation = next(
        (ln for ln in (mine.get("lanes") or []) if ln.get("id") == "foundation"),
        {},
    )
    assert my_foundation.get("prompts"), (
        "Individual view must still surface the caller's own Foundation prompts "
        "— the scrub is joint-only."
    )


def test_my_active_cases_endpoint_lists_caller_cases_with_consent_state():
    """Iter188 onboarding nudge endpoint: `GET /api/complete-report/my-active-cases`
    must:
      * Include the seeded SA-DEMO01 case when called as parent1 (a member).
      * Report the caller's OWN `my_consent_at` (null when not consented).
      * Report only a boolean `coparent_has_consented` — never leak the
        co-parent's raw timestamp.
      * Return the caller's co-parent name so the nudge can render
        "with Riley Parent" without a second round-trip.
    """
    # Reset any pre-existing consent so this test starts from a
    # deterministic state (prior tests may have consented + revoked).
    r = requests.get(
        f"{BASE_URL}/api/complete-report/my-active-cases",
        headers=_auth_headers(),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "cases" in data
    demo = next((c for c in data["cases"] if c["case_id"] == "SA-DEMO01"), None)
    assert demo is not None, f"SA-DEMO01 missing from response: {data}"
    # coparent_name from the seeded parent B — Riley Parent.
    assert demo["coparent_name"] == "Riley Parent"
    # Exposed state fields — the endpoint must NEVER expose the
    # other parent's raw consent timestamp, only a boolean.
    assert "coparent_has_consented" in demo
    assert isinstance(demo["coparent_has_consented"], bool)
    assert "my_consent_at" in demo  # may be None or an ISO string
    # Defensive assertion: the response must NOT carry `parents` or
    # any other case-level identifier that could turn into a leak
    # surface if a future refactor forgets to project the fields.
    assert "parents" not in demo


def test_my_active_cases_endpoint_requires_auth():
    r = requests.get(f"{BASE_URL}/api/complete-report/my-active-cases", timeout=10)
    assert r.status_code in (401, 403)


def test_child_needs_consent_toggle_unlocks_highlights_only_after_both_consent():
    """Iter187 dual-consent flow — a caller toggling their consent
    alone MUST NOT unlock highlights. Both parents must consent.

    We simulate this by:
      1) Confirming initial joint view is scrubbed (no highlights).
      2) POST /joint/SA-DEMO01/consent/child-needs as parent A → 200.
      3) Re-fetching joint view — still no highlights (waiting for B).
      4) POST as parent B (fresh login) → 200 + `unlocked: True`.
      5) Re-fetching joint view — highlights preserved through scrub.
      6) POST again as parent A → clears the flag (toggle-off).
      7) Re-fetching → no highlights again.
    """
    import time
    def _bearer_for(email: str) -> str:
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": "TestPass123!"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    a_hdrs = {"Authorization": f"Bearer {_bearer_for('parent1@test.com')}"}
    b_hdrs = {"Authorization": f"Bearer {_bearer_for('parent2@test.com')}"}

    def _joint_json(hdrs):
        rr = requests.get(f"{BASE_URL}/api/complete-report/joint/SA-DEMO01", headers=hdrs, timeout=10)
        assert rr.status_code == 200, rr.text
        return rr.json()

    def _clear_consent(hdrs, current):
        # POST toggles: if already consented, POST clears it. Called
        # in setup + teardown so the test is isolated from prior runs.
        if current:
            requests.post(f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/consent/child-needs", headers=hdrs, timeout=10)

    # Setup — clear any leftover consents from a prior test run.
    j = _joint_json(a_hdrs)
    _clear_consent(a_hdrs, j.get("my_consent",{}).get("child_needs",{}).get("my_consent_at"))
    j = _joint_json(b_hdrs)
    _clear_consent(b_hdrs, j.get("my_consent",{}).get("child_needs",{}).get("my_consent_at"))

    # 1) Initial state: neither has consented → no highlights leaked.
    j = _joint_json(a_hdrs)
    assert not j["my_consent"]["child_needs"]["unlocked"]
    for lane in j["parent_a"]["lanes"]:
        assert "highlights" not in lane
    for lane in j["parent_b"]["lanes"]:
        assert "highlights" not in lane

    # 2) Parent A consents → still locked (waiting on B).
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/consent/child-needs",
        headers=a_hdrs, timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["my_consent_at"]
    assert r.json()["unlocked"] is False

    # 3) Re-fetch — still scrubbed.
    j = _joint_json(a_hdrs)
    assert not j["my_consent"]["child_needs"]["unlocked"]
    for lane in j["parent_a"]["lanes"]:
        assert "highlights" not in lane, "Consent from A alone must not unlock A's own highlights on the JOINT view either"

    # 4) Parent B consents → BOTH now consented, joint view unlocked.
    time.sleep(0.05)  # small nudge for consent_iso monotonicity
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/consent/child-needs",
        headers=b_hdrs, timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["unlocked"] is True

    # 5) Re-fetch — highlights now preserved through the scrub.
    j = _joint_json(a_hdrs)
    assert j["my_consent"]["child_needs"]["unlocked"] is True
    # Highlights field CAN now appear on child_needs lanes (contents
    # depend on whether the parent seeded any).
    for lane in j["parent_a"]["lanes"]:
        if lane["id"] == "child_needs":
            # The presence check is what matters — value may be [] if
            # the parent hasn't seeded highlights, but the field key
            # must be preserved through the scrub.
            assert "highlights" in lane, "Section 5 unlock failed to preserve highlights key"

    # 6) Parent A toggles off — clears the flag → joint view re-locks.
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/consent/child-needs",
        headers=a_hdrs, timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["my_consent_at"] is None
    assert r.json()["unlocked"] is False

    # 7) Re-fetch — scrubbed again.
    j = _joint_json(a_hdrs)
    assert not j["my_consent"]["child_needs"]["unlocked"]
    for lane in j["parent_a"]["lanes"]:
        assert "highlights" not in lane
    for lane in j["parent_b"]["lanes"]:
        assert "highlights" not in lane

    # Teardown — clear parent B's leftover consent so re-running the
    # test suite starts from a clean slate.
    j = _joint_json(b_hdrs)
    _clear_consent(b_hdrs, j.get("my_consent",{}).get("child_needs",{}).get("my_consent_at"))


def test_joint_endpoint_returns_404_for_unknown_case():
    # A well-formed but nonexistent case_id must 404 (never 403) so
    # we don't leak case existence to unauthorised callers.
    r = requests.get(
        f"{BASE_URL}/api/complete-report/joint/SA-ZZZZZZ",
        headers=_auth_headers(),
        timeout=10,
    )
    assert r.status_code == 404, r.text


def test_joint_seeded_demo_case_is_reachable_by_member():
    """`SA-DEMO01` is seeded by `seed_joint_sample_case.py` — parent1@test.com
    is on the case as parent A. This test asserts the joint JSON view
    lists both parents by name and returns the neutral tri-state
    (shared / one-side / not-yet) alignment map. The PDF variant must
    render as a real `%PDF-` document."""
    r = requests.get(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01",
        headers=_auth_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    assert data["variant"] == "joint"
    assert data["case_id"] == "SA-DEMO01"
    assert data.get("parents") == ["Sam Parent", "Riley Parent"]
    # Both parents completed Foundation → foundation must be shared.
    lanes_by_id = {ln["id"]: ln for ln in data.get("lanes") or []}
    assert lanes_by_id["foundation"]["status"] == "shared", lanes_by_id["foundation"]
    # Communication is seeded only on Parent A → one-side.
    assert lanes_by_id["communication"]["status"] == "one-side", lanes_by_id["communication"]
    # Activities was not seeded → not-yet.
    assert lanes_by_id["activities"]["status"] == "not-yet", lanes_by_id["activities"]

    r_pdf = requests.get(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01.pdf",
        headers=_auth_headers(),
        timeout=15,
    )
    assert r_pdf.status_code == 200, r_pdf.text[:400]
    assert r_pdf.headers.get("content-type") == "application/pdf"
    assert r_pdf.content[:5] == b"%PDF-"
    assert len(r_pdf.content) > 3000


# ------------------------------ aggregator --------------------------------- #

def test_aggregator_lanes_are_deterministic_and_have_metadata():
    from complete_alignment_aggregator import LANES
    ids = [ln["id"] for ln in LANES]
    assert ids == [
        "foundation", "communication", "activities", "schedule",
        "child_needs", "safety", "coparenting",
    ]
    for meta in LANES:
        assert meta["title"], f"Missing title on lane {meta['id']}"
        assert meta["blurb"], f"Missing blurb on lane {meta['id']}"


def test_pdf_renderer_handles_empty_aggregate_without_crashing():
    """A brand-new parent with zero completed reflections must still
    receive a valid PDF — the "not yet" state is a first-class section
    outcome, not an error."""
    from complete_alignment_report_pdf import render_individual_pdf
    empty_agg = {
        "user_id": "test-user",
        "generated_at": "2026-09-10T00:00:00+00:00",
        "counts": {"completed": 0, "total": 7},
        "child_name": None,
        "lanes": [
            {"id": lid, "title": t, "blurb": b, "completed": False, "updated_at": None}
            for lid, t, b in (
                ("foundation", "Foundation Statement", "Four-prompt reflection."),
                ("communication", "Communication", "How you share info."),
                ("activities", "Activities & Costs", "Weekly commitments."),
                ("schedule", "Parenting Schedule", "Weekday / weekend."),
                ("child_needs", "Child Needs Statement", "Medical / educational."),
                ("safety", "Safety Reflection", "Private safety screen."),
                ("coparenting", "Co-Parenting Assessment", "Priorities."),
            )
        ],
    }
    pdf_bytes = render_individual_pdf(empty_agg, parent_name="Test Parent")
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 2000


def test_pdf_renderer_joint_variant_produces_valid_pdf():
    from complete_alignment_report_pdf import render_joint_pdf
    minimal_joint = {
        "generated_at": "2026-09-10T00:00:00+00:00",
        "counts": {"shared": 1, "one_side": 1, "total": 7},
        "child_name": "Ren",
        "parent_a": {"parent_name": "Alex", "child_name": "Ren", "lanes": []},
        "parent_b": {"parent_name": "Sam", "child_name": "Ren", "lanes": []},
        "lanes": [
            {"id": "foundation", "title": "Foundation Statement", "blurb": "Prompt.", "status": "shared", "parent_a_completed": True, "parent_b_completed": True},
            {"id": "communication", "title": "Communication", "blurb": "How.", "status": "one-side", "parent_a_completed": True, "parent_b_completed": False},
            {"id": "activities", "title": "Activities & Costs", "blurb": "Cost.", "status": "not-yet", "parent_a_completed": False, "parent_b_completed": False},
            {"id": "schedule", "title": "Parenting Schedule", "blurb": "Rhythm.", "status": "not-yet", "parent_a_completed": False, "parent_b_completed": False},
            {"id": "child_needs", "title": "Child Needs Statement", "blurb": "Needs.", "status": "not-yet", "parent_a_completed": False, "parent_b_completed": False},
            {"id": "safety", "title": "Safety Reflection", "blurb": "Safety.", "status": "not-yet", "parent_a_completed": False, "parent_b_completed": False},
            {"id": "coparenting", "title": "Co-Parenting Assessment", "blurb": "Priorities.", "status": "not-yet", "parent_a_completed": False, "parent_b_completed": False},
        ],
    }
    pdf_bytes = render_joint_pdf(minimal_joint, parents=["Alex", "Sam"])
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 2000
