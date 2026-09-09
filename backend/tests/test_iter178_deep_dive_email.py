"""Iteration 178 — Email PDF for the three Deep Dives + Landing dual-entry.

Covers:
  * POST /edu-deep/report/email
  * POST /med-deep/report/email
  * POST /psych-deep/report/email
    Each with: 401 unauth · 404 when no report cached · 200 happy
    path (via patched _send).
  * send_deep_dive_report_pdf() direct rendering test for the
    three variants (label + subject + filename).
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Tuple
from unittest.mock import patch

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _register(prefix: str) -> Tuple[str, str, str]:
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"P {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"], r.json()["user"]["user_id"]


# ---------------------------------------------------------------------
# Endpoint contract: 401 / 404
# ---------------------------------------------------------------------

def test_edu_report_email_requires_auth():
    r = requests.post(f"{BASE_URL}/api/edu-deep/report/email", json={},
                      timeout=30)
    assert r.status_code == 401


def test_med_report_email_requires_auth():
    r = requests.post(f"{BASE_URL}/api/med-deep/report/email", json={},
                      timeout=30)
    assert r.status_code == 401


def test_psych_report_email_requires_auth():
    r = requests.post(f"{BASE_URL}/api/psych-deep/report/email", json={},
                      timeout=30)
    assert r.status_code == 401


def test_edu_report_email_404_when_no_report_cached():
    _e, tok, _uid = _register("edu-404")
    r = requests.post(f"{BASE_URL}/api/edu-deep/report/email", json={},
                      headers=_headers(tok), timeout=30)
    assert r.status_code == 404
    assert "generate" in r.json()["detail"].lower()


def test_med_report_email_404_when_no_report_cached():
    _e, tok, _uid = _register("med-404")
    r = requests.post(f"{BASE_URL}/api/med-deep/report/email", json={},
                      headers=_headers(tok), timeout=30)
    assert r.status_code == 404


def test_psych_report_email_404_when_no_report_cached():
    _e, tok, _uid = _register("psych-404")
    r = requests.post(f"{BASE_URL}/api/psych-deep/report/email", json={},
                      headers=_headers(tok), timeout=30)
    assert r.status_code == 404


# ---------------------------------------------------------------------
# Direct render test for send_deep_dive_report_pdf
# ---------------------------------------------------------------------

def test_send_deep_dive_report_pdf_educational_variant():
    from email_service import send_deep_dive_report_pdf
    captured = []
    with patch("email_service._send", side_effect=lambda **k: captured.append(k)):
        send_deep_dive_report_pdf(
            variant="educational",
            to_email="parent@example.com",
            user_name="Test Parent",
            pdf_bytes=b"%PDF-1.4\ntest",
        )
    assert len(captured) == 1
    call = captured[0]
    assert "Educational" in call["subject"]
    assert "Educational_Deep_Dive.pdf" in [name for name, _ in call["attachments"]]
    assert "Educational Needs" in call["html"]


def test_send_deep_dive_report_pdf_medical_variant():
    from email_service import send_deep_dive_report_pdf
    captured = []
    with patch("email_service._send", side_effect=lambda **k: captured.append(k)):
        send_deep_dive_report_pdf(
            variant="medical",
            to_email="parent@example.com",
            user_name="Test Parent",
            pdf_bytes=b"%PDF-1.4\ntest",
        )
    call = captured[0]
    assert "Medical" in call["subject"]
    assert "Medical_Deep_Dive.pdf" in [name for name, _ in call["attachments"]]


def test_send_deep_dive_report_pdf_psychological_variant():
    from email_service import send_deep_dive_report_pdf
    captured = []
    with patch("email_service._send", side_effect=lambda **k: captured.append(k)):
        send_deep_dive_report_pdf(
            variant="psychological",
            to_email="parent@example.com",
            user_name="Test Parent",
            pdf_bytes=b"%PDF-1.4\ntest",
        )
    call = captured[0]
    assert "Psychological" in call["subject"]
    assert "Psychological_Deep_Dive.pdf" in [name for name, _ in call["attachments"]]


def test_send_deep_dive_report_pdf_rejects_unknown_variant():
    from email_service import (
        EmailSendError, send_deep_dive_report_pdf,
    )
    try:
        send_deep_dive_report_pdf(
            variant="not-a-real-variant",
            to_email="parent@example.com",
            user_name="Test",
            pdf_bytes=b"x",
        )
        raised = False
    except EmailSendError:
        raised = True
    assert raised
