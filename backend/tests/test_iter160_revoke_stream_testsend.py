"""Iteration 160 — Revoke Shared Preview + CSV Streaming + Preview Test-Send.

Three feature blocks:
  * Foundation Statement preview-link revocation (parent-owned).
  * Bulk CSV NDJSON streaming endpoint (event-by-event).
  * Reminder Preview "send to my own inbox" test dispatch (rate-limited).
"""
from __future__ import annotations

import io
import json
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

def _register(prefix: str) -> Tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"User {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _save_reflection(token: str, payload: dict) -> None:
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json=payload, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------
# Revoke Shared Preview
# ---------------------------------------------------------------------

def _mint_share_preview_token(token: str) -> Tuple[str, str]:
    """Trigger a share, return (share_token_last_segment, preview_jti)."""
    _save_reflection(token, {"child_lens": "content"})
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    preview_url = r.json()["preview_url"]
    share_token = preview_url.split("/")[-1]
    # Look up the jti via the history endpoint.
    hist = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(token), timeout=30,
    )
    assert hist.status_code == 200
    top = hist.json()["shares"][0]
    assert top["preview_status"] == "active"
    assert top["preview_jti"]
    return share_token, top["preview_jti"]


def test_history_returns_preview_status_active():
    _email, tok = _register("hstpv1")
    _mint_share_preview_token(tok)
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    top = r.json()["shares"][0]
    assert top["preview_status"] == "active"
    assert top["preview_jti"]
    assert top["preview_expires_at"]


def test_revoke_preview_link_flips_shared_endpoint_to_404():
    _email, tok = _register("revpv1")
    share_token, jti = _mint_share_preview_token(tok)
    # Public shared endpoint works before revoke.
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}",
        timeout=30,
    )
    assert r.status_code == 200
    # Revoke.
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": jti}, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["already_revoked"] is False
    # Public endpoint now 404s.
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}",
        timeout=30,
    )
    assert r.status_code == 404
    assert "revoked" in r.json()["detail"].lower()
    # History reflects the new status.
    hist = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    assert hist.json()["shares"][0]["preview_status"] == "revoked"


def test_revoke_preview_link_is_idempotent():
    _email, tok = _register("revpv2")
    _share_token, jti = _mint_share_preview_token(tok)
    r1 = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": jti}, headers=_headers(tok), timeout=30,
    )
    r2 = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": jti}, headers=_headers(tok), timeout=30,
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["already_revoked"] is False
    assert r2.json()["already_revoked"] is True


def test_revoke_preview_link_404_for_foreign_jti():
    _email_a, tok_a = _register("revpvA")
    _email_b, tok_b = _register("revpvB")
    _share_token, jti = _mint_share_preview_token(tok_a)
    # Parent B tries to revoke parent A's token → 404.
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": jti}, headers=_headers(tok_b), timeout=30,
    )
    assert r.status_code == 404


def test_revoke_preview_link_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": "abcdef1234567890"}, timeout=30,
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------
# Bulk CSV Streaming
# ---------------------------------------------------------------------

