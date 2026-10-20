"""Iteration 155 — Foundation Statement PDF + share endpoints.

Structured in two blocks:
  * Pure unit tests for the PDF builder + content guard.
  * Live-server API tests via `requests` + BASE_URL (same pattern as
    the rest of the backend test suite; TestClient trips over
    Motor's shared event loop).
"""
from __future__ import annotations

import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import requests

sys.path.insert(0, "/app/backend")

from foundation_statement_pdf import (
    build_foundation_statement_pdf,
    foundation_statement_has_content,
)
from tests.conftest import BASE_URL  # noqa: E402


# ---------------------------------------------------------------------
# Pure builder tests
# ---------------------------------------------------------------------

def test_pdf_builder_composes_four_prompts(tmp_path: Path) -> None:
    pdf_bytes = build_foundation_statement_pdf(
        author_name="Sam Parent",
        reflection={
            "child_lens": "AAA child perspective content.",
            "own_part": "BBB my own part content.",
            "best_outcome": "CCC best outcome content.",
            "coparent_feedback": "DDD coparent perspective content.",
        },
    )
    assert pdf_bytes[:4] == b"%PDF"
    p = tmp_path / "f.pdf"; p.write_bytes(pdf_bytes)
    r = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    text = re.sub(r"\s+", " ", r.stdout)
    assert "Child-Focused Foundation Statement" in text  # PDF title since the parent-report restyle
    assert "Completed by Sam Parent" in text
    assert "THROUGH MY CHILD'S EYES" in text.upper()
    assert "AAA child perspective content" in text
    assert "MY OWN PART" in text.upper()
    assert "BBB my own part content" in text
    assert "MY BEST-CASE OUTCOME" in text.upper()
    assert "CCC best outcome content" in text
    assert "THROUGH MY CO-PARENT'S EYES" in text.upper()
    assert "DDD coparent perspective content" in text
    # Court-report disclaimer present
    assert "COURT" in text.upper() or "MEDIATION" in text.upper()


def test_pdf_builder_skips_empty_prompts(tmp_path: Path) -> None:
    pdf_bytes = build_foundation_statement_pdf(
        author_name="Riley Parent",
        reflection={
            "child_lens": "Only this section.",
            "own_part": "",
            "best_outcome": "   ",
        },
    )
    p = tmp_path / "f.pdf"; p.write_bytes(pdf_bytes)
    r = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=30)
    text = re.sub(r"\s+", " ", r.stdout).upper()
    assert "THROUGH MY CHILD'S EYES" in text
    assert "MY OWN PART" not in text
    assert "MY BEST-CASE OUTCOME" not in text


def test_pdf_builder_raises_on_empty_reflection() -> None:
    with pytest.raises(ValueError):
        build_foundation_statement_pdf(
            author_name="Sam", reflection={"child_lens": "", "own_part": "   "},
        )
    with pytest.raises(ValueError):
        build_foundation_statement_pdf(author_name="Sam", reflection={})


@pytest.mark.parametrize(
    "reflection,expected",
    [
        ({"child_lens": "x"}, True),
        ({"own_part": "  "}, False),
        ({}, False),
        (None, False),
        ("not a dict", False),
        ({"worry": "legacy content"}, True),
    ],
)
def test_has_content_guard(reflection, expected):
    assert foundation_statement_has_content(reflection) is expected


# ---------------------------------------------------------------------
# Live-server API tests
# ---------------------------------------------------------------------

