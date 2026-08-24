"""Virtru Hosted Gateway (Pattern A) — HIPAA-compliant SMTP relay.

The Virtru Hosted Gateway is a smart-host SMTP relay that inserts
per-message encryption when it sees an `X-Virtru-Encrypt: 1` MIME
header AND the tenant has a matching outbound Security Rule
configured. Authentication is done by the `X-Virtru-Auth` MIME header
(an organisation-specific token supplied by Virtru), NOT by SMTP
AUTH LOGIN.

This module deliberately uses synchronous `smtplib` to match the rest
of `email_service.py`, which already runs the Resend HTTPS SDK
synchronously inside async FastAPI handlers. Introducing `aiosmtplib`
would require cascading `async/await` through every caller and buys
us nothing today — a future refactor can swap this out.

Docs:
  - https://support.virtru.com/hc/en-us/articles/360025586974
  - https://support.virtru.com/hc/en-us/articles/360011915913
  - https://support.virtru.com/hc/en-us/articles/360005943393

Environment variables (all read at call-time so hot-reload works):
  VIRTRU_ENABLED           — "true" to route through Virtru
  VIRTRU_AUTH_HEADER       — value of X-Virtru-Auth (secret; never log)
  VIRTRU_FROM_EMAIL        — envelope + From address (DNS-verified)
  VIRTRU_SMTP_HOST         — default smtp.virtrugateway.com
  VIRTRU_SMTP_PORT         — default 587
  VIRTRU_SMTP_STARTTLS     — default true (explicit STARTTLS on 587)
  VIRTRU_SMTP_TIMEOUT_SECONDS — default 30
  VIRTRU_FORCE_ENCRYPT     — "true" to always add X-Virtru-Encrypt: 1
  VIRTRU_SUBJECT_MARKER    — optional fallback trigger, e.g. "#secure#"
  VIRTRU_FORCE_ENCRYPT_REQUIRED — "true" to refuse fallback to Resend
                                   when Virtru isn't ready (fail-closed)
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Tuple


logger = logging.getLogger(__name__)


class VirtruNotConfigured(RuntimeError):
    """Virtru is disabled or the auth header is missing."""


class VirtruSendError(RuntimeError):
    """SMTP submission to Virtru failed."""


# Application safety cap on total raw attachment bytes. Virtru itself
# permits 150 MB total; base64 MIME overhead pushes wire size ~1.37x,
# so we cap the raw sum well below that. Failure raises before the
# credentials are touched.
_MAX_RAW_ATTACHMENT_BYTES = 100 * 1024 * 1024  # 100 MB


def _bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def virtru_is_ready() -> bool:
    """True if we can currently submit through Virtru.

    Read at call-time so ops can enable/disable without a restart.
    """
    return (
        _bool("VIRTRU_ENABLED")
        and bool(os.environ.get("VIRTRU_AUTH_HEADER"))
        and bool(os.environ.get("VIRTRU_FROM_EMAIL"))
    )


def virtru_force_encrypt_required() -> bool:
    """If true, callers MUST NOT silently fall back to a non-Virtru
    provider when Virtru isn't ready. Fail-closed for HIPAA-scoped
    email once we cut over."""
    return _bool("VIRTRU_FORCE_ENCRYPT_REQUIRED")


def _validate_attachments(attachments: List[Tuple[str, bytes]]) -> None:
    total = sum(len(data) for _, data in attachments)
    if total > _MAX_RAW_ATTACHMENT_BYTES:
        raise VirtruSendError(
            f"Attachments total {total} bytes exceeds the "
            f"{_MAX_RAW_ATTACHMENT_BYTES}-byte safety cap."
        )
    for filename, _data in attachments:
        if not filename.lower().endswith(".pdf"):
            # Nothing here today isn't a PDF, but we surface the
            # constraint explicitly so future callers see it early.
            raise VirtruSendError(f"Only PDF attachments are supported (got {filename!r}).")


def _build_message(
    *,
    from_header: str,
    to_email: str,
    subject: str,
    html: str,
    text: str,
    reply_to: Optional[str],
    attachments: List[Tuple[str, bytes]],
) -> EmailMessage:
    """Assemble an RFC 822 message with the Virtru control headers.

    `X-Virtru-Auth` is added last inside the sending function so it
    never appears in any log line that renders the message.
    """
    msg = EmailMessage()
    msg["From"] = from_header
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Body: text/plain first, then html alternative — same order the
    # branded Resend template uses.
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    for filename, data in attachments:
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )

    if _bool("VIRTRU_FORCE_ENCRYPT", default=False):
        msg["X-Virtru-Encrypt"] = "1"
        marker = (os.environ.get("VIRTRU_SUBJECT_MARKER") or "").strip()
        if marker and marker.lower() not in subject.lower():
            msg.replace_header("Subject", f"{marker} {subject}")
    return msg


def send_via_virtru(
    *,
    to_email: str,
    subject: str,
    html: str,
    text: str,
    reply_to: Optional[str] = None,
    attachments: Optional[List[Tuple[str, bytes]]] = None,
) -> None:
    """Submit a message via the Virtru Hosted Gateway.

    Raises `VirtruNotConfigured` if the tenant isn't provisioned, and
    `VirtruSendError` on SMTP-level failure. Callers decide whether to
    fall back to another provider — see `email_service._send()`.
    """
    if not virtru_is_ready():
        raise VirtruNotConfigured("Virtru is disabled or the auth header is missing.")

    atts = list(attachments or [])
    _validate_attachments(atts)

    from_email = os.environ["VIRTRU_FROM_EMAIL"].strip()
    from_name = (os.environ.get("VIRTRU_FROM_NAME") or "SA CoParents").strip()
    from_header = f"{from_name} <{from_email}>" if from_name else from_email

    msg = _build_message(
        from_header=from_header,
        to_email=to_email,
        subject=subject,
        html=html,
        text=text,
        reply_to=reply_to,
        attachments=atts,
    )

    # `X-Virtru-Auth` is added here, after `_build_message` returns, so
    # that if anything inside `_build_message` were to log the message
    # (it doesn't) the header would still be absent. The secret is
    # NEVER interpolated into log lines below.
    msg["X-Virtru-Auth"] = os.environ["VIRTRU_AUTH_HEADER"]

    host = os.environ.get("VIRTRU_SMTP_HOST", "smtp.virtrugateway.com")
    port = int(os.environ.get("VIRTRU_SMTP_PORT", "587"))
    timeout = float(os.environ.get("VIRTRU_SMTP_TIMEOUT_SECONDS", "30"))
    use_starttls = _bool("VIRTRU_SMTP_STARTTLS", default=True)

    try:
        with smtplib.SMTP(host=host, port=port, timeout=timeout) as smtp:
            if use_starttls:
                smtp.starttls()
            # No SMTP AUTH — Virtru authenticates via the MIME header.
            smtp.send_message(msg, from_addr=from_email, to_addrs=[to_email])
    except (smtplib.SMTPException, OSError) as exc:
        # Explicitly do NOT include the message object or any header
        # value in the log — the auth header is a live secret.
        logger.warning(
            "Virtru send failed host=%s port=%s recipient_domain=%s error=%s",
            host, port, to_email.rsplit("@", 1)[-1] if "@" in to_email else "unknown",
            type(exc).__name__,
        )
        raise VirtruSendError(str(exc)) from exc
