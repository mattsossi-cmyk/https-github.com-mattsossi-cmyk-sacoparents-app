"""Email service for SA Coparents — uses Resend (https://resend.com).

Public interface (unchanged, callers don't need to be updated):
  - EmailNotConfigured, EmailSendError
  - send_magic_link(to_email, link_url, user_name=None)
  - send_setup_link(to_email, link_url)
  - send_password_reset_link(to_email, link_url, user_name=None)
  - send_verification_link(to_email, link_url, user_name=None)
  - send_mediator_email(to_email, mediator_name, user_name, user_email, attachments, doc_labels)

All emails are sent through the Resend HTTP API via the `resend` SDK.
Templates remain HTML + plain-text fallback.
"""
import base64
import logging
import os
from typing import List, Optional, Tuple

import resend


logger = logging.getLogger(__name__)


class EmailNotConfigured(Exception):
    """Resend API key is missing — feature should be reported as disabled."""


class EmailSendError(Exception):
    """Resend send failed — surface a friendly message to the user."""


def _config() -> dict:
    return {
        "api_key": os.environ.get("RESEND_API_KEY", "").strip(),
        "from_email": (
            os.environ.get("RESEND_FROM_EMAIL", "").strip()
            or "onboarding@resend.dev"
        ),
        "from_name": os.environ.get("RESEND_FROM_NAME", "SA Coparents").strip(),
        "reply_to": os.environ.get("RESEND_REPLY_TO", "").strip(),
    }


def is_configured() -> bool:
    return bool(_config()["api_key"])


def _from_header(cfg: dict) -> str:
    """Return a `Name <email>` formatted From header."""
    return f'{cfg["from_name"]} <{cfg["from_email"]}>'


def _send(
    *,
    to_email: str,
    subject: str,
    html: str,
    text: str,
    reply_to: Optional[str] = None,
    attachments: Optional[List[Tuple[str, bytes]]] = None,
    failure_message: str,
) -> None:
    """Internal: send via Resend with consistent error handling."""
    if not is_configured():
        raise EmailNotConfigured(
            "Email sending is not configured. Set RESEND_API_KEY and try again."
        )
    cfg = _config()
    resend.api_key = cfg["api_key"]

    params: dict = {
        "from": _from_header(cfg),
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if reply_to or cfg["reply_to"]:
        params["reply_to"] = [reply_to or cfg["reply_to"]]
    if attachments:
        params["attachments"] = [
            {
                "filename": name,
                "content": base64.b64encode(data).decode("ascii"),
            }
            for name, data in attachments
        ]

    try:
        resend.Emails.send(params)
    except Exception as e:
        # Resend raises subclasses of resend.exceptions.ResendError, but the SDK
        # also lets through requests / network errors. Treat them all as send failures.
        logger.exception("Resend send failed: %s", subject)
        raise EmailSendError(failure_message) from e


# ============ Internal helpers ============
def _branded_html(*, headline: str, body_html: str, cta_label: str, cta_url: Optional[str] = None) -> str:
    """Wrap content in the SA Coparents branded email shell."""
    cta = (
        f'<p style="margin:0 0 24px 0;"><a href="{cta_url}" '
        f'style="display:inline-block;background:linear-gradient(135deg,#3D1A78,#2DB5B5);'
        f'color:#fff;text-decoration:none;font-weight:700;padding:14px 28px;'
        f'border-radius:999px;">{cta_label}</a></p>'
        if cta_url
        else ""
    )
    fallback = (
        f'<p style="font-size:13px;color:#857E9C;line-height:1.55;margin:0;">'
        f"If the button doesn't work, copy this link into your browser:<br/>"
        f'<span style="word-break:break-all;color:#3D1A78;">{cta_url}</span></p>'
        if cta_url
        else ""
    )
    return f"""<!doctype html>
<html><body style="font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#F8F7FC;color:#1A1330;margin:0;padding:40px 24px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:24px;padding:36px;box-shadow:0 8px 30px rgba(0,0,0,0.06);">
    <div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:12px;">SA Coparents</div>
    <h1 style="font-size:24px;font-weight:800;color:#1A1330;letter-spacing:-0.02em;margin:0 0 16px 0;">{headline}</h1>
    {body_html}
    {cta}
    {fallback}
    <hr style="border:none;border-top:1px solid #E5E0EE;margin:28px 0;"/>
    <p style="font-size:12px;color:#857E9C;line-height:1.55;margin:0;">SA Coparents · <a href="https://sacoparentsapp.online" style="color:#3D1A78;text-decoration:none;">sacoparentsapp.online</a></p>
  </div>
</body></html>"""


def _cover_note(
    user_name: str,
    user_email: str,
    mediator_name: Optional[str],
    doc_labels: List[str],
) -> Tuple[str, str]:
    """Build plain + html cover note for the mediator email."""
    greeting = f"Hi {mediator_name}," if mediator_name else "Hi,"
    bullet_lines = "".join([f"<li>{d}</li>" for d in doc_labels])
    plain = (
        f"{greeting}\n\n"
        f"I've prepared the attached documents for our mediation. "
        f"Please review them before our session.\n\n"
        f"Attached:\n" + "\n".join([f"- {d}" for d in doc_labels]) + "\n\n"
        f"You can reply directly to this email if you have any questions.\n\n"
        f"Thanks,\n{user_name}\n{user_email}\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"{greeting} I've prepared the attached documents for our mediation. "
        f"Please review them before our session.</p>"
        f'<ul style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;padding-left:20px;">'
        f"{bullet_lines}</ul>"
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"You can reply directly to this email if you have any questions.</p>"
        f'<p style="font-size:15px;line-height:1.55;color:#1A1330;margin:0;">'
        f"Thanks,<br/><strong>{user_name}</strong><br/>"
        f'<a href="mailto:{user_email}" style="color:#3D1A78;text-decoration:none;">{user_email}</a></p>'
    )
    html = _branded_html(headline="Mediation prep documents", body_html=body_html, cta_label="")
    return plain, html


# ============ Public API ============
def send_magic_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send a one-tap sign-in link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Tap the link below to sign in to SA Coparents. It expires in 15 minutes "
        "and can only be used once.\n\n"
        f"{link_url}\n\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "— SA Coparents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Use the button below to sign in. The link expires in "
        f"<strong>15 minutes</strong> and can only be used once.</p>"
    )
    html = _branded_html(
        headline="Tap to sign in",
        body_html=body_html,
        cta_label="Sign in to SA Coparents",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="Your SA Coparents sign-in link",
        html=html,
        text=plain,
        failure_message="Could not send your sign-in link right now. Please try again in a moment.",
    )


