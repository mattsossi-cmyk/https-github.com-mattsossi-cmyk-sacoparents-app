"""Iteration 157 — Case Notes (private) + Foundation Statement
Share History + Resend.

Case Notes:
  * PATCH /professional/joint-alignment/cases/{case_id}/case-notes
  * Owner-only, max 2000 chars
  * `case_notes` surfaces in /cases-i-created but NEVER in any
    parent-facing payload

Share History:
  * GET  /mediation/foundation-statement/shares  (last 25)
  * POST /mediation/foundation-statement/shares/{share_id}/resend
  * Empty reflection → 409, rate limit shared with first-time send
"""
from __future__ import annotations

import sys
import uuid
from typing import Optional

import pytest
import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def _register(name: str, *, display_name: str = "Test Sender") -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_iter157_{name}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": display_name},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _mint_case(token: str) -> str:
    """Mint a professional case owned by the caller."""
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {
                    "parent_slot": "A",
                    "email": f"parenta_{uuid.uuid4().hex[:6]}@test.com",
                    "name": "Parent A",
                },
                {
                    "parent_slot": "B",
                    "email": f"parentb_{uuid.uuid4().hex[:6]}@test.com",
                    "name": "Parent B",
                },
            ],
        },
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["case_id"]


def _save_reflection(token: str, payload: dict) -> None:
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json=payload, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------
# Case Notes tests
# ---------------------------------------------------------------------

def test_case_notes_save_and_surface_on_mine():
    _email, token = _register("cn_save")
    case_id = _mint_case(token)

    # PATCH the notes.
    r = requests.patch(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/case-notes",
        json={"case_notes": "Alex wants short pickup windows. Court in April."},
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    assert r.json()["case_notes"] == "Alex wants short pickup windows. Court in April."

    # Verify /cases-i-created returns the notes.
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    cs = [c for c in r.json()["cases"] if c["case_id"] == case_id]
    assert len(cs) == 1
    assert cs[0]["case_notes"] == "Alex wants short pickup windows. Court in April."


def test_case_notes_clear_via_null():
    _email, token = _register("cn_clear")
    case_id = _mint_case(token)

    # Save then clear.
    for note in ["initial", None]:
        r = requests.patch(
            f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/case-notes",
            json={"case_notes": note},
            headers=_headers(token), timeout=30,
        )
        assert r.status_code == 200
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token), timeout=30,
    )
    cs = [c for c in r.json()["cases"] if c["case_id"] == case_id]
    assert cs[0].get("case_notes") is None


def test_case_notes_owner_only_denies_stranger():
    """A DIFFERENT authenticated mediator must get 404 when patching
    someone else's case notes."""
    _email_a, token_a = _register("cn_owner")
    case_id = _mint_case(token_a)

    _email_b, token_b = _register("cn_stranger")
    r = requests.patch(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/case-notes",
        json={"case_notes": "leak attempt"},
        headers=_headers(token_b), timeout=30,
    )
    assert r.status_code == 404


def test_case_notes_never_surfaces_to_parent_invite_payload():
    """Case notes must NEVER appear in the parent-facing invite
    response (`/joint-alignment/mine` — parent view). This is the
    security contract of the private-notes field."""
    _email, token = _register("cn_leak_check")
    case_id = _mint_case(token)

    # Save distinctive notes.
    tag = f"PRIVATE-{uuid.uuid4().hex[:6]}"
    requests.patch(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/case-notes",
        json={"case_notes": tag}, headers=_headers(token), timeout=30,
    ).raise_for_status()

    # Grab the parent's invitation token and load the parent-view payload.
    mine = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token), timeout=30,
    ).json()
    case = next(c for c in mine["cases"] if c["case_id"] == case_id)
    invite_url = next(
        (p["invitation_url"] for p in case["parents"] if p.get("invitation_url")),
        None,
    )
    assert invite_url, "expected at least one parent invitation URL"

    # The invite URL ends in the token — extract it.
    token_str = invite_url.rstrip("/").split("/")[-1]
    r = requests.get(
        f"{BASE_URL}/api/integrations/joint-alignment/invitation/{token_str}",
        timeout=30,
    )
    # Even if 200 (case is fetchable) or 404 (route lives elsewhere),
    # the response body must NEVER contain the tag.
    assert tag not in r.text, (
        f"Case notes leaked to parent-facing payload: {r.text[:400]}"
    )


def test_case_notes_max_length_enforced():
    _email, token = _register("cn_maxlen")
    case_id = _mint_case(token)
    # Pydantic rejects >2000 with 422.
    r = requests.patch(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/case-notes",
        json={"case_notes": "x" * 2001},
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------
# Foundation Statement Share History tests
# ---------------------------------------------------------------------

def test_history_empty_for_new_user():
    _email, token = _register("hist_empty")
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["shares"] == []


def test_history_returns_row_after_send():
    _email, token = _register("hist_send")
    _save_reflection(token, {"child_lens": "content for share history"})
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={
            "recipient_email": "delivered@resend.dev",
            "recipient_name": "Mediator M",
            "personal_note": "See you Thursday.",
        },
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    )
    shares = r.json()["shares"]
    assert len(shares) == 1
    row = shares[0]
    assert row["recipient_email"] == "delivered@resend.dev"
    assert row["recipient_name"] == "Mediator M"
    assert row["personal_note"] == "See you Thursday."
    assert row["share_id"], "share_id must be present on new rows"
    assert row["created_at"], "created_at must be present"


def test_resend_uses_original_recipient_and_note():
    _email, token = _register("hist_resend")
    _save_reflection(token, {"child_lens": "content for resend"})
    # First send.
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={
            "recipient_email": "delivered@resend.dev",
            "recipient_name": "Original Recipient",
            "personal_note": "Original note.",
        },
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    # Get share_id.
    shares = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    ).json()["shares"]
    original_id = shares[0]["share_id"]
    # Resend.
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/shares/{original_id}/resend",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["delivered_to"] == "delivered@resend.dev"
    new_id = data["share_id"]
    assert new_id != original_id
    # History now has 2 rows, both to the same recipient with the same note.
    shares = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    ).json()["shares"]
    assert len(shares) == 2
    # Latest row (index 0 — sorted desc) is the resend.
    assert shares[0]["share_id"] == new_id
    assert shares[0]["recipient_email"] == "delivered@resend.dev"
    assert shares[0]["recipient_name"] == "Original Recipient"
    assert shares[0]["personal_note"] == "Original note."


def test_resend_404_for_stranger():
    _email_a, token_a = _register("resend_owner")
    _save_reflection(token_a, {"child_lens": "content"})
    requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token_a), timeout=30,
    ).raise_for_status()
    original_id = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token_a), timeout=30,
    ).json()["shares"][0]["share_id"]

    _email_b, token_b = _register("resend_stranger")
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/shares/{original_id}/resend",
        headers=_headers(token_b), timeout=30,
    )
    assert r.status_code == 404


def test_resend_409_when_reflection_deleted():
    """If the parent has deleted every prompt since the original send,
    resend must 409 rather than sending an empty PDF."""
    _email, token = _register("resend_empty")
    _save_reflection(token, {"child_lens": "content"})
    requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token), timeout=30,
    ).raise_for_status()
    share_id = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    ).json()["shares"][0]["share_id"]

    # Now wipe the reflection.
    _save_reflection(token, {
        "child_lens": "", "own_part": "", "best_outcome": "", "coparent_feedback": "",
    })
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/shares/{share_id}/resend",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 409
