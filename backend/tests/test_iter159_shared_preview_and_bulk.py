"""Iteration 159 — Shared Preview Page + Reminder Preview + Bulk CSV.

Three feature blocks tested together:
  * Foundation Statement token-linked public preview page
    (`/foundation-statement/shared/{token}` + voice endpoints).
  * Reminder-email preview endpoint (owner-only, renders WITHOUT
    dispatching to Resend).
  * Bulk CSV importer for Joint Alignment cases (100 rows max,
    duplicate detection, template download).

All tests are live-server via `requests` + BASE_URL — matching the
convention set by iter150+, iter155, iter158. Where a test requires
minted cases or reflections, a fresh isolated account is registered
per-test so runs are order-independent.
"""
from __future__ import annotations

import io
import sys
import uuid
from typing import Optional, Tuple

import pytest
import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _register(prefix: str) -> Tuple[str, str, str]:
    """Return (email, token, user_id) for a fresh isolated user."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"User {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return email, data["access_token"], data.get("user", {}).get("user_id", "")


def _headers(token: Optional[str]) -> dict:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _save_reflection(token: str, payload: dict) -> None:
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json=payload, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------
# Foundation Statement — shared preview
# ---------------------------------------------------------------------

def _mint_share_link(token: str) -> str:
    """Trigger a share that includes a preview_url and return the
    embedded token (last URL segment)."""
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    preview_url = r.json().get("preview_url", "")
    assert preview_url.startswith("http"), f"missing preview URL in {r.json()}"
    return preview_url.split("/")[-1]


def test_share_response_includes_preview_url_and_expiry():
    _email, tok, _ = _register("shpreview")
    _save_reflection(tok, {"child_lens": "content"})
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["preview_url"].startswith("http")
    assert "/foundation/shared/" in data["preview_url"]
    assert data["preview_expires_in_days"] == 30


def test_shared_json_endpoint_public_and_returns_sections():
    _email, tok, _ = _register("shjson")
    _save_reflection(tok, {
        "child_lens": "handoffs feel rushed",
        "best_outcome": "calmer weeknights",
    })
    share_token = _mint_share_link(tok)
    # Unauthenticated — public endpoint.
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}",
        timeout=30,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["sender_name"]
    assert len(payload["sections"]) == 2
    assert payload["sections"][0]["key"] == "child_lens"
    assert payload["sections"][0]["text"] == "handoffs feel rushed"
    # Sender / user_id metadata should NEVER be leaked to the recipient.
    assert "user_id" not in payload
    assert "sender_email" not in payload


def test_shared_endpoint_404s_for_invalid_token():
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/not.a.token",
        timeout=30,
    )
    assert r.status_code == 404


def test_shared_voice_manifest_returns_public_urls():
    _email, tok, _ = _register("shvoice")
    _save_reflection(tok, {"child_lens": "public voice test"})
    share_token = _mint_share_link(tok)
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}/voice/manifest",
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["voice"] == "shimmer"
    assert data["sections"][0]["audio_url"].startswith(
        f"/api/mediation/foundation-statement/shared/{share_token}/voice/section/",
    )
    assert data["supported_voices"] == ["shimmer", "nova", "alloy", "fable"]


def test_shared_endpoint_404s_when_reflection_cleared():
    _email, tok, _ = _register("shcleared")
    _save_reflection(tok, {"child_lens": "gonna clear"})
    share_token = _mint_share_link(tok)
    # Wipe the reflection — the previously-minted preview link
    # should now 404 with a "removed content" message.
    _save_reflection(tok, {"child_lens": "", "own_part": "",
                          "best_outcome": "", "coparent_feedback": ""})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}",
        timeout=30,
    )
    assert r.status_code == 404
    assert "removed" in r.json()["detail"].lower()


# ---------------------------------------------------------------------
# Reminder Preview Modal
# ---------------------------------------------------------------------

def _mint_case(token: str, *, reminder_note: str = "") -> str:
    body = {
        "assessment_type": "communication",
        "parents": [
            {"email": f"parent-a-{uuid.uuid4().hex[:6]}@example.com", "name": "Parent A"},
            {"email": f"parent-b-{uuid.uuid4().hex[:6]}@example.com", "name": "Parent B"},
        ],
    }
    if reminder_note:
        body["reminder_note"] = reminder_note
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json=body, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["case_id"]


def test_reminder_preview_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/SA-000000/reminder-preview",
        timeout=30,
    )
    assert r.status_code == 401


def test_reminder_preview_happy_path_renders_html_and_text():
    _email, tok, _ = _register("rpreview")
    case_id = _mint_case(tok, reminder_note="See you Thursday.")
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["case_id"] == case_id
    assert data["parent_index"] == 0
    assert data["parent_email"].startswith("parent-a-")
    assert data["parent_accepted"] is False
    assert data["has_reminder_note"] is True
    assert case_id in data["subject"]
    assert case_id in data["text"]
    assert "Thursday" in data["text"]
    # HTML branded template.
    assert "<html" in data["html"].lower()
    assert "gentle reminder" in data["html"].lower()


def test_reminder_preview_parent_index_1_selects_second_parent():
    _email, tok, _ = _register("rprev2")
    case_id = _mint_case(tok)
    r0 = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview?parent_index=0",
        headers=_headers(tok), timeout=30,
    )
    r1 = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview?parent_index=1",
        headers=_headers(tok), timeout=30,
    )
    assert r0.status_code == 200 and r1.status_code == 200
    assert r0.json()["parent_email"] != r1.json()["parent_email"]


def test_reminder_preview_400_for_out_of_range_parent_index():
    _email, tok, _ = _register("rprev400")
    case_id = _mint_case(tok)
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview?parent_index=99",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 400


def test_reminder_preview_404_for_foreign_case():
    _email_a, tok_a, _ = _register("rprevA")
    _email_b, tok_b, _ = _register("rprevB")
    case_id = _mint_case(tok_a)
    # Mediator B tries to preview mediator A's case → 404.
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview",
        headers=_headers(tok_b), timeout=30,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# Bulk CSV Import
# ---------------------------------------------------------------------

def _upload_csv(token: str, csv_text: str, **params) -> requests.Response:
    files = {"file": ("bulk.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    return requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )


def test_bulk_csv_requires_auth():
    files = {"file": ("bulk.csv", io.BytesIO(b"parent1_email,parent2_email\n"), "text/csv")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv",
        files=files, timeout=30,
    )
    assert r.status_code == 401


def test_bulk_csv_rejects_non_csv_filename():
    _email, tok, _ = _register("bulkcsv1")
    files = {"file": ("bulk.txt", io.BytesIO(b"parent1_email,parent2_email\n"), "text/plain")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv",
        files=files,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code == 400


def test_bulk_csv_rejects_missing_required_columns():
    _email, tok, _ = _register("bulkcsv2")
    r = _upload_csv(tok, "parent1_email\nfoo@example.com\n")
    assert r.status_code == 400
    assert "parent1_email" in r.json()["detail"] and "parent2_email" in r.json()["detail"]


def test_bulk_csv_happy_path_mints_cases():
    _email, tok, _ = _register("bulkcsv3")
    csv = (
        "parent1_email,parent2_email,assessment_type,reminder_note\n"
        f"first-{uuid.uuid4().hex[:6]}@example.com,"
        f"second-{uuid.uuid4().hex[:6]}@example.com,communication,See you Thursday.\n"
    )
    r = _upload_csv(tok, csv)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_rows"] == 1
    assert len(data["created"]) == 1
    assert data["created"][0]["case_id"].startswith("SA-")
    assert data["created"][0]["assessment_type"] == "communication"


def test_bulk_csv_silent_skips_duplicates_on_reupload():
    _email, tok, _ = _register("bulkcsv4")
    a = f"a-{uuid.uuid4().hex[:6]}@example.com"
    b = f"b-{uuid.uuid4().hex[:6]}@example.com"
    csv = (
        "parent1_email,parent2_email,assessment_type\n"
        f"{a},{b},communication\n"
    )
    first = _upload_csv(tok, csv)
    assert first.status_code == 200
    assert len(first.json()["created"]) == 1
    # Re-upload identical CSV → same pair should now silently skip.
    second = _upload_csv(tok, csv)
    assert second.status_code == 200
    data = second.json()
    assert len(data["created"]) == 0
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["reason"] == "duplicate"


def test_bulk_csv_errored_rows_do_not_abort_the_batch():
    _email, tok, _ = _register("bulkcsv5")
    csv = (
        "parent1_email,parent2_email,assessment_type\n"
        f"good1-{uuid.uuid4().hex[:6]}@example.com,good2-{uuid.uuid4().hex[:6]}@example.com,communication\n"
        f"not-an-email,broken-{uuid.uuid4().hex[:6]}@example.com,communication\n"
        f"missing-lane-{uuid.uuid4().hex[:6]}@example.com,other-{uuid.uuid4().hex[:6]}@example.com,\n"
    )
    r = _upload_csv(tok, csv)
    assert r.status_code == 200
    data = r.json()
    assert data["total_rows"] == 3
    assert len(data["created"]) == 1
    assert len(data["errored"]) == 2
    reasons = " ".join(e["reason"] for e in data["errored"]).lower()
    assert "email" in reasons
    assert "assessment_type" in reasons


def test_bulk_csv_default_lane_falls_back_for_empty_rows():
    _email, tok, _ = _register("bulkcsv6")
    csv = (
        "parent1_email,parent2_email\n"
        f"lane-x-{uuid.uuid4().hex[:6]}@example.com,lane-y-{uuid.uuid4().hex[:6]}@example.com\n"
    )
    r = _upload_csv(tok, csv, default_assessment_type="co-parenting")
    assert r.status_code == 200
    data = r.json()
    assert len(data["created"]) == 1
    assert data["created"][0]["assessment_type"] == "co-parenting"


def test_bulk_csv_enforces_100_row_cap():
    _email, tok, _ = _register("bulkcsv7")
    # 101 data rows.
    rows = ["parent1_email,parent2_email,assessment_type"]
    for i in range(101):
        rows.append(f"cap-{i}-a@example.com,cap-{i}-b@example.com,communication")
    r = _upload_csv(tok, "\n".join(rows) + "\n")
    assert r.status_code == 413


def test_bulk_csv_template_endpoint():
    _email, tok, _ = _register("bulkcsv8")
    r = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv/template",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "parent1_email" in r.text
    assert "parent2_email" in r.text
    assert "assessment_type" in r.text
