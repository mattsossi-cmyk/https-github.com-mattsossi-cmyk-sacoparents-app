"""iter122 · Virtru Hosted Gateway (Pattern A) — SMTP relay wiring.

Tests use `monkeypatch` + `unittest.mock.patch("smtplib.SMTP")` so no
real SMTP connection is made. We validate:

  * `virtru_is_ready()` gates on all three env vars.
  * The MIME message carries `X-Virtru-Auth` and (when forced)
    `X-Virtru-Encrypt: 1`, plus both PDF attachments.
  * `smtplib.SMTP.starttls()` is called on port 587.
  * The auth header is NEVER logged.
  * Non-PDF attachments are rejected before any SMTP call.
  * `VIRTRU_FORCE_ENCRYPT_REQUIRED=true` blocks Resend fallback when
    Virtru isn't ready (fail-closed).
"""
import io
import logging
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def virtru_env(monkeypatch):
    monkeypatch.setenv("VIRTRU_ENABLED", "true")
    monkeypatch.setenv("VIRTRU_AUTH_HEADER", "test-secret-do-not-log")
    monkeypatch.setenv("VIRTRU_FROM_EMAIL", "reports@sacoparentsapp.online")
    monkeypatch.setenv("VIRTRU_FROM_NAME", "SA CoParents")
    monkeypatch.setenv("VIRTRU_FORCE_ENCRYPT", "true")
    monkeypatch.setenv("VIRTRU_SMTP_HOST", "smtp.virtrugateway.com")
    monkeypatch.setenv("VIRTRU_SMTP_PORT", "587")
    monkeypatch.setenv("VIRTRU_SMTP_STARTTLS", "true")


def test_virtru_is_ready_gates_on_all_three(monkeypatch):
    from virtru_mailer import virtru_is_ready

    monkeypatch.delenv("VIRTRU_ENABLED", raising=False)
    monkeypatch.delenv("VIRTRU_AUTH_HEADER", raising=False)
    monkeypatch.delenv("VIRTRU_FROM_EMAIL", raising=False)
    assert virtru_is_ready() is False

    monkeypatch.setenv("VIRTRU_ENABLED", "true")
    assert virtru_is_ready() is False  # missing auth + from

    monkeypatch.setenv("VIRTRU_AUTH_HEADER", "x")
    assert virtru_is_ready() is False  # missing from

    monkeypatch.setenv("VIRTRU_FROM_EMAIL", "reports@example.com")
    assert virtru_is_ready() is True


def test_send_via_virtru_writes_expected_headers_and_two_attachments(virtru_env):
    from virtru_mailer import send_via_virtru

    with patch("virtru_mailer.smtplib.SMTP") as smtp_cls:
        client = MagicMock()
        smtp_cls.return_value.__enter__.return_value = client

        send_via_virtru(
            to_email="mediator@example.com",
            subject="Joint Co-Parenting Summary — A & B",
            html="<p>hi</p>",
            text="hi",
            reply_to="parent@example.com",
            attachments=[
                ("intro.pdf", b"%PDF-1.4 intro"),
                ("joint-report.pdf", b"%PDF-1.4 report"),
            ],
        )

        # SMTP config
        assert smtp_cls.call_args.kwargs["host"] == "smtp.virtrugateway.com"
        assert smtp_cls.call_args.kwargs["port"] == 587
        client.starttls.assert_called_once()
        # No SMTP AUTH — auth is via MIME header.
        client.login.assert_not_called()

        # Inspect the outgoing message
        args, kwargs = client.send_message.call_args
        msg = args[0]
        assert isinstance(msg, EmailMessage)
        assert msg["X-Virtru-Auth"] == "test-secret-do-not-log"
        assert msg["X-Virtru-Encrypt"] == "1"
        assert msg["To"] == "mediator@example.com"
        assert msg["Reply-To"] == "parent@example.com"
        assert kwargs["from_addr"] == "reports@sacoparentsapp.online"
        assert kwargs["to_addrs"] == ["mediator@example.com"]

        pdfs = [
            (a.get_filename(), a.get_payload(decode=True))
            for a in msg.iter_attachments()
        ]
        assert len(pdfs) == 2
        assert pdfs[0][0] == "intro.pdf"
        assert pdfs[1][0] == "joint-report.pdf"


def test_send_via_virtru_rejects_non_pdf_attachments(virtru_env):
    from virtru_mailer import VirtruSendError, send_via_virtru

    with patch("virtru_mailer.smtplib.SMTP") as smtp_cls:
        with pytest.raises(VirtruSendError):
            send_via_virtru(
                to_email="mediator@example.com",
                subject="s", html="<p/>", text="t",
                attachments=[("bogus.txt", b"nope")],
            )
        smtp_cls.assert_not_called()


def test_send_via_virtru_does_not_log_auth_header(virtru_env, caplog):
    from virtru_mailer import VirtruSendError, send_via_virtru

    with patch("virtru_mailer.smtplib.SMTP") as smtp_cls:
        import smtplib as _smtplib
        smtp_cls.return_value.__enter__.return_value.send_message.side_effect = (
            _smtplib.SMTPException("boom")
        )
        with caplog.at_level(logging.WARNING, logger="virtru_mailer"):
            with pytest.raises(VirtruSendError):
                send_via_virtru(
                    to_email="mediator@example.com",
                    subject="s", html="<p/>", text="t",
                    attachments=[("intro.pdf", b"%PDF")],
                )

    # Auth header must never appear in any log line, even on failure.
    for rec in caplog.records:
        assert "test-secret-do-not-log" not in rec.getMessage()


def test_send_via_virtru_raises_when_not_configured(monkeypatch):
    from virtru_mailer import VirtruNotConfigured, send_via_virtru

    monkeypatch.delenv("VIRTRU_ENABLED", raising=False)
    with pytest.raises(VirtruNotConfigured):
        send_via_virtru(
            to_email="x@example.com", subject="s", html="<p/>", text="t",
            attachments=[("a.pdf", b"%PDF")],
        )


def test_email_service_fails_closed_when_encryption_required(monkeypatch):
    """email_service._send with require_encrypted=True must raise if
    the operator has flagged encryption as mandatory but Virtru isn't
    ready. It must NOT silently fall back to Resend."""
    monkeypatch.setenv("VIRTRU_FORCE_ENCRYPT_REQUIRED", "true")
    monkeypatch.delenv("VIRTRU_ENABLED", raising=False)

    import email_service
    from email_service import EmailSendError

    with pytest.raises(EmailSendError):
        email_service._send(
            to_email="mediator@example.com",
            subject="Joint report",
            html="<p/>",
            text="",
            attachments=[("joint-report.pdf", b"%PDF")],
            failure_message="Couldn't send.",
            require_encrypted=True,
        )