def send_setup_link(*, to_email: str, link_url: str) -> None:
    """Send a one-tap 'create your account' link."""
    plain = (
        "Welcome to SA Coparents.\n\n"
        "Someone (probably you) requested an account for this email. "
        "Tap the link below to set up your account. It expires in 15 minutes.\n\n"
        f"{link_url}\n\n"
        "If this wasn't you, you can safely ignore this email — no account was created.\n\n"
        "— SA Coparents · sacoparentsapp.online\n"
    )
    body_html = (
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        "Welcome. Tap the button below to finish creating your SA Coparents account. "
        "The link expires in <strong>15 minutes</strong>.</p>"
    )
    html = _branded_html(
        headline="Set up your account",
        body_html=body_html,
        cta_label="Set up my account",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="Set up your SA Coparents account",
        html=html,
        text=plain,
        failure_message="Couldn't send the setup link right now. Please try again.",
    )


def send_password_reset_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send a password-reset link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Someone (probably you) asked to reset the password on your SA Coparents account. "
        "Tap the link below to choose a new password. It expires in 15 minutes "
        "and can only be used once.\n\n"
        f"{link_url}\n\n"
        "If you didn't request this, you can safely ignore this email — your password hasn't changed.\n\n"
        "— SA Coparents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Tap the button below to choose a new password. The link expires in "
        f"<strong>15 minutes</strong> and can only be used once.</p>"
    )
    html = _branded_html(
        headline="Reset your password",
        body_html=body_html,
        cta_label="Reset my password",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="Reset your SA Coparents password",
        html=html,
        text=plain,
        failure_message="Could not send your reset link right now. Please try again in a moment.",
    )


def send_verification_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send an email-address verification link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Please confirm this is your email address so we can keep your SA Coparents "
        "account secure and send you important updates. Tap the link below — "
        "it expires in 24 hours.\n\n"
        f"{link_url}\n\n"
        "If you didn't create an account, you can safely ignore this email.\n\n"
        "— SA Coparents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Please confirm your email address so we can keep your account "
        f"secure. The link expires in <strong>24 hours</strong>.</p>"
    )
    html = _branded_html(
        headline="Confirm your email",
        body_html=body_html,
        cta_label="Confirm my email",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="Confirm your SA Coparents email",
        html=html,
        text=plain,
        failure_message="Could not send your verification link right now. Please try again in a moment.",
    )


def send_mediator_email(
    *,
    to_email: str,
    mediator_name: Optional[str],
    user_name: str,
    user_email: str,
    attachments: List[Tuple[str, bytes]],
    doc_labels: List[str],
) -> None:
    """Send PDFs to a mediator. attachments is a list of (filename, pdf_bytes)."""
    if not attachments:
        raise EmailSendError("No documents selected to send.")
    plain, html = _cover_note(user_name, user_email, mediator_name, doc_labels)
    subject = f"Mediation prep from {user_name or user_email}"
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=user_email or None,
        attachments=attachments,
        failure_message="Could not send email right now. Please try again in a moment.",
    )