def _stream_upload(token: str, csv_text: str, **params) -> list:
    """POST to the stream endpoint and return the parsed NDJSON events."""
    files = {"file": ("bulk.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv/stream",
        files=files, params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60, stream=True,
    )
    r.raise_for_status()
    events = []
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        events.append(json.loads(line))
    return events


def test_stream_emits_start_row_done_events_in_order():
    _email, tok = _register("stream1")
    csv = (
        "parent1_email,parent2_email,assessment_type\n"
        f"strm-a-{uuid.uuid4().hex[:6]}@example.com,strm-b-{uuid.uuid4().hex[:6]}@example.com,communication\n"
    )
    events = _stream_upload(tok, csv)
    assert len(events) >= 3
    assert events[0]["event"] == "start"
    assert events[0]["total_rows"] == 1
    assert events[1]["event"] == "row"
    assert events[1]["status"] == "created"
    assert events[1]["case_id"].startswith("SA-")
    assert events[-1]["event"] == "done"
    assert events[-1]["summary"]["created"] == 1


def test_stream_reports_duplicates_and_errors_as_row_events():
    _email, tok = _register("stream2")
    good_a = f"a-{uuid.uuid4().hex[:6]}@example.com"
    good_b = f"b-{uuid.uuid4().hex[:6]}@example.com"
    # First upload: mint good pair.
    first = (
        "parent1_email,parent2_email,assessment_type\n"
        f"{good_a},{good_b},communication\n"
    )
    events = _stream_upload(tok, first)
    assert events[-1]["summary"]["created"] == 1
    # Second upload: same pair + one bad.
    second = (
        "parent1_email,parent2_email,assessment_type\n"
        f"{good_a},{good_b},communication\n"
        f"not-an-email,other-{uuid.uuid4().hex[:6]}@example.com,communication\n"
    )
    events = _stream_upload(tok, second)
    row_events = [e for e in events if e["event"] == "row"]
    assert len(row_events) == 2
    statuses = sorted([r["status"] for r in row_events])
    assert statuses == ["errored", "skipped"]
    assert events[-1]["summary"] == {
        "total_rows": 2, "created": 0, "skipped": 1, "errored": 1,
    }


def test_stream_400s_before_stream_starts_on_missing_headers():
    _email, tok = _register("stream3")
    csv = "parent1_email\nfoo@example.com\n"
    files = {"file": ("bulk.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv/stream",
        files=files,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code == 400
    assert "parent2_email" in r.json()["detail"]


def test_stream_413_over_row_cap():
    _email, tok = _register("stream4")
    lines = ["parent1_email,parent2_email,assessment_type"]
    for i in range(101):
        lines.append(f"cap-{i}-a@example.com,cap-{i}-b@example.com,communication")
    csv = "\n".join(lines) + "\n"
    files = {"file": ("bulk.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv/stream",
        files=files,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code == 413


def test_stream_response_has_ndjson_content_type():
    _email, tok = _register("stream5")
    csv = (
        "parent1_email,parent2_email,assessment_type\n"
        f"nd-a-{uuid.uuid4().hex[:6]}@example.com,nd-b-{uuid.uuid4().hex[:6]}@example.com,communication\n"
    )
    files = {"file": ("bulk.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/bulk-csv/stream",
        files=files,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30, stream=True,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    r.close()


# ---------------------------------------------------------------------
# Preview Test Send
# ---------------------------------------------------------------------

def _mint_case(token: str) -> str:
    body = {
        "assessment_type": "communication",
        "parents": [
            {"email": f"tsend-a-{uuid.uuid4().hex[:6]}@example.com", "name": "Parent A"},
            {"email": f"tsend-b-{uuid.uuid4().hex[:6]}@example.com", "name": "Parent B"},
        ],
        "reminder_note": "See you Thursday.",
    }
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json=body, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["case_id"]


def test_test_send_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/SA-XXXXXX/reminder-preview/send-test",
        timeout=30,
    )
    assert r.status_code == 401


def test_test_send_happy_path_returns_delivered_to():
    _email, tok = _register("tsend1")
    case_id = _mint_case(tok)
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview/send-test",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["delivered_to"].startswith("test_tsend1")
    assert isinstance(data["remaining_this_hour"], int)


def test_test_send_404_for_foreign_case():
    _email_a, tok_a = _register("tsendA")
    _email_b, tok_b = _register("tsendB")
    case_id = _mint_case(tok_a)
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview/send-test",
        headers=_headers(tok_b), timeout=30,
    )
    assert r.status_code == 404


def test_test_send_400_for_out_of_range_parent_index():
    _email, tok = _register("tsend2")
    case_id = _mint_case(tok)
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases/{case_id}/reminder-preview/send-test?parent_index=42",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 400