def _register(name: str) -> tuple[str, str]:
    """Register a fresh isolated parent and return (email, bearer)."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_fnd_{name}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": f"Foundation {name}"},
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


def test_api_download_pdf_409_when_empty():
    _email, token = _register("dl409")
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement.pdf",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 409
    assert "empty" in r.json()["detail"].lower()


def test_api_download_pdf_200_when_content():
    _email, token = _register("dl200")
    _save_reflection(token, {"child_lens": "content", "own_part": "more content"})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement.pdf",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # The endpoint MUST send the file as an attachment (not inline) so
    # the browser triggers a download instead of rendering the PDF
    # inside an iframe — matters on mobile Safari.
    disposition = r.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower(), disposition
    assert "foundation-statement.pdf" in disposition, disposition
    assert r.content[:4] == b"%PDF"


def test_api_share_rejects_self_recipient():
    email, token = _register("self")
    _save_reflection(token, {"child_lens": "content"})
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": email}, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 400
    assert "yourself" in r.json()["detail"].lower()


def test_api_share_409_when_empty():
    _email, token = _register("share409")
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "somebody@example.com"},
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 409


def test_api_share_happy_path_via_resend_test_address():
    """Uses Resend's official testing address so the send actually
    completes without touching a real inbox. Also verifies the
    audit row lands with the remaining-this-hour counter."""
    _email, token = _register("happy")
    _save_reflection(token, {
        "child_lens": "handoffs feel rushed",
        "best_outcome": "calmer weeknights",
    })
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={
            "recipient_email": "delivered@resend.dev",
            "recipient_name": "Test Mediator",
            "personal_note": "Looking forward to Thursday.",
        },
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["delivered_to"] == "delivered@resend.dev"
    assert data["remaining_this_hour"] == 4  # 5 max - this one = 4 remaining


def test_api_share_rate_limit_429_after_five_sends():
    """Sixth send within the hour must 429 with a friendly message.
    Uses Resend's testing address so the first five actually deliver."""
    _email, token = _register("ratelimit")
    _save_reflection(token, {"child_lens": "content for rate limit test"})
    for i in range(5):
        r = requests.post(
            f"{BASE_URL}/api/mediation/foundation-statement/share",
            json={"recipient_email": "delivered@resend.dev"},
            headers=_headers(token), timeout=30,
        )
        assert r.status_code == 200, f"send #{i + 1}: {r.status_code} {r.text}"
        assert r.json()["remaining_this_hour"] == 5 - i - 1
    r6 = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/share",
        json={"recipient_email": "delivered@resend.dev"},
        headers=_headers(token), timeout=30,
    )
    assert r6.status_code == 429, r6.text
    assert "hour" in r6.json()["detail"].lower()


def test_pdf_builder_handles_unicode_prompts(tmp_path: Path) -> None:
    """En-dashes, em-dashes, smart quotes, and emoji must not crash
    the latin1-only fpdf2 output — `_safe()` transliterates them."""
    unicode_child = "My child would say — softly — that handoffs feel \u2018rushed\u2019."
    unicode_own = "I over-explain \u2013 that's my part in it. \U0001F60A"  # emoji
    unicode_best = "Calmer weeknights. \u201cLess texting, more listening.\u201d"
    pdf_bytes = build_foundation_statement_pdf(
        author_name="R\u00e9mi Parent",  # accented sender name
        reflection={
            "child_lens": unicode_child,
            "own_part": unicode_own,
            "best_outcome": unicode_best,
        },
    )
    assert pdf_bytes[:4] == b"%PDF"
    p = tmp_path / "u.pdf"; p.write_bytes(pdf_bytes)
    r = subprocess.run(
        ["pdftotext", "-layout", str(p), "-"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0
    text = r.stdout
    # The transliterated content is present — dashes/quotes/emoji
    # collapse to ASCII fallbacks, but the CONTENT still shows up.
    assert "handoffs feel" in text
    assert "over-explain" in text
    assert "Calmer weeknights" in text
    assert "Less texting" in text
    # Latin-1 accented chars survive as-is (fpdf2's latin-1 encoding
    # supports them); only non-latin1 chars (emoji, CJK) get stripped.
    assert "Rémi Parent" in text


def test_api_share_uses_email_local_part_when_sender_has_no_name():
    """A sender registered with an empty display name must still get
    a sensible author string on the PDF (email local-part fallback),
    and the download must succeed."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_fnd_noname_{suffix}@test.com"
    # Fresh register with an EMPTY name.
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": ""},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    _save_reflection(token, {"child_lens": "content for no-name sender"})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement.pdf",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    # Extract and verify the "Written by <local-part>" line is present.
    tmp_pdf = f"/tmp/foundation-noname-{suffix}.pdf"
    with open(tmp_pdf, "wb") as f:
        f.write(r.content)
    proc = subprocess.run(
        ["pdftotext", "-layout", tmp_pdf, "-"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    # `auth.register` lowercases the email, so the local-part
    # fallback used by `_author_display_name` is lowercase too.
    expected_local = email.lower().split("@", 1)[0]
    assert expected_local in proc.stdout, (
        f"Expected fallback author '{expected_local}' on PDF, got:\n{proc.stdout[:600]}"
    )

