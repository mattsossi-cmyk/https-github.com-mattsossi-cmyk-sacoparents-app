"""Iteration 161 — Foundation Statement recipient-open analytics.

Tests the "did they read it?" feedback loop:
  * Public shared endpoint records a row per human open.
  * Link-preview bots (Slack / Discord / WhatsApp / etc.) are
    filtered BEFORE the write so an unfurl never inflates the count.
  * History payload includes per-row `open_count`, `last_opened_at`,
    `unique_ip_count`.
  * Aggregation is scoped to the caller (a foreign parent never
    sees another parent's open stats).
  * IP hashing gives unique-viewer count without storing raw IPs.
"""
from __future__ import annotations

import sys
import time
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

import foundation_statement_analytics as fsa  # noqa: E402
from tests.conftest import BASE_URL  # noqa: E402


# ---------------------------------------------------------------------
# Pure unit tests (bot detection, IP hashing)
# ---------------------------------------------------------------------

def test_bot_detection_flags_common_link_preview_crawlers():
    assert fsa.is_link_preview_bot("Slackbot-LinkExpanding 1.0 (+https://slack.com/bot)")
    assert fsa.is_link_preview_bot("WhatsApp/2.23.4")
    assert fsa.is_link_preview_bot("Twitterbot/1.0")
    assert fsa.is_link_preview_bot("facebookexternalhit/1.1")
    assert fsa.is_link_preview_bot("LinkedInBot/1.0 (compatible)")
    assert fsa.is_link_preview_bot("TelegramBot (like TwitterBot)")
    assert fsa.is_link_preview_bot("Discordbot/2.0")


def test_bot_detection_flags_scripts_and_missing_ua():
    assert fsa.is_link_preview_bot(None)
    assert fsa.is_link_preview_bot("")
    assert fsa.is_link_preview_bot("curl/7.68.0")
    assert fsa.is_link_preview_bot("Wget/1.20.3")
    assert fsa.is_link_preview_bot("python-requests/2.31.0")
    assert fsa.is_link_preview_bot("PostmanRuntime/7.32.0")


def test_bot_detection_lets_real_browsers_through():
    # Real recipient browsers. If any of these ever get flagged the
    # entire feature breaks silently.
    real = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    for ua in real:
        assert not fsa.is_link_preview_bot(ua), f"real browser flagged: {ua}"


def test_ip_hashing_is_deterministic_and_short():
    assert fsa._hash_ip(None) is None
    assert fsa._hash_ip("") is None
    a = fsa._hash_ip("192.168.1.1")
    b = fsa._hash_ip("192.168.1.1")
    c = fsa._hash_ip("192.168.1.2")
    assert a == b
    assert a != c
    assert len(a) == 16  # short-hash so we don't hoard IP data


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


def _mint_share(token: str) -> str:
    """Register a reflection, share, return the token last-segment."""
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "content for analytics test"},
        headers=_headers(token), timeout=30,
    )
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token), timeout=30,
    )
    return r.json()["preview_url"].split("/")[-1]


def _open_shared(share_token: str, *, user_agent: str) -> int:
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shared/{share_token}",
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    return r.status_code


# ---------------------------------------------------------------------
# Live-server API tests
# ---------------------------------------------------------------------

def test_history_starts_with_zero_opens():
    _email, tok = _register("anlz1")
    _mint_share(tok)
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    top = r.json()["shares"][0]
    assert top["open_count"] == 0
    assert top["unique_ip_count"] == 0
    assert top["last_opened_at"] is None


def test_human_open_increments_count_and_sets_timestamp():
    _email, tok = _register("anlz2")
    share_token = _mint_share(tok)
    # Two opens with real browser UAs.
    assert _open_shared(share_token, user_agent="Mozilla/5.0 Chrome/120") == 200
    time.sleep(0.05)  # ensure distinct opened_at
    assert _open_shared(share_token, user_agent="Mozilla/5.0 Safari/17") == 200

    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    top = r.json()["shares"][0]
    assert top["open_count"] == 2
    assert top["last_opened_at"] is not None
    assert top["unique_ip_count"] >= 1  # same test-runner IP → 1


def test_bot_open_does_not_count():
    _email, tok = _register("anlz3")
    share_token = _mint_share(tok)
    # These MUST NOT count.
    assert _open_shared(share_token, user_agent="Slackbot-LinkExpanding 1.0") == 200
    assert _open_shared(share_token, user_agent="WhatsApp/2.23") == 200
    assert _open_shared(share_token, user_agent="curl/7.68.0") == 200

    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    top = r.json()["shares"][0]
    assert top["open_count"] == 0, (
        f"expected 0, got {top['open_count']} — bot filter is broken"
    )


def test_bot_and_human_opens_only_count_humans():
    _email, tok = _register("anlz4")
    share_token = _mint_share(tok)
    # Bots first.
    _open_shared(share_token, user_agent="Slackbot-LinkExpanding 1.0")
    _open_shared(share_token, user_agent="WhatsApp/2.23")
    # Then humans.
    _open_shared(share_token, user_agent="Mozilla/5.0 Chrome/120")
    _open_shared(share_token, user_agent="Mozilla/5.0 Firefox/122")

    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    top = r.json()["shares"][0]
    assert top["open_count"] == 2


def test_analytics_are_scoped_per_sender():
    _email_a, tok_a = _register("anlzA")
    _email_b, tok_b = _register("anlzB")
    share_a = _mint_share(tok_a)
    _mint_share(tok_b)  # noise
    # Human opens Sender A's link twice.
    _open_shared(share_a, user_agent="Mozilla/5.0 Chrome/120")
    _open_shared(share_a, user_agent="Mozilla/5.0 Chrome/120")

    hist_a = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok_a), timeout=30,
    ).json()["shares"]
    hist_b = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok_b), timeout=30,
    ).json()["shares"]
    assert hist_a[0]["open_count"] == 2
    # Sender B's share must NOT see Sender A's opens.
    assert hist_b[0]["open_count"] == 0


def test_revoked_link_still_reports_prior_opens():
    _email, tok = _register("anlz6")
    share_token = _mint_share(tok)
    _open_shared(share_token, user_agent="Mozilla/5.0 Chrome/120")
    _open_shared(share_token, user_agent="Mozilla/5.0 Safari/17")
    # Revoke.
    hist = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    ).json()["shares"]
    jti = hist[0]["preview_jti"]
    requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/preview-links/revoke",
        json={"jti": jti}, headers=_headers(tok), timeout=30,
    )
    # After revoke: public URL 404s BUT the history keeps the count.
    assert _open_shared(share_token, user_agent="Mozilla/5.0 Chrome/120") == 404
    hist = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    ).json()["shares"]
    assert hist[0]["preview_status"] == "revoked"
    assert hist[0]["open_count"] == 2  # historical opens preserved


def test_history_row_shape_includes_analytics_fields():
    _email, tok = _register("anlz7")
    _mint_share(tok)
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/shares",
        headers=_headers(tok), timeout=30,
    )
    top = r.json()["shares"][0]
    for key in ("open_count", "last_opened_at", "unique_ip_count"):
        assert key in top, f"history row missing `{key}`"
