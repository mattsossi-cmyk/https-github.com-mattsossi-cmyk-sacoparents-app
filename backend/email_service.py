"""Email service for SA CoParents — uses Resend (https://resend.com).

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
import html as _html
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

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
        "from_name": os.environ.get("RESEND_FROM_NAME", "SA CoParents").strip(),
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
    require_encrypted: bool = False,
) -> None:
    """Internal: send via Virtru (if enabled) then Resend as fallback.

    `require_encrypted=True` — refuse to submit through any non-Virtru
    provider. Used for HIPAA-scoped joint reports / agreements once
    the tenant is provisioned (`VIRTRU_FORCE_ENCRYPT_REQUIRED=true`).
    """
    # Late imports so a missing virtru_mailer module never breaks
    # the rest of the email service.
    try:
        from virtru_mailer import (  # noqa: WPS433 — deliberate late import
            VirtruNotConfigured,
            VirtruSendError,
            send_via_virtru,
            virtru_force_encrypt_required,
            virtru_is_ready,
        )
        _virtru_available = True
    except Exception:  # pragma: no cover - defensive
        _virtru_available = False
        virtru_is_ready = lambda: False  # noqa: E731
        virtru_force_encrypt_required = lambda: False  # noqa: E731

    # Fail-closed: HIPAA-scoped sends must NOT silently fall back to
    # the standard Resend provider if the operator has said Virtru is
    # mandatory. Better a visible failure than an unencrypted PHI email.
    if require_encrypted and virtru_force_encrypt_required() and not virtru_is_ready():
        raise EmailSendError(
            "Encrypted delivery is required but the secure gateway is not configured."
        )

    if _virtru_available and virtru_is_ready():
        try:
            send_via_virtru(
                to_email=to_email,
                subject=subject,
                html=html,
                text=text,
                reply_to=reply_to,
                attachments=attachments,
            )
            return
        except VirtruNotConfigured:
            # Fall through to Resend — provisioning is incomplete.
            logger.info("Virtru not configured; routing via Resend for %s", subject)
        except VirtruSendError:
            if require_encrypted and virtru_force_encrypt_required():
                # We already logged in send_via_virtru; surface a
                # friendly failure to the caller so we never re-route
                # PHI through a non-encrypted provider.
                raise EmailSendError(failure_message)
            logger.warning(
                "Virtru submission failed; falling back to Resend for %s", subject,
            )

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
    """Wrap content in the SA CoParents branded email shell."""
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
    <div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:12px;">SA CoParents</div>
    <h1 style="font-size:24px;font-weight:800;color:#1A1330;letter-spacing:-0.02em;margin:0 0 16px 0;">{headline}</h1>
    {body_html}
    {cta}
    {fallback}
    <hr style="border:none;border-top:1px solid #E5E0EE;margin:28px 0;"/>
    <p style="font-size:12px;color:#857E9C;line-height:1.55;margin:0;">SA CoParents · <a href="https://sacoparentsapp.online" style="color:#3D1A78;text-decoration:none;">sacoparentsapp.online</a></p>
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
def send_silent_reviewer_nudge(
    *,
    to_email: str,
    parent_name: str,
    recipient_display: str,
    artefact_label: str,
    share_page_url: str,
    days_since_sent: int,
) -> None:
    """Nudge the SENDING PARENT (not the reviewer) when a share they
    emailed hasn't been opened after N days.

    Deliberately nudges the parent — never the reviewer — because the
    parent chose the share, holds the audit relationship, and can
    decide whether to re-send. Auto-emailing the professional risks
    feeling like spam.
    """
    plain = (
        f"Hi {parent_name or 'there'},\n\n"
        f"Quick heads-up: {days_since_sent} days ago you emailed the "
        f"{artefact_label} to {recipient_display}, and it hasn't been "
        f"opened yet.\n\n"
        "That could mean anything — a busy inbox, an unread folder, "
        "or a link they just haven't gotten to. If it would help, you "
        "can re-send it in one tap from your dashboard:\n\n"
        f"{share_page_url}\n\n"
        "You can also revoke the link from that page if you'd rather "
        "share a fresh copy manually.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'Hi {_html.escape(parent_name or "there")},'
        f'</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'Quick heads-up: <strong>{days_since_sent} days ago</strong> '
        f'you emailed the <strong>{_html.escape(artefact_label)}</strong> '
        f'to <strong>{_html.escape(recipient_display)}</strong>, and it '
        f"hasn't been opened yet."
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:14px;padding:14px 16px;'
        f'margin:0 0 16px 0;border:1px solid #E5E0EE;color:#1A1330;'
        f'font-size:14px;line-height:1.55;">'
        f'That could mean anything &mdash; a busy inbox, an unread '
        f"folder, or a link they just haven't gotten to. If it would "
        f'help, you can re-send it in one tap from your dashboard.'
        f'</div>'
        f'<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        f'You can also revoke the link from your dashboard if you\u2019d '
        f'rather share a fresh copy manually.'
        f'</p>'
    )
    html = _branded_html(
        headline=f"Your {artefact_label} hasn\u2019t been opened yet",
        body_html=body_html,
        cta_label="Open your dashboard",
        cta_url=share_page_url,
    )
    _send(
        to_email=to_email,
        subject=f"{recipient_display} hasn\u2019t opened your {artefact_label} yet",
        html=html,
        text=plain,
        failure_message="Could not send the follow-up nudge right now.",
    )


def send_magic_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send a one-tap sign-in link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Tap the link below to sign in to SA CoParents. It expires in 15 minutes "
        "and can only be used once.\n\n"
        f"{link_url}\n\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Use the button below to sign in. The link expires in "
        f"<strong>15 minutes</strong> and can only be used once.</p>"
    )
    html = _branded_html(
        headline="Tap to sign in",
        body_html=body_html,
        cta_label="Sign in to SA CoParents",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="Your SA CoParents sign-in link",
        html=html,
        text=plain,
        failure_message="Could not send your sign-in link right now. Please try again in a moment.",
    )


def send_setup_link(*, to_email: str, link_url: str) -> None:
    """Send a one-tap 'create your account' link."""
    plain = (
        "Welcome to SA CoParents.\n\n"
        "Someone (probably you) requested an account for this email. "
        "Tap the link below to set up your account. It expires in 15 minutes.\n\n"
        f"{link_url}\n\n"
        "If this wasn't you, you can safely ignore this email — no account was created.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        "Welcome. Tap the button below to finish creating your SA CoParents account. "
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
        subject="Set up your SA CoParents account",
        html=html,
        text=plain,
        failure_message="Couldn't send the setup link right now. Please try again.",
    )


def send_password_reset_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send a password-reset link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Someone (probably you) asked to reset the password on your SA CoParents account. "
        "Tap the link below to choose a new password. It expires in 15 minutes "
        "and can only be used once.\n\n"
        f"{link_url}\n\n"
        "If you didn't request this, you can safely ignore this email — your password hasn't changed.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
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
        subject="Reset your SA CoParents password",
        html=html,
        text=plain,
        failure_message="Could not send your reset link right now. Please try again in a moment.",
    )


def send_verification_link(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Send an email-address verification link."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Please confirm this is your email address so we can keep your SA CoParents "
        "account secure and send you important updates. Tap the link below — "
        "it expires in 24 hours.\n\n"
        f"{link_url}\n\n"
        "If you didn't create an account, you can safely ignore this email.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
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
        subject="Confirm your SA CoParents email",
        html=html,
        text=plain,
        failure_message="Could not send your verification link right now. Please try again in a moment.",
    )


def send_verification_code(
    *,
    to_email: str,
    code: str,
    user_name: Optional[str] = None,
) -> None:
    """Send a 6-digit email verification code (in-app entry, no link)."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Enter this 6-digit code in the app to confirm your email address:\n\n"
        f"    {code}\n\n"
        "It expires in 15 minutes. If you didn't request this, you can safely "
        "ignore this email.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Enter this 6-digit code in the app to confirm your email address. "
        f"It expires in <strong>15 minutes</strong>.</p>"
        f'<div style="text-align:center;margin:24px 0 32px;">'
        f'<div style="display:inline-block;font-family:-apple-system,SFMono-Regular,Menlo,monospace;'
        f'letter-spacing:0.6em;font-size:34px;font-weight:800;color:#1A1330;background:#F1EEF7;'
        f'border:1px solid #E5E0EE;border-radius:16px;padding:18px 30px 18px 36px;">{_html.escape(code)}</div></div>'
        f'<p style="font-size:12px;color:#857E9C;margin:0;">Didn\'t request this? You can safely ignore this email.</p>'
    )
    html = _branded_html(
        headline="Confirm your email",
        body_html=body_html,
        cta_label="",
    )
    _send(
        to_email=to_email,
        subject=f"Your SA CoParents code: {code}",
        html=html,
        text=plain,
        failure_message="Could not send your verification code right now. Please try again in a moment.",
    )


def send_password_reset_code(
    *,
    to_email: str,
    code: str,
    user_name: Optional[str] = None,
) -> None:
    """Send a 6-digit password-reset code (in-app entry, no link)."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Someone (probably you) asked to reset the password on your SA CoParents "
        "account. Enter this 6-digit code in the app to choose a new password:\n\n"
        f"    {code}\n\n"
        "It expires in 15 minutes and can only be used once. If you didn't request "
        "this, you can safely ignore this email — your password hasn't changed.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        f"{greeting} Enter this 6-digit code in the app to choose a new password. "
        f"It expires in <strong>15 minutes</strong> and can only be used once.</p>"
        f'<div style="text-align:center;margin:24px 0 32px;">'
        f'<div style="display:inline-block;font-family:-apple-system,SFMono-Regular,Menlo,monospace;'
        f'letter-spacing:0.6em;font-size:34px;font-weight:800;color:#1A1330;background:#F1EEF7;'
        f'border:1px solid #E5E0EE;border-radius:16px;padding:18px 30px 18px 36px;">{_html.escape(code)}</div></div>'
        f'<p style="font-size:12px;color:#857E9C;margin:0;">Didn\'t request this? You can safely ignore this email — your password hasn\'t changed.</p>'
    )
    html = _branded_html(
        headline="Reset your password",
        body_html=body_html,
        cta_label="",
    )
    _send(
        to_email=to_email,
        subject=f"SA CoParents reset code: {code}",
        html=html,
        text=plain,
        failure_message="Could not send your reset code right now. Please try again in a moment.",
    )


def send_post_summary_checkin(
    *,
    to_email: str,
    user_name: Optional[str] = None,
    recap_text: Optional[str] = None,
    journal_url: str = "",
) -> None:
    """Two-week post-summary check-in. Embeds the user's AI-generated weekly
    journal recap if they have one; otherwise sends a simpler check-in note."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    cta_url = journal_url or "https://sacoparentsapp.online/journal"

    if recap_text:
        plain = (
            f"{greeting}\n\n"
            "It's been two weeks since you put your Mediation Prep Summary together. "
            "We just wanted to check in.\n\n"
            "Here's a short recap of your journal from the past week:\n\n"
            f"{recap_text}\n\n"
            f"Pick up where you left off:\n{cta_url}\n\n"
            "— SA CoParenting App · sacoparentsapp.online\n"
        )
        body_html = (
            f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
            f"{greeting} It's been two weeks since you put your Mediation Prep "
            f"Summary together. We wanted to check in.</p>"
            '<div style="background:#F8F7FC;border-left:3px solid #3D1A78;'
            'padding:14px 18px;border-radius:6px;margin:0 0 22px 0;">'
            '<div style="font-size:10px;letter-spacing:.18em;text-transform:uppercase;'
            'color:#3D1A78;font-weight:700;margin-bottom:6px;">Your week in review</div>'
            f'<div style="font-size:14px;line-height:1.6;color:#1A1330;white-space:pre-wrap;">'
            f"{recap_text}</div></div>"
        )
        subject = "Two weeks on — your check-in from SA CoParenting App"
    else:
        plain = (
            f"{greeting}\n\n"
            "It's been two weeks since you put together your Mediation Prep Summary. "
            "We just wanted to check in.\n\n"
            "How are things going? A few quiet minutes in the journal — even one short "
            "entry — can help you stay grounded and focused on what matters most.\n\n"
            f"Open your journal:\n{cta_url}\n\n"
            "— SA CoParenting App · sacoparentsapp.online\n"
        )
        body_html = (
            f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
            f"{greeting} It's been two weeks since you put together your Mediation "
            f"Prep Summary. We wanted to check in.</p>"
            '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 22px 0;">'
            "How are things going? A few quiet minutes in the journal — even one short "
            "entry — can help you stay grounded and focused on what matters most.</p>"
        )
        subject = "Two weeks on — your check-in from SA CoParenting App"

    html = _branded_html(
        headline="Just checking in",
        body_html=body_html,
        cta_label="Open my journal",
        cta_url=cta_url,
    )
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        failure_message="Could not send the check-in email right now.",
    )


def send_admin_weekly_briefing(
    *,
    to_email: str,
    week_iso: str,
    briefing: dict,
    signals: dict,
    view_url: str = "",
) -> None:
    """Monday 8 AM admin email — wraps the AI-generated weekly briefing in
    branded HTML."""

    def _ul(items):
        items = [i for i in (items or []) if i]
        if not items:
            return ""
        lis = "".join(
            f'<li style="margin:0 0 8px 0;color:#1A1330;font-size:14px;line-height:1.55;">{i}</li>'
            for i in items
        )
        return f'<ul style="margin:0 0 18px 18px;padding:0;list-style:disc;">{lis}</ul>'

    counts = (signals or {}).get("counts") or {}
    avg_nps = ((signals or {}).get("nps") or {}).get("avg")
    nps_line = f"Avg NPS {avg_nps}/10" if avg_nps is not None else "No NPS yet"
    sign_ups = (counts.get("new_users") or 0) + (counts.get("new_guests") or 0)
    counts_strip = (
        '<table role="presentation" cellspacing="0" cellpadding="0" border="0" '
        'style="width:100%;margin:0 0 22px 0;border-collapse:collapse;">'
        '<tr>'
        f'<td style="width:25%;background:#F8F7FC;padding:14px 12px;border-radius:8px;text-align:center;">'
        f'<div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#857E9C;font-weight:700;">Signups</div>'
        f'<div style="font-size:22px;color:#1A1330;margin-top:4px;font-family:Georgia,serif;">{sign_ups}</div>'
        '</td>'
        '<td style="width:8px;"></td>'
        f'<td style="width:25%;background:#F8F7FC;padding:14px 12px;border-radius:8px;text-align:center;">'
        f'<div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#857E9C;font-weight:700;">Summaries</div>'
        f'<div style="font-size:22px;color:#1A1330;margin-top:4px;font-family:Georgia,serif;">{counts.get("summaries_generated", 0)}</div>'
        '</td>'
        '<td style="width:8px;"></td>'
        f'<td style="width:25%;background:#F8F7FC;padding:14px 12px;border-radius:8px;text-align:center;">'
        f'<div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#857E9C;font-weight:700;">Surveys</div>'
        f'<div style="font-size:22px;color:#1A1330;margin-top:4px;font-family:Georgia,serif;">{counts.get("survey_responses", 0)}</div>'
        f'<div style="font-size:10px;color:#857E9C;margin-top:2px;">{nps_line}</div>'
        '</td>'
        '<td style="width:8px;"></td>'
        f'<td style="width:25%;background:#F8F7FC;padding:14px 12px;border-radius:8px;text-align:center;">'
        f'<div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#857E9C;font-weight:700;">Invites</div>'
        f'<div style="font-size:22px;color:#1A1330;margin-top:4px;font-family:Georgia,serif;">{counts.get("invites_sent", 0)}</div>'
        f'<div style="font-size:10px;color:#857E9C;margin-top:2px;">{counts.get("invites_accepted", 0)} accepted</div>'
        '</td>'
        '</tr></table>'
    )

    concerning = briefing.get("concerning_patterns") or []
    concerning_block = ""
    if concerning:
        lis = "".join(
            f'<li style="margin:0 0 6px 0;color:#9A3A23;font-size:14px;line-height:1.5;">{i}</li>'
            for i in concerning
        )
        concerning_block = (
            '<div style="background:#FCE3DC;border-left:4px solid #9A3A23;'
            'padding:14px 18px;border-radius:6px;margin:0 0 22px 0;">'
            '<div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#9A3A23;'
            'font-weight:700;margin-bottom:6px;">Worth a closer look</div>'
            f'<ul style="margin:6px 0 0 18px;padding:0;list-style:disc;">{lis}</ul>'
            '</div>'
        )

    headline = briefing.get("headline") or "Quiet week — too little data to call."
    _empty_msg = (
        '<p style="font-size:13px;color:#857E9C;margin:0 0 18px 0;">Nothing this week.</p>'
    )
    _empty_actions = (
        '<p style="font-size:13px;color:#857E9C;margin:0 0 18px 0;">No suggestions this week.</p>'
    )
    body_html = (
        f'<p style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin:0 0 4px 0;">Weekly insights · {week_iso}</p>'
        f'<p style="font-family:Georgia,serif;font-size:20px;line-height:1.4;color:#1A1330;margin:0 0 22px 0;">{headline}</p>'
        f"{counts_strip}"
        f"{concerning_block}"
        '<p style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin:0 0 6px 0;">Highlights</p>'
        f"{_ul(briefing.get('highlights')) or _empty_msg}"
        '<p style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin:0 0 6px 0;">User voice themes</p>'
        f"{_ul(briefing.get('user_voice_themes')) or _empty_msg}"
        '<p style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin:0 0 6px 0;">Recommended actions</p>'
        f"{_ul(briefing.get('recommended_actions')) or _empty_actions}"
    )

    if briefing.get("closing_note"):
        body_html += (
            f'<p style="font-family:Georgia,serif;font-style:italic;font-size:14px;color:#4B4567;'
            f'border-top:1px solid #E5E0EE;padding-top:14px;margin:18px 0 0 0;">'
            f'&ldquo;{briefing["closing_note"]}&rdquo;</p>'
        )

    plain_lines = [
        f"Weekly insights · {week_iso}",
        "",
        headline,
        "",
        f"Signups: {sign_ups} | Summaries: {counts.get('summaries_generated', 0)} | "
        f"Survey responses: {counts.get('survey_responses', 0)} ({nps_line}) | "
        f"Invites: {counts.get('invites_sent', 0)} ({counts.get('invites_accepted', 0)} accepted)",
    ]
    if concerning:
        plain_lines += ["", "Worth a closer look:"]
        plain_lines += [f"  • {i}" for i in concerning]
    for label, key in (
        ("Highlights", "highlights"),
        ("User voice themes", "user_voice_themes"),
        ("Recommended actions", "recommended_actions"),
    ):
        items = briefing.get(key) or []
        if items:
            plain_lines += ["", f"{label}:"] + [f"  • {i}" for i in items]
    if briefing.get("closing_note"):
        plain_lines += ["", briefing["closing_note"]]
    plain_lines += ["", f"Open the dashboard: {view_url or 'https://sacoparentsapp.online/admin/insights'}"]

    html = _branded_html(
        headline="Your 5-minute Monday read",
        body_html=body_html,
        cta_label="Open the full dashboard",
        cta_url=view_url or "https://sacoparentsapp.online/admin/insights",
    )
    _send(
        to_email=to_email,
        subject=f"SA CoParents — weekly insights ({week_iso})",
        html=html,
        text="\n".join(plain_lines),
        failure_message="Could not send the weekly admin briefing email.",
    )


def send_compare_invite(
    *,
    to_email: str,
    link_url: str,
    inviter_name: Optional[str] = None,
    product_label: str = "Deep Dive",
    aligned_pct: Optional[int] = None,
    previous_aligned_pct: Optional[int] = None,
) -> None:
    """Notify a co-parent that a compare request is awaiting their consent.

    Sent once when the first parent hits POST /compare/link so the invited
    co-parent knows to log in and consent (or decline). Never contains any
    private assessment content — only a call to log in.

    If ``aligned_pct`` is provided (both parents already completed their
    assessments at invite time), the email gets a neutral one-line teaser
    of the current alignment percentage so the recipient sees the value
    before they click through. The number is a summary only — no items or
    prompts leak before consent.

    If ``previous_aligned_pct`` is also provided (the user pair has at
    least one earlier compare snapshot for this pathway), a small trend
    line — "↑ +7% since your last check-in" — is rendered next to the
    current percentage so co-parents see progress at a glance.
    """
    inviter = (inviter_name or "Your co-parent").strip() or "Your co-parent"
    # Clamp to a safe integer range in case an upstream caller ever hands us
    # a float or an out-of-bounds value.
    def _clamp(v):
        if isinstance(v, (int, float)):
            return max(0, min(100, int(v)))
        return None
    preview = _clamp(aligned_pct)
    previous = _clamp(previous_aligned_pct)
    delta = None if (preview is None or previous is None) else preview - previous
    # Trend copy pieces
    trend_plain = ""
    trend_html = ""
    if delta is not None:
        if delta > 0:
            arrow = "↑"
            trend_word = f"up {delta} points since your last check-in"
            trend_color = "#1F5C3B"
        elif delta < 0:
            arrow = "↓"
            trend_word = f"down {abs(delta)} points since your last check-in"
            trend_color = "#8C3A3A"
        else:
            arrow = "→"
            trend_word = "no change since your last check-in"
            trend_color = "#4B4567"
        trend_plain = f" {arrow} {trend_word} (was {previous}%)."
        trend_html = (
            f'<div style="font-size:12px;color:{trend_color};margin:8px 0 0 0;'
            f'font-weight:600;">{arrow} {trend_word} '
            f'<span style="color:#857E9C;font-weight:400;">(was {previous}%)</span>'
            f'</div>'
        )
    preview_plain = ""
    preview_html = ""
    if preview is not None:
        preview_plain = (
            f"\nBefore you decide: based on both of your answers so far, you "
            f"already agree on about {preview}% of them.{trend_plain}\n"
        )
        preview_html = (
            '<div style="margin:0 0 18px 0;padding:14px 16px;border-radius:14px;'
            'border:1px solid #B5DFC5;background:#F1F9F4;">'
            '<div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;'
            'color:#1F5C3B;font-weight:700;margin:0 0 4px 0;">A quick preview</div>'
            f'<div style="font-size:22px;line-height:1.2;color:#1A1330;font-weight:800;'
            f'font-family:Georgia,\'Times New Roman\',serif;">You already agree on '
            f'about {preview}% of your answers.</div>'
            f'{trend_html}'
            '<div style="font-size:12px;color:#4B4567;margin:6px 0 0 0;">'
            "This is a summary only — no items are shared until you consent."
            '</div></div>'
        )
    plain = (
        f"{inviter} would like to compare {product_label} answers with you on "
        "SA CoParenting App.\n"
        f"{preview_plain}"
        "\nNothing is shared automatically. Log in and, if you consent, both parents' "
        "answers will appear neutrally side-by-side — never labelling either of you "
        "'right' or 'wrong'.\n\n"
        f"Review the request here:\n{link_url}\n\n"
        "If you'd rather not, ignore this email and no comparison will ever be created.\n\n"
        "— SA CoParenting App · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"<strong>{inviter}</strong> would like to compare {product_label} answers with "
        f"you on SA CoParenting App.</p>"
        f"{preview_html}"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        "Nothing is shared automatically. Log in and, if you consent, both parents' "
        "answers will appear neutrally side-by-side — never labelling either of you "
        "<em>right</em> or <em>wrong</em>.</p>"
        '<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 22px 0;">'
        "If you'd rather not, ignore this email — no comparison will ever be created.</p>"
    )
    html = _branded_html(
        headline=f"{inviter} invited you to compare notes",
        body_html=body_html,
        cta_label="Review the request",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject=f"{inviter} invited you to compare {product_label} answers on SA CoParenting App",
        html=html,
        text=plain,
        failure_message="Could not send the compare-request email right now.",
    )


def send_compare_invite_nudge(
    *,
    to_email: str,
    creator_name: str,
    partner_name: str,
    partner_email: str,
    kind_label: str,
    created_at_iso: str,
) -> None:
    """Nudge the CREATOR of a Compare Share request whose partner has
    not consented within 7 days. Warm, no-blame framing — parents in
    conflict are already fragile and a dunning-toned reminder would be
    counterproductive. Sends once per share_id per dedupe window.
    """
    who = (creator_name or "").strip()
    partner_who = (partner_name or "").strip() or (partner_email or "your co-parent")
    when_days = ""
    try:
        if created_at_iso:
            from datetime import datetime, timezone
            d = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - d).days
            if days > 0:
                when_days = f" (sent about {days} day{'s' if days != 1 else ''} ago)"
    except Exception:  # noqa: BLE001
        when_days = ""

    greeting = f"Hi {who}," if who else "Hi,"
    escaped_partner = _html.escape(partner_who)
    escaped_kind = _html.escape(kind_label)
    escaped_when = _html.escape(when_days)
    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'A quick friendly note — your <strong>{escaped_kind}</strong> Compare '
        f'Share request to <strong>{escaped_partner}</strong> is still waiting on their '
        f'consent{escaped_when}. That&rsquo;s normal — sometimes life just gets in the way.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:14px;padding:14px 16px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:6px;">'
        f'A few options</div>'
        f'<ul style="margin:0;padding-left:18px;color:#1A1330;font-size:14px;line-height:1.55;">'
        f'<li>Message {escaped_partner} outside the app to let them know you\u2019ve sent something to their inbox.</li>'
        f'<li>Log in and view the Compare Hub — you can send the invite again or cancel it if you\u2019ve changed your mind.</li>'
        f'<li>Do nothing. The request will remain pending until either of you acts on it.</li>'
        f'</ul>'
        f'</div>'
        f'<p style="font-size:13px;line-height:1.6;color:#857E9C;margin:0 0 12px 0;font-style:italic;">'
        f'No pressure. SA CoParents will only send this reminder once every '
        f'seven days per pending request.'
        f'</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"A quick friendly note — your {kind_label} Compare Share request to "
        f"{partner_who} is still waiting on their consent{when_days}. "
        f"That's normal, life gets in the way.\n\n"
        f"A few options:\n"
        f"  • Message {partner_who} outside the app to let them know you've sent something.\n"
        f"  • Log in and view the Compare Hub — you can resend or cancel.\n"
        f"  • Do nothing. The request stays pending until either of you acts.\n\n"
        f"No pressure. SA CoParents only sends this reminder once every seven days "
        f"per pending request.\n"
    )
    html = _branded_html(
        headline=f"Your {kind_label} request is still pending",
        body_html=body_html,
        cta_label="Open Compare Hub",
        cta_url=(os.environ.get("PUBLIC_APP_URL") or "").rstrip("/") + "/compare",
    )
    _send(
        to_email=to_email,
        subject=f"Your {kind_label} Compare Share is still pending",
        html=html,
        text=plain,
        failure_message="Could not send the invite nudge right now.",
    )





def send_coparent_invite(*, to_email: str, link_url: str, inviter_name: Optional[str] = None) -> None:
    """Invite a co-parent to prep for mediation in their own private account."""
    inviter = (inviter_name or "Your co-parent").strip() or "Your co-parent"
    plain = (
        f"{inviter} has invited you to prep for mediation using SA CoParenting App.\n\n"
        "It's a guided, child-centered workspace that helps both parents arrive at "
        "mediation prepared, calm, and focused on what matters most: your child.\n\n"
        "Your prep is completely private — your co-parent never sees your answers.\n\n"
        f"Get started here:\n{link_url}\n\n"
        "This link expires in 30 days.\n\n"
        "— SA CoParenting App · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"<strong>{inviter}</strong> has invited you to prep for mediation using "
        f"SA CoParenting App.</p>"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        "It's a guided, child-centered workspace that helps both parents arrive at "
        "mediation prepared, calm, and focused on what matters most.</p>"
        '<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 22px 0;">'
        "Your prep is completely <strong>private</strong> — your co-parent never "
        "sees your answers. This link expires in 30 days.</p>"
    )
    html = _branded_html(
        headline=f"{inviter} invited you to prep together",
        body_html=body_html,
        cta_label="Start my private prep",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject=f"{inviter} invited you to prep for mediation on SA CoParenting App",
        html=html,
        text=plain,
        failure_message="Could not send the co-parent invitation right now.",
    )


def send_post_event_survey(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Initial post-event ("How was mediation?") survey email — sent 7 days
    after a user generates their Mediation Summary."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Now that you've had a chance to use SA CoParenting App, we'd love to hear how it went.\n\n"
        "Your feedback helps us improve the app for other parents — and if you've shared it "
        "with a mediator, therapist, or attorney, your perspective is incredibly valuable.\n\n"
        "The survey takes about 3 minutes:\n\n"
        f"{link_url}\n\n"
        "Thank you for taking the time to help us build something better for families.\n\n"
        "— SA CoParenting App · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"{greeting} Now that you've had a chance to use SA CoParenting App, we'd "
        f"love to hear how it went.</p>"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 24px 0;">'
        "Your answers help us improve the app for other parents. It takes about "
        "<strong>3 minutes</strong>.</p>"
    )
    html = _branded_html(
        headline="How did it go?",
        body_html=body_html,
        cta_label="Take the 3-minute survey",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="How did SA CoParenting App work for you?",
        html=html,
        text=plain,
        failure_message="Could not send the survey invitation right now.",
    )


def send_post_event_survey_reminder(*, to_email: str, link_url: str, user_name: Optional[str] = None) -> None:
    """Single reminder if the parent didn't respond to the first email."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Just a gentle follow-up — when you have a spare 3 minutes, we'd really value "
        "your honest feedback on SA CoParenting App.\n\n"
        f"{link_url}\n\n"
        "If you'd rather not respond, no worries — this is the last reminder you'll get.\n\n"
        "— SA CoParenting App · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"{greeting} A gentle follow-up — when you have 3 minutes, we'd really value "
        f"your honest feedback.</p>"
        '<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 24px 0;">'
        "This is the last reminder you'll get about this survey.</p>"
    )
    html = _branded_html(
        headline="One quick favour",
        body_html=body_html,
        cta_label="Share your feedback",
        cta_url=link_url,
    )
    _send(
        to_email=to_email,
        subject="A quick favour — how did SA CoParenting App work for you?",
        html=html,
        text=plain,
        failure_message="Could not send the survey reminder right now.",
    )


def send_snc_coparent_invite(
    *,
    to_email: str,
    inviter_name: Optional[str],
    accept_url: str,
) -> None:
    """Invite a co-parent to complete their own Special Needs Co-Parenting
    assessment. Their answers stay private — the only shared output is a
    neutral side-by-side once both parents finish."""
    inviter = (inviter_name or "Your co-parent").strip() or "Your co-parent"
    plain = (
        f"{inviter} has invited you to complete the SA CoParents "
        f"Special Needs Co-Parenting Assessment.\n\n"
        "You'll each answer the same 13-section questionnaire in your own "
        "private account. Your answers are never shown to the other parent — "
        "the only shared output is a neutral, side-by-side comparison once "
        "both of you complete it.\n\n"
        f"Get started here:\n{accept_url}\n\n"
        "This link expires in 60 days.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"<strong>{inviter}</strong> has invited you to complete the SA CoParents "
        f"<strong>Special Needs Co-Parenting Assessment</strong>.</p>"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        "You'll each answer the same 13-section questionnaire in your own "
        "<em>private</em> account. Your answers are never shown to the other "
        "parent — the only shared output is a neutral, side-by-side comparison "
        "once both of you complete it.</p>"
        '<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 22px 0;">'
        "Safety responses are always kept out of the shared comparison. "
        "This link expires in 60 days.</p>"
    )
    html = _branded_html(
        headline=f"{inviter} invited you to a side-by-side",
        body_html=body_html,
        cta_label="Start my private assessment",
        cta_url=accept_url,
    )
    _send(
        to_email=to_email,
        subject=f"{inviter} invited you to the Special Needs Co-Parenting Assessment",
        html=html,
        text=plain,
        failure_message="Could not send the SNC invitation right now.",
    )


def send_snc_report_ready(
    *,
    to_email: str,
    user_name: Optional[str],
    child_first_name: Optional[str],
    priority_concerns: List[str],
    open_report_url: str,
    pdf_bytes: bytes,
) -> None:
    """Notify the parent that their Special Needs Co-Parenting report is ready.

    Attaches the individual-parent PDF and includes a short recap of their
    highest-priority items. The email is sent from a single 'ready' notification —
    it is not sent again on regenerate, so we don't spam the parent every time
    they edit an answer.
    """
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    child_line = (
        f"Your report for {child_first_name} is ready to review and share."
        if child_first_name
        else "Your report is ready to review and share."
    )

    concerns = [c for c in (priority_concerns or []) if c]
    concerns_html = ""
    concerns_plain = ""
    if concerns:
        items_html = "".join(
            f'<li style="margin:0 0 6px 0;color:#1A1330;font-size:14px;line-height:1.55;">{c}</li>'
            for c in concerns[:5]
        )
        concerns_html = (
            '<div style="background:#F8F7FC;border-left:3px solid #3D1A78;'
            'padding:14px 18px;border-radius:6px;margin:0 0 22px 0;">'
            '<div style="font-size:10px;letter-spacing:.18em;text-transform:uppercase;'
            'color:#3D1A78;font-weight:700;margin-bottom:6px;">Your priority items</div>'
            f'<ul style="margin:6px 0 0 18px;padding:0;list-style:disc;">{items_html}</ul>'
            "</div>"
        )
        concerns_plain = "\nYour priority items:\n" + "\n".join(
            f"  • {c}" for c in concerns[:5]
        ) + "\n"

    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">{greeting}</p>'
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"{child_line} The individual parent report attached to this email is built "
        f"only from your answers — it does not compare you to the other parent, does "
        f"not diagnose your child, and does not determine parental fitness.</p>"
        f"{concerns_html}"
        '<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        "You can share the attached PDF with a mediator, teacher, treating "
        "professional, or your co-parent — you decide who sees it.</p>"
        '<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        "Your Family Violence &amp; Communication Safety answers, if any, are kept "
        "out of the shared/scored parts of this document.</p>"
    )
    plain = (
        f"{greeting}\n\n"
        f"{child_line}\n\n"
        "The attached PDF is your individual parent report. It's built only from "
        "your answers — it doesn't compare you to the other parent, doesn't diagnose "
        "your child, and doesn't determine parental fitness.\n"
        f"{concerns_plain}\n"
        f"Open your report online:\n{open_report_url}\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    html = _branded_html(
        headline="Your Special Needs Co-Parenting report is ready",
        body_html=body_html,
        cta_label="Open my report",
        cta_url=open_report_url,
    )
    _send(
        to_email=to_email,
        subject="Your Special Needs Co-Parenting report is ready",
        html=html,
        text=plain,
        attachments=[("Special_Needs_Co-Parenting_Report.pdf", pdf_bytes)],
        failure_message="Couldn't email your Special Needs report right now.",
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


def send_safety_assessment_report(
    *,
    to_email: str,
    user_name: str,
    level: int,
    pathway_title: str,
    pathway_summary: str,
    pdf_bytes: bytes,
) -> None:
    """Email the IPV Communication Safety Screen report (with PDF attached)."""
    greeting = f"Hi {user_name}," if user_name and not user_name.lower().startswith("demo") else "Hi,"
    safety_line = (
        "Reminder: This assessment is not a diagnosis or legal advice. "
        "If you are in immediate danger, call 911. "
        "National Domestic Violence Hotline: 800-799-7233 (text START to 88788)."
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">{greeting}</p>'
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 16px 0;">'
        f"Here is the copy of your Family Violence and Communication Safety Screen you requested. "
        f"Your recommended pathway is:</p>"
        f'<div style="background:#F8F7FC;border-radius:16px;padding:18px 20px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:6px;">Level {level}</div>'
        f'<div style="font-size:18px;font-weight:800;color:#1A1330;margin-bottom:8px;">{pathway_title}</div>'
        f'<div style="font-size:14px;color:#4B4567;line-height:1.55;">{pathway_summary}</div>'
        f"</div>"
        f'<p style="font-size:14px;line-height:1.55;color:#4B4567;margin:0 0 12px 0;">'
        f"The full report with your answers and recommendations is attached as a PDF. "
        f"You can share it with an attorney, advocate, mediator, or trusted support person.</p>"
        f'<p style="font-size:13px;line-height:1.55;color:#9A3A23;margin:0 0 8px 0;background:#FCE3DC;border-radius:12px;padding:12px 14px;border:1px solid #9A3A23;border-opacity:0.2;">'
        f"{safety_line}</p>"
    )
    plain = (
        f"{greeting}\n\n"
        f"Your Family Violence and Communication Safety Screen result is attached.\n\n"
        f"Level {level}: {pathway_title}\n\n"
        f"{pathway_summary}\n\n"
        f"{safety_line}\n"
    )
    html = _branded_html(
        headline="Your Safety Screen report",
        body_html=body_html,
        cta_label="",
    )
    _send(
        to_email=to_email,
        subject="Your Family Violence and Communication Safety Screen - SA CoParents",
        html=html,
        text=plain,
        attachments=[("safety-assessment.pdf", pdf_bytes)],
        failure_message="Couldn't email your safety screen right now. Please try again in a moment.",
    )


def send_mediator_safety_assessment(
    *,
    to_email: str,
    mediator_name: str,
    parent_name: str,
    parent_email: str,
    parent_message: str,
    level: int,
    pathway_title: str,
    pathway_summary: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> None:
    """One-tap CTA: forward a parent's IPV Safety Screen pathway to their mediator."""
    greeting = f"Hi {mediator_name}," if mediator_name else "Hi,"
    who = parent_name or parent_email
    optional_note_html = (
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0 0 16px 0;'
        f'background:#F8F7FC;border-radius:14px;padding:14px 16px;border:1px solid #E5E0EE;">'
        f'<span style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;">'
        f'Note from {who}</span><br/>{parent_message}</p>'
        if parent_message
        else ""
    )
    optional_note_plain = f"\nNote from {who}:\n{parent_message}\n" if parent_message else ""

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">{greeting}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'<strong>{who}</strong> is preparing for mediation through SA CoParents and asked me to send you '
        f'their Family Violence and Communication Safety Screen result so you have the safest starting point for their case.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:16px;padding:18px 20px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:6px;">'
        f'Level {level} pathway</div>'
        f'<div style="font-size:18px;font-weight:800;color:#1A1330;margin-bottom:8px;">{pathway_title}</div>'
        f'<div style="font-size:14px;color:#4B4567;line-height:1.55;">{pathway_summary}</div>'
        f'</div>'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 12px 0;">'
        f'The full assessment with each answer and the recommended pathway is attached as a PDF. '
        f'You can reply directly to this email to reach {who}.</p>'
        f'<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        f'This assessment is a screening tool, not a diagnosis or legal advice. If there is immediate danger, '
        f'call 911. National Domestic Violence Hotline: 800-799-7233.</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"{who} is preparing for mediation through SA CoParents and asked me to forward "
        f"their Family Violence and Communication Safety Screen.\n\n"
        f"Level {level}: {pathway_title}\n{pathway_summary}\n"
        f"{optional_note_plain}"
        f"\nThe full report is attached as a PDF. You can reply directly to reach {who}"
        f" ({parent_email}).\n\n"
        f"This assessment is a screening tool, not a diagnosis or legal advice. "
        f"If there is immediate danger, call 911. National Domestic Violence Hotline: 800-799-7233.\n"
    )
    html = _branded_html(
        headline=f"Safety pathway from {who}",
        body_html=body_html,
        cta_label="",
    )
    subject = f"Mediation safety pathway from {who}"
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=parent_email or None,
        attachments=[(pdf_filename or "safety-assessment.pdf", pdf_bytes)],
        failure_message="Couldn't email your mediator right now. Please try again in a moment.",
    )


def send_four_dimension_briefing(
    *,
    to_email: str,
    recipient_name: str,
    recipient_role: str,
    parent_name: str,
    parent_email: str,
    parent_message: str,
    pdf_bytes: bytes,
    pdf_filename: str = "four-dimension-briefing.pdf",
) -> None:
    """Send the combined 4-Dimension Briefing (Safety + Companion) to a
    mediator, parent facilitator ad litem, or trial court. Reply-to is
    the parent's email so the recipient can respond directly."""
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    who = parent_name or parent_email or "This parent"
    role_line = f" ({recipient_role})" if recipient_role else ""
    escaped_role = _html.escape(recipient_role or "")
    optional_note_html = (
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0 0 16px 0;'
        f'background:#F8F7FC;border-radius:14px;padding:14px 16px;border:1px solid #E5E0EE;">'
        f'<span style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;">'
        f'Note from {_html.escape(who)}</span><br/>{_html.escape(parent_message)}</p>'
        if parent_message
        else ""
    )
    optional_note_plain = (
        f"\nNote from {who}:\n{parent_message}\n"
        if parent_message
        else ""
    )

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'<strong>{_html.escape(who)}</strong> is preparing for their next co-parenting '
        f'session through SA CoParents and asked me to send you their <strong>4-Dimension '
        f'Co-Parenting Briefing</strong>{" " + escaped_role if escaped_role else ""}.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:16px;padding:18px 20px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:6px;">'
        f'What is inside</div>'
        f'<ul style="margin:0;padding-left:18px;color:#1A1330;font-size:14px;line-height:1.55;">'
        f'<li><strong>Dimension 1 · Safety</strong> — family violence &amp; coercive-control screen.</li>'
        f'<li><strong>Dimension 2 · Communication</strong> — tone, cadence, clarity.</li>'
        f'<li><strong>Dimension 3 · Emotional regulation</strong> — stress &amp; conflict response.</li>'
        f'<li><strong>Dimension 4 · Executive function</strong> — planning &amp; follow-through.</li>'
        f'</ul>'
        f'</div>'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 12px 0;">'
        f'The briefing is attached as a PDF. You can reply directly to this email to reach {_html.escape(who)}.'
        f'</p>'
        f'<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        f'This briefing is informational preparation support only. It is not legal advice, medical '
        f'diagnosis, or a substitute for a licensed professional.</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"{who} is preparing for their next co-parenting session through SA CoParents "
        f"and asked me to send you their 4-Dimension Co-Parenting Briefing{role_line}.\n\n"
        f"The briefing consolidates:\n"
        f"  - Dimension 1 · Safety\n"
        f"  - Dimension 2 · Communication\n"
        f"  - Dimension 3 · Emotional regulation\n"
        f"  - Dimension 4 · Executive function\n"
        f"{optional_note_plain}"
        f"\nThe full briefing is attached as a PDF. You can reply directly to reach "
        f"{who} ({parent_email}).\n\n"
        f"This briefing is informational preparation support only. Not legal advice, "
        f"medical diagnosis, or a substitute for a licensed professional.\n"
    )
    html = _branded_html(
        headline=f"4-Dimension Briefing from {_html.escape(who)}",
        body_html=body_html,
        cta_label="",
    )
    subject = f"4-Dimension Co-Parenting Briefing from {who}"
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=parent_email or None,
        attachments=[(pdf_filename or "four-dimension-briefing.pdf", pdf_bytes)],
        failure_message="Couldn't send the briefing right now. Please try again in a moment.",
    )


def send_pathway_report(
    *,
    to_email: str,
    recipient_name: str,
    recipient_role: str,
    parent_name: str,
    parent_email: str,
    parent_message: str,
    is_dual_party: bool,
    primary_pathway_label: str,
    hard_locked: bool,
    pdf_bytes: bytes,
    pdf_filename: str = "pathway-report.pdf",
) -> None:
    """Send the Dispute Resolution Pathway Report PDF to a mediator,
    attorney, court, or therapist. Reply-to is the parent's email so the
    recipient can respond directly.

    Same tone as `send_four_dimension_briefing`: informational, non-
    directive, explicitly not legal advice. When the algorithm hard-
    locked to a non-mediation pathway (safety trigger) we flag that in
    the covering email body so the recipient knows to read the PDF's
    safety section carefully.
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    who = parent_name or parent_email or "This parent"
    role_line = f" ({recipient_role})" if recipient_role else ""
    escaped_role = _html.escape(recipient_role or "")
    escaped_pathway = _html.escape(primary_pathway_label or "Pathway recommendation")
    scope_label = (
        "Two-parent report (both parents consented via the Compare share)"
        if is_dual_party else
        "Single-parent preview (co-parent has not yet consented)"
    )
    optional_note_html = (
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0 0 16px 0;'
        f'background:#F8F7FC;border-radius:14px;padding:14px 16px;border:1px solid #E5E0EE;">'
        f'<span style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;">'
        f'Note from {_html.escape(who)}</span><br/>{_html.escape(parent_message)}</p>'
        if parent_message
        else ""
    )
    optional_note_plain = (
        f"\nNote from {who}:\n{parent_message}\n"
        if parent_message
        else ""
    )
    hard_lock_html = (
        f'<div style="background:#FCEDEB;border-radius:14px;padding:14px 16px;margin:0 0 16px 0;'
        f'border:1px solid #EFB4B4;color:#B02A2A;font-size:14px;line-height:1.55;">'
        f'<strong>Safety trigger applied.</strong> The rule engine did not '
        f'recommend a consensual process because safety indicators were '
        f'present in the assessment data. Please read the safety section '
        f'of the attached PDF carefully.'
        f'</div>'
        if hard_locked else ""
    )
    hard_lock_plain = (
        "\nSAFETY TRIGGER APPLIED. The rule engine did not recommend a "
        "consensual process because safety indicators were present. "
        "Please read the safety section of the PDF carefully.\n"
        if hard_locked else ""
    )

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'<strong>{_html.escape(who)}</strong> is preparing for their next '
        f'co-parenting session through SA CoParents and asked me to send you '
        f'their <strong>Dispute Resolution Pathway Report</strong>'
        f'{" " + escaped_role if escaped_role else ""}.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:16px;padding:18px 20px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:6px;">'
        f'Primary pathway</div>'
        f'<div style="font-size:16px;color:#1A1330;font-weight:700;line-height:1.35;">'
        f'{escaped_pathway}</div>'
        f'<div style="font-size:12px;color:#857E9C;margin-top:6px;">'
        f'{_html.escape(scope_label)}</div>'
        f'</div>'
        f'{hard_lock_html}'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 12px 0;">'
        f'The full report is attached as a PDF. It includes suitability '
        f'ratings across mediation, collaborative practice, arbitration, '
        f'and litigated processes, plus considerations and goals. You can '
        f'reply directly to this email to reach {_html.escape(who)}.'
        f'</p>'
        f'<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        f'This report is generated from a deterministic rule engine over '
        f'self-reported assessment data — not by an AI model, and not by a '
        f'licensed clinician. It is informational only. Not legal advice, '
        f'a psychological determination, or a substitute for the '
        f'recipient\u2019s own professional screening.</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"{who} is preparing for their next co-parenting session through "
        f"SA CoParents and asked me to send you their Dispute Resolution "
        f"Pathway Report{role_line}.\n\n"
        f"Primary pathway: {primary_pathway_label}\n"
        f"Scope: {scope_label}\n"
        f"{hard_lock_plain}"
        f"{optional_note_plain}"
        f"\nThe full report is attached as a PDF. You can reply directly "
        f"to reach {who} ({parent_email}).\n\n"
        f"This report is generated from a deterministic rule engine over "
        f"self-reported assessment data. It is informational only. Not "
        f"legal advice, a psychological determination, or a substitute "
        f"for the recipient's own professional screening.\n"
    )
    html = _branded_html(
        headline=f"Pathway Report from {_html.escape(who)}",
        body_html=body_html,
        cta_label="",
    )
    subject = f"Dispute Resolution Pathway Report from {who}"
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=parent_email or None,
        attachments=[(pdf_filename or "pathway-report.pdf", pdf_bytes)],
        failure_message="Couldn't send the pathway report right now. Please try again in a moment.",
    )





def send_joint_professional_report(
    *,
    to_email: str,
    recipient_name: str,
    recipient_role: str,
    parent_a_name: str,
    parent_b_name: str,
    parent_email: str,
    parent_message: str,
    summary_counts: Dict[str, int],
    pdf_bytes: bytes,
    pdf_filename: str = "joint-professional-report.pdf",
    preview_url: Optional[str] = None,
) -> None:
    """Email the Joint Co-Parenting Summary for Professional Review to a
    mediator, attorney, court, or therapist. Reply-to is the sending
    parent's email so the recipient can respond directly.

    Language is deliberately neutral and mirrors the report itself: the
    PDF is a preparation resource, NOT a custody evaluation, forensic
    assessment, clinical diagnosis, expert opinion, or recommendation to
    any court. Both parents' names appear in the covering copy so the
    recipient understands it aggregates both perspectives (a share
    already carries mutual consent).
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    sender = parent_a_name or parent_email or "This parent"
    escaped_role = _html.escape(recipient_role or "")
    scope = (
        f"{_html.escape(parent_a_name or 'Parent A')} and "
        f"{_html.escape(parent_b_name or 'Parent B')}"
    )
    diff_count = int(summary_counts.get("areas_where_perceptions_differ") or 0)
    agree_count = int(summary_counts.get("areas_of_agreement") or 0)
    issues_count = int(summary_counts.get("issues_for_professional_discussion") or 0)

    optional_note_html = (
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0 0 16px 0;'
        f'background:#F8F7FC;border-radius:14px;padding:14px 16px;border:1px solid #E5E0EE;">'
        f'<span style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;">'
        f'Note from {_html.escape(sender)}</span><br/>{_html.escape(parent_message)}</p>'
        if parent_message
        else ""
    )
    optional_note_plain = (
        f"\nNote from {sender}:\n{parent_message}\n"
        if parent_message
        else ""
    )
    disclaimer_html = (
        '<div style="background:#FCEDEB;border-radius:14px;padding:14px 16px;margin:0 0 16px 0;'
        'border:1px solid #EFB4B4;color:#B02A2A;font-size:13px;line-height:1.55;">'
        '<strong>This is not a custody evaluation.</strong> The attached '
        'Joint Report is a preparation and communication resource compiled '
        "from both parents' self-reported answers. It is not a forensic "
        "assessment, clinical diagnosis, expert opinion, or recommendation "
        "to any court."
        '</div>'
    )
    disclaimer_plain = (
        "\nTHIS IS NOT A CUSTODY EVALUATION. The attached Joint Report is a "
        "preparation and communication resource compiled from both parents' "
        "self-reported answers. It is not a forensic assessment, clinical "
        "diagnosis, expert opinion, or recommendation to any court.\n"
    )

    # Optional in-browser view link — same signed token minted by the
    # `share-link` endpoint. Lets the recipient click through from their
    # inbox instead of downloading the PDF first. Sender can revoke.
    view_link_html = ""
    view_link_plain = ""
    if preview_url:
        safe_url = _html.escape(preview_url)
        view_link_html = (
            '<div style="background:#EFE9F9;border-radius:14px;padding:14px 16px;'
            'margin:0 0 16px 0;border:1px solid #CFC1EA;">'
            '<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;'
            'color:#3D1A78;font-weight:700;margin-bottom:8px;">Prefer to view in your browser?</div>'
            f'<a href="{safe_url}" style="display:inline-block;background:#3D1A78;color:#FFFFFF;'
            'text-decoration:none;font-weight:600;font-size:14px;padding:10px 16px;'
            'border-radius:999px;">Open the joint report online</a>'
            '<div style="font-size:12px;color:#4B4567;margin-top:8px;line-height:1.5;">'
            'The link opens the same report that\u2019s attached here \u2014 no login required. '
            'Sender can revoke access at any time.</div>'
            '</div>'
        )
        view_link_plain = (
            f"\nPrefer to view in your browser? Open the joint report online:\n{preview_url}\n"
            "(Same content as the attached PDF. No login required. Sender can revoke access at any time.)\n"
        )

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'<strong>{_html.escape(sender)}</strong> is preparing for co-parenting '
        f'discussions through SA CoParents and asked me to send you the '
        f'<strong>Joint Co-Parenting Summary for Professional Review</strong> '
        f'covering {scope}'
        f'{" (" + escaped_role + ")" if escaped_role else ""}.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:16px;padding:16px 18px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:8px;">'
        f'At a glance</div>'
        f'<ul style="font-size:14px;color:#1A1330;line-height:1.55;margin:0;padding-left:18px;">'
        f'<li>{agree_count} items where both parents\u2019 responses aligned</li>'
        f'<li>{diff_count} items where their perceptions differ</li>'
        f'<li>{issues_count} topics flagged for professional discussion</li>'
        f'</ul>'
        f'</div>'
        f'{disclaimer_html}'
        f'{view_link_html}'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 12px 0;">'
        f'The full report is attached as a PDF, alongside a short '
        f'<em>3-minute Introduction to SA CoParents</em> so you have '
        f'context about the platform. Every row of the joint report is '
        f'phrased in neutral, non-adjudicative language and reflects '
        f'what the parents said, not what SA CoParents or any '
        f'professional has concluded. You can reply directly to this '
        f'email to reach {_html.escape(sender)}.'
        f'</p>'
        f'<p style="font-size:12px;line-height:1.55;color:#857E9C;margin:0;">'
        f'Only Finding 3 (Parenting-Plan Implications) of the Trauma-'
        f'Informed Safety and Functioning Lens is included. The underlying '
        f'family-violence and trauma findings remain private to the parent '
        f'who completed that screen.'
        f'</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"{sender} is preparing for co-parenting discussions through "
        f"SA CoParents and asked me to send you the Joint Co-Parenting "
        f"Summary for Professional Review covering "
        f"{parent_a_name or 'Parent A'} and {parent_b_name or 'Parent B'}"
        f"{' (' + (recipient_role or '') + ')' if recipient_role else ''}.\n\n"
        f"At a glance:\n"
        f"  * {agree_count} items where both parents' responses aligned\n"
        f"  * {diff_count} items where their perceptions differ\n"
        f"  * {issues_count} topics flagged for professional discussion\n"
        f"{disclaimer_plain}"
        f"{view_link_plain}"
        f"{optional_note_plain}"
        f"\nThe full report is attached as a PDF. Every row is phrased in "
        f"neutral, non-adjudicative language and reflects what the parents "
        f"said, not what SA CoParents or any professional has concluded. "
        f"You can reply directly to this email to reach {sender} "
        f"({parent_email}).\n\n"
        f"Only Finding 3 (Parenting-Plan Implications) of the Trauma-"
        f"Informed Safety and Functioning Lens is included. The underlying "
        f"family-violence and trauma findings remain private to the parent "
        f"who completed that screen.\n"
    )
    html = _branded_html(
        headline=f"Joint Co-Parenting Summary from {_html.escape(sender)}",
        body_html=body_html,
        cta_label="",
    )
    subject = (
        f"Joint Co-Parenting Summary for Professional Review \u2014 "
        f"{parent_a_name or 'Parent A'} & {parent_b_name or 'Parent B'}"
    )
    # Bundle the 3-minute Professional Intro as a companion attachment so
    # the recipient has context about the platform without the parent
    # having to attach it separately. Failures generating the intro must
    # never block the main send.
    try:
        from professional_intro_transcript import (
            PROFESSIONAL_INTRO_FILENAME, build_professional_intro_pdf,
        )
        intro_attachment = [
            (PROFESSIONAL_INTRO_FILENAME, build_professional_intro_pdf()),
        ]
    except Exception:  # pragma: no cover - defensive
        intro_attachment = []
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=parent_email or None,
        attachments=[
            (pdf_filename or "joint-professional-report.pdf", pdf_bytes),
        ] + intro_attachment,
        failure_message="Couldn't send the joint report right now. Please try again in a moment.",
        require_encrypted=True,
    )


def send_joint_agreement_draft(
    *,
    to_email: str,
    recipient_name: str,
    recipient_role: str,
    parent_a_name: str,
    parent_b_name: str,
    parent_email: str,
    parent_message: str,
    summary: Dict[str, Any],
    pdf_bytes: bytes,
    pdf_filename: str = "joint-coparenting-agreement.pdf",
    preview_url: Optional[str] = None,
) -> None:
    """Email the Joint Co-Parenting Agreement Draft PDF directly to a
    mediator, attorney, court, or therapist.

    Covering text is deliberately framed as a DRAFT FOR DISCUSSION — never
    a signed agreement, court order, or custody recommendation. Both
    parents' consent is implicit in the active Compare share the draft
    was generated from. Reply-to is the sending parent so the recipient
    can respond directly.
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    sender = parent_a_name or parent_email or "This parent"
    scope = (
        f"{_html.escape(parent_a_name or 'Parent A')} and "
        f"{_html.escape(parent_b_name or 'Parent B')}"
    )
    both_ct = int((summary or {}).get("both_proposed") or 0)
    a_only  = int((summary or {}).get("parent_a_only") or 0)
    b_only  = int((summary or {}).get("parent_b_only") or 0)
    conv_pct = int((summary or {}).get("converged_pct") or 0)

    optional_note_html = (
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0 0 16px 0;'
        f'background:#F8F7FC;border-radius:14px;padding:14px 16px;border:1px solid #E5E0EE;">'
        f'<span style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#3D1A78;font-weight:700;">'
        f'Note from {_html.escape(sender)}</span><br/>{_html.escape(parent_message)}</p>'
        if parent_message else ""
    )
    optional_note_plain = (
        f"\nNote from {sender}:\n{parent_message}\n"
        if parent_message else ""
    )
    disclaimer_html = (
        '<div style="background:#FFF6D8;border-radius:14px;padding:14px 16px;margin:0 0 16px 0;'
        'border:1px solid #E4D8B8;color:#8A6B12;font-size:13px;line-height:1.55;">'
        '<strong>This is a draft for discussion.</strong> The attached '
        'document is a merged draft compiled from both parents\u2019 '
        'individual agreement drafts. It is not a signed agreement, a '
        'court order, a legal document, or a custody recommendation. Both '
        'parents remain responsible for reviewing each clause with their '
        'own professionals before adopting anything.'
        '</div>'
    )
    disclaimer_plain = (
        "\nTHIS IS A DRAFT FOR DISCUSSION. The attached document is a "
        "merged draft compiled from both parents' individual agreement "
        "drafts. It is not a signed agreement, a court order, a legal "
        "document, or a custody recommendation.\n"
    )

    # Optional in-browser view link — same signed token the interactive
    # "Get shareable link" flow mints, so the recipient can click through
    # from their inbox instead of downloading the PDF first.
    view_link_html = ""
    view_link_plain = ""
    if preview_url:
        safe_url = _html.escape(preview_url)
        view_link_html = (
            '<div style="background:#EFE9F9;border-radius:14px;padding:14px 16px;'
            'margin:0 0 16px 0;border:1px solid #CFC1EA;">'
            '<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;'
            'color:#3D1A78;font-weight:700;margin-bottom:8px;">Prefer to view in your browser?</div>'
            f'<a href="{safe_url}" style="display:inline-block;background:#3D1A78;color:#FFFFFF;'
            'text-decoration:none;font-weight:600;font-size:14px;padding:10px 16px;'
            f'border-radius:999px;">Open the joint draft online</a>'
            '<div style="font-size:12px;color:#4B4567;margin-top:8px;line-height:1.5;">'
            'The link opens the same draft that\u2019s attached here \u2014 no login required. '
            f'Sender can revoke access at any time.</div>'
            '</div>'
        )
        view_link_plain = (
            f"\nPrefer to view in your browser? Open the joint draft online:\n{preview_url}\n"
            "(Same content as the attached PDF. No login required. Sender can revoke access at any time.)\n"
        )

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 16px 0;">'
        f'<strong>{_html.escape(sender)}</strong> is preparing for '
        f'co-parenting discussions through SA CoParents and asked me to '
        f'send you the <strong>Joint Co-Parenting Agreement Draft</strong> '
        f'covering {scope}'
        f'{" (" + _html.escape(recipient_role) + ")" if recipient_role else ""}.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:16px;padding:16px 18px;margin:0 0 16px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#3D1A78;font-weight:700;margin-bottom:8px;">'
        f'At a glance</div>'
        f'<ul style="font-size:14px;color:#1A1330;line-height:1.55;margin:0;padding-left:18px;">'
        f'<li>{both_ct} clauses proposed by <strong>both</strong> parents</li>'
        f'<li>{a_only} clauses proposed by {_html.escape(parent_a_name or "Parent A")} only</li>'
        f'<li>{b_only} clauses proposed by {_html.escape(parent_b_name or "Parent B")} only</li>'
        f'<li>Convergence: <strong>{conv_pct}%</strong></li>'
        f'</ul>'
        f'</div>'
        f'{disclaimer_html}'
        f'{view_link_html}'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 12px 0;">'
        f'The full draft is attached as a PDF, alongside a short '
        f'<em>3-minute Introduction to SA CoParents</em> so you have '
        f'context about the platform. Every clause is shown verbatim '
        f'under the parent who proposed it \u2014 the merger only '
        f'classifies clauses into buckets, it does not rewrite them. '
        f'You can reply directly to this email to reach {_html.escape(sender)}.'
        f'</p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"{sender} is preparing for co-parenting discussions through "
        f"SA CoParents and asked me to send you the Joint Co-Parenting "
        f"Agreement Draft covering "
        f"{parent_a_name or 'Parent A'} and {parent_b_name or 'Parent B'}"
        f"{' (' + (recipient_role or '') + ')' if recipient_role else ''}.\n\n"
        f"At a glance:\n"
        f"  * {both_ct} clauses proposed by both parents\n"
        f"  * {a_only} clauses proposed by "
        f"{parent_a_name or 'Parent A'} only\n"
        f"  * {b_only} clauses proposed by "
        f"{parent_b_name or 'Parent B'} only\n"
        f"  * Convergence: {conv_pct}%\n"
        f"{disclaimer_plain}"
        f"{view_link_plain}"
        f"{optional_note_plain}"
        f"\nThe full draft is attached as a PDF. Every clause is shown "
        f"verbatim under the parent who proposed it \u2014 the merger "
        f"only classifies clauses into buckets, it does not rewrite them. "
        f"You can reply directly to this email to reach {sender} "
        f"({parent_email}).\n"
    )
    html = _branded_html(
        headline=f"Joint Agreement Draft from {_html.escape(sender)}",
        body_html=body_html,
        cta_label="",
    )
    subject = (
        f"Joint Co-Parenting Agreement Draft \u2014 "
        f"{parent_a_name or 'Parent A'} & {parent_b_name or 'Parent B'}"
    )
    # Bundle the 3-minute Professional Intro alongside the draft so the
    # recipient has platform context regardless of whether they've also
    # received the Joint Report. Intro-build failures never block the send.
    try:
        from professional_intro_transcript import (
            PROFESSIONAL_INTRO_FILENAME, build_professional_intro_pdf,
        )
        intro_attachment = [
            (PROFESSIONAL_INTRO_FILENAME, build_professional_intro_pdf()),
        ]
    except Exception:  # pragma: no cover - defensive
        intro_attachment = []
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=parent_email or None,
        attachments=[
            (pdf_filename or "joint-coparenting-agreement.pdf", pdf_bytes),
        ] + intro_attachment,
        failure_message="Couldn't send the joint agreement right now. Please try again in a moment.",
        require_encrypted=True,
    )



def send_snc_report_pdf(
    *,
    to_email: str,
    user_name: Optional[str],
    pdf_bytes: bytes,
    pdf_filename: str = "Special_Needs_Report.pdf",
) -> None:
    """Email the authenticated parent their own Special Needs v2 report PDF."""
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    plain = (
        f"{greeting}\n\n"
        "Your Special Needs Co-Parenting report is attached as a branded PDF.\n\n"
        "It's a neutral, individualized summary you can keep for yourself, share "
        "with your mediator, or bring to a family professional. It does not "
        "diagnose, determine parental fitness, or replace legal advice.\n\n"
        "If your circumstances change, generate the report again from the SA "
        "CoParents app and any new information will be included.\n\n"
        "— SA CoParents · sacoparentsapp.online\n"
    )
    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"{greeting}</p>"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        "Your <strong>Special Needs Co-Parenting</strong> report is attached "
        "as a branded PDF.</p>"
        '<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 22px 0;">'
        "It's a neutral, individualized summary you can keep for yourself, "
        "share with your mediator, or bring to a family professional.</p>"
        '<p style="font-size:12px;line-height:1.5;color:#857E9C;margin:0 0 14px 0;">'
        "This report does not diagnose, determine parental fitness, or replace "
        "legal advice.</p>"
    )
    html = _branded_html(
        headline="Your Special Needs report",
        body_html=body_html,
        cta_label="Open SA CoParents",
        cta_url="https://sacoparentsapp.online",
    )
    _send(
        to_email=to_email,
        subject="Your Special Needs Co-Parenting report",
        html=html,
        text=plain,
        attachments=[(pdf_filename or "Special_Needs_Report.pdf", pdf_bytes)],
        failure_message="Couldn't email your Special Needs report right now. Please try again in a moment.",
    )


def send_weekly_progress_summary(
    *,
    to_email: str,
    user_name: Optional[str],
    completed_count: int,
    total: int,
    streak_days: int,
    milestones_this_week: List[str],
    alignment_pct: Optional[int],
    dashboard_url: str,
    personal_note: Optional[str] = None,
    cheers_received: Optional[List[Dict[str, Any]]] = None,
    community_pulse: Optional[List[Dict[str, Any]]] = None,
    wall_opted_in: bool = False,
) -> None:
    """Sunday-friendly momentum email. Neutral, encouraging, single CTA.

    ``cheers_received`` / ``community_pulse`` come from
    ``wall_utils.build_weekly_cheer_digest`` and render an optional
    "Community cheers" block below the milestones list. Cheerer identity
    is never exposed — counts + anonymised badge labels only. If both
    lists are empty (or the parent isn't opted-in AND the community has
    no cheer activity yet) the block is silently skipped.
    """
    hello = (user_name or "").strip() or "there"
    note = (personal_note or "").strip()
    lit = ", ".join(milestones_this_week) if milestones_this_week else ""
    week_line = (
        f"This week you lit {lit}." if lit
        else "No new milestones lit this week — small steps still count."
    )
    streak_line = (
        f"You've shown up {streak_days} day{'s' if streak_days != 1 else ''} in a row. "
        "Consistency is the quiet superpower of co-parenting."
        if streak_days > 0
        else "A brand-new week is a great time to start a streak."
    )
    align_line = (
        f"Latest alignment with your co-parent: {alignment_pct}%."
        if isinstance(alignment_pct, int)
        else ""
    )

    # ------------------------------------------------------------------
    # Cheer digest — plain-text lines
    # ------------------------------------------------------------------
    cheers_received = cheers_received or []
    community_pulse = community_pulse or []
    total_cheers_received = sum(int(r.get("cheer_count") or 0) for r in cheers_received)
    cheer_lines_plain: List[str] = []
    if cheers_received:
        cheer_lines_plain.append(
            f"Community cheers on your milestones this week: {total_cheers_received}"
        )
        for r in cheers_received:
            n = int(r.get("cheer_count") or 0)
            lbl = str(r.get("badge_label") or r.get("badge_type") or "").rstrip(".")
            cheer_lines_plain.append(
                f"  \u2665 {n} cheer{'s' if n != 1 else ''} on: {lbl}"
            )
    if community_pulse:
        top = community_pulse[0]
        n = int(top.get("cheer_count") or 0)
        lbl = str(top.get("badge_label") or top.get("badge_type") or "").rstrip(".")
        cheer_lines_plain.append(
            f"Most-cheered community moment this week: {lbl} ({n} cheers)."
        )
    cheer_block_plain = ("\n" + "\n".join(cheer_lines_plain) + "\n") if cheer_lines_plain else ""

    plain = (
        f"Hi {hello},\n\n"
        f"Your Sunday snapshot from SA CoParents.\n\n"
        + (f"A quick note from you:\n\u201C{note}\u201D\n\n" if note else "")
        + f"Progress: {completed_count} of {total} milestones lit.\n"
        f"{week_line}\n"
        f"{streak_line}\n"
        f"{align_line}\n"
        f"{cheer_block_plain}\n"
        f"Open your dashboard: {dashboard_url}\n\n"
        "\u2014 SA CoParents \u00b7 sacoparentsapp.online\n"
    )
    milestone_html = ""
    if milestones_this_week:
        milestone_html = (
            '<ul style="margin:8px 0 14px 0;padding:0 0 0 18px;color:#1A1330;font-size:14px;line-height:1.55;">'
            + "".join(f"<li>{m}</li>" for m in milestones_this_week)
            + "</ul>"
        )
    align_html = ""
    if align_line:
        align_html = (
            '<div style="font-size:13px;color:#4B4567;margin:6px 0 0 0;">'
            f'{align_line}</div>'
        )
    note_html = ""
    if note:
        safe_note = _html.escape(note).replace("\n", "<br/>")
        note_html = (
            '<div style="margin:0 0 18px 0;padding:16px 18px;border-radius:14px;'
            'border:1px solid #E4D8B8;background:#FFF9EB;position:relative;">'
            '<div style="font-size:10px;letter-spacing:0.22em;text-transform:uppercase;'
            'color:#8A6B12;font-weight:700;margin:0 0 6px 0;">A note from you</div>'
            '<div style="font-family:\'Caveat\',\'Bradley Hand\',cursive;'
            'font-size:20px;line-height:1.45;color:#3B2A05;">'
            f'\u201C{safe_note}\u201D'
            '</div>'
            '</div>'
        )

    # ------------------------------------------------------------------
    # Cheer digest — HTML block
    # ------------------------------------------------------------------
    cheer_block_html = ""
    if cheers_received or community_pulse:
        rows_html_parts: List[str] = []
        if cheers_received:
            rows_html_parts.append(
                '<div style="font-size:13px;color:#4B4567;margin:0 0 8px 0;">'
                f'<strong>{total_cheers_received} cheer{"s" if total_cheers_received != 1 else ""}</strong> '
                'landed on your milestones this week from other parents on the wall.'
                '</div>'
            )
            for r in cheers_received[:5]:
                n = int(r.get("cheer_count") or 0)
                lbl = _html.escape(str(r.get("badge_label") or "").rstrip("."))
                rows_html_parts.append(
                    '<div style="font-size:13px;color:#1A1330;margin:0 0 4px 0;">'
                    f'<span style="color:#B8125A;">&hearts;</span> '
                    f'<strong>{n}</strong> on: <em style="color:#4B4567;font-style:normal;">{lbl}</em>'
                    '</div>'
                )
        if community_pulse:
            top = community_pulse[0]
            n = int(top.get("cheer_count") or 0)
            lbl = _html.escape(str(top.get("badge_label") or "").rstrip("."))
            rows_html_parts.append(
                '<div style="font-size:12px;color:#4B4567;margin:10px 0 0 0;'
                'padding-top:10px;border-top:1px dashed #D6CFE8;">'
                'Most-cheered community moment this week: '
                f'<em style="color:#3D1A78;font-style:normal;">{lbl}</em> '
                f'\u00b7 <strong>{n} cheers</strong>.'
                '</div>'
            )
        header_label = "Community cheers" if wall_opted_in else "From the community"
        cheer_block_html = (
            '<div style="margin:0 0 18px 0;padding:14px 16px;border-radius:14px;'
            'border:1px solid #F4D0DE;background:#FEF5F8;">'
            '<div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;'
            f'color:#B8125A;font-weight:700;margin:0 0 6px 0;">{header_label}</div>'
            + "".join(rows_html_parts)
            + '</div>'
        )

    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"Hi <strong>{hello}</strong>, your Sunday snapshot from SA CoParents.</p>"
        f'{note_html}'
        '<div style="margin:0 0 18px 0;padding:14px 16px;border-radius:14px;'
        'border:1px solid #D6CFE8;background:#F5F1FB;">'
        '<div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;'
        'color:#3D1A78;font-weight:700;margin:0 0 4px 0;">Weekly progress</div>'
        f'<div style="font-size:22px;line-height:1.2;color:#1A1330;font-weight:800;'
        f'font-family:Georgia,\'Times New Roman\',serif;">'
        f'{completed_count} of {total} milestones lit.</div>'
        f'<div style="font-size:13px;color:#4B4567;margin:6px 0 0 0;">{streak_line}</div>'
        f'{align_html}'
        '</div>'
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 8px 0;">{week_line}</p>'
        f"{milestone_html}"
        f"{cheer_block_html}"
        '<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 18px 0;">'
        "Small, steady work is what mediators love to see.</p>"
    )
    html = _branded_html(
        headline="Your Sunday progress snapshot",
        body_html=body_html,
        cta_label="Open my dashboard",
        cta_url=dashboard_url,
    )
    _send(
        to_email=to_email,
        subject="Your Sunday co-parenting progress snapshot",
        html=html,
        text=plain,
        failure_message="Couldn't send your weekly summary right now. Please try again in a moment.",
    )



def send_reviewer_packet(
    *,
    to_email: str,
    recipient_name: str,
    recipient_role_label: str,
    operator_name: str,
    operator_email: str,
    personal_note: str,
    pdf_bytes: bytes,
    pdf_filename: str = "sa-coparents-safety-screen-reviewer-packet.pdf",
) -> None:
    """Email the Safety Screen Reviewer Packet to a candidate reviewer.

    The email is a professional invitation to review the SA CoParents
    Family Violence and Communication Safety Screen. Reply-to is the
    operator's real email so the reviewer can respond directly.
    """
    greeting = f"Dear {recipient_name}," if recipient_name else "Dear reviewer,"
    role_esc = _html.escape(recipient_role_label or "")
    optional_note_html = (
        f'<div style="background:#F8F7FC;border-radius:14px;padding:14px 16px;'
        f'border:1px solid #E5E0EE;margin:0 0 16px 0;">'
        f'<div style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;'
        f'color:#3D1A78;font-weight:700;margin-bottom:4px;">Personal note</div>'
        f'<div style="font-size:14px;line-height:1.6;color:#1A1330;">{_html.escape(personal_note)}</div>'
        f'</div>'
        if personal_note
        else ""
    )
    optional_note_plain = f"\nPersonal note:\n{personal_note}\n" if personal_note else ""

    body_html = (
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 14px 0;">'
        f'{_html.escape(greeting)}</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 14px 0;">'
        f"I&rsquo;m {_html.escape(operator_name) or 'the operator'} of "
        f'<strong>SA CoParents</strong>, a preparation tool for separating '
        f'parents. I&rsquo;m writing to invite your professional review of our '
        f'<strong>Family Violence and Communication Safety Screen</strong>'
        f'{" as " + role_esc if role_esc else ""}.'
        f'</p>'
        f'<p style="font-size:15px;line-height:1.6;color:#4B4567;margin:0 0 14px 0;">'
        f'The screen is a self-administered educational tool. It is not '
        f'presented to users as a validated clinical instrument, and our '
        f'methodology page is candid about that. That said, users may still '
        f'assign more authority to a polished score than the disclaimer '
        f'intends, and I want expert eyes on every question, rule, and '
        f'report before we tell parents to rely on it.'
        f'</p>'
        f'<div style="background:#F8F7FC;border-radius:14px;padding:16px 18px;'
        f'margin:0 0 14px 0;border:1px solid #E5E0EE;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;'
        f'color:#3D1A78;font-weight:700;margin-bottom:6px;">The attached packet contains</div>'
        f'<ul style="margin:0;padding-left:18px;color:#1A1330;font-size:14px;line-height:1.55;">'
        f'<li>How the screen currently works (Sections 1 &amp; 2, pathway logic).</li>'
        f'<li>Every current question, with high-concern triggers flagged.</li>'
        f'<li>A reviewer checklist tailored to this instrument.</li>'
        f'<li>The MASIC-S coverage gaps I&rsquo;d like you to draft items for.</li>'
        f'<li>A sign-off page with your name, credentials, role, review date, and a public attestation.</li>'
        f'</ul></div>'
        f'{optional_note_html}'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 14px 0;">'
        f'If you agree, your name, credentials, role, and review date will be '
        f'published on our public methodology page — this is a transparency '
        f'commitment to users. Your review does not constitute a clinical, '
        f'legal, or evidentiary endorsement of the tool for any specific case.'
        f'</p>'
        f'<p style="font-size:14px;line-height:1.6;color:#4B4567;margin:0 0 14px 0;">'
        f'Please reply directly to this email with any questions, timeline, '
        f'or fee expectations. Thank you for considering.'
        f'</p>'
        f'<p style="font-size:14px;line-height:1.6;color:#1A1330;margin:0;">'
        f'Warmly,<br/><strong>{_html.escape(operator_name or "SA CoParents")}</strong><br/>'
        f'<span style="color:#4B4567;">{_html.escape(operator_email)}</span></p>'
    )
    plain = (
        f"{greeting}\n\n"
        f"I'm {operator_name or 'the operator'} of SA CoParents, a preparation "
        f"tool for separating parents. I'm writing to invite your professional "
        f"review of our Family Violence and Communication Safety Screen"
        f"{' as ' + (recipient_role_label or '') if recipient_role_label else ''}.\n\n"
        f"The screen is a self-administered educational tool. It is not presented "
        f"to users as a validated clinical instrument, and our methodology page "
        f"is candid about that. That said, users may still assign more authority "
        f"to a polished score than the disclaimer intends, and I want expert "
        f"eyes on every question, rule, and report before we tell parents to "
        f"rely on it.\n\n"
        f"The attached packet contains:\n"
        f"  - How the screen currently works\n"
        f"  - Every current question, with high-concern triggers flagged\n"
        f"  - A reviewer checklist tailored to this instrument\n"
        f"  - MASIC-S coverage gaps to draft items for\n"
        f"  - A sign-off page for name, credentials, role, review date, and public attestation\n"
        f"{optional_note_plain}\n"
        f"If you agree, your name, credentials, role, and review date will be "
        f"published on our public methodology page — a transparency commitment "
        f"to users. Your review does not constitute a clinical, legal, or "
        f"evidentiary endorsement for any specific case.\n\n"
        f"Please reply directly to this email with any questions, timeline, or "
        f"fee expectations.\n\n"
        f"Warmly,\n{operator_name or 'SA CoParents'}\n{operator_email}\n"
    )
    html = _branded_html(
        headline="Reviewer invitation · Family Violence and Communication Safety Screen",
        body_html=body_html,
        cta_label="",
    )
    subject = "SA CoParents · Invitation to review our Safety Screen"
    _send(
        to_email=to_email,
        subject=subject,
        html=html,
        text=plain,
        reply_to=operator_email or None,
        attachments=[(pdf_filename, pdf_bytes)],
        failure_message="Couldn't send the reviewer packet right now. Please try again in a moment.",
    )



def send_coordinator_nd_alert(
    *,
    to_email: str,
    tier: str,
    tier_label: str,
    total_score: int,
    target_name: Optional[str],
    coparent_name: Optional[str],
    assessment_id: str,
    submitted_at: str,
    reason: str = "hit",
) -> None:
    """Fire a low-noise ops email to the operator when a parent's ND Risk
    Assessment lands on ``high`` or ``critical``.

    - Kept intentionally terse so it reads well from a phone lock-screen.
    - Includes the assessment id (the operator has admin role and can
      hit ``GET /api/nd-risk/assessment/{id}`` to pull the full record).
    - `reason` distinguishes fresh alerts from tier escalations.
    """
    submitted_display = submitted_at[:19].replace("T", " ") + " UTC"
    target_display   = target_name  or "(no name)"
    coparent_display = coparent_name or "(no coparent named)"
    tier_color = "#B02A2A" if tier == "critical" else "#B26A00"

    reason_headline = {
        "hit":       f"ND Risk hit {tier_label}",
        "escalated": f"ND Risk ESCALATED to {tier_label}",
        "re_hit":    f"ND Risk still at {tier_label}",
    }.get(reason, f"ND Risk at {tier_label}")

    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"A parent's Neurodivergent Risk Assessment just resolved to a tier "
        f"that warrants a same-day human touch-point.</p>"
        f'<div style="background:#FCEDEB;border-left:4px solid {tier_color};border-radius:12px;padding:14px 16px;margin:0 0 18px 0;">'
        f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{tier_color};font-weight:800;">{_html.escape(reason.replace("_", " ").title())}</div>'
        f'<div style="font-size:20px;font-weight:800;color:#1A1330;margin-top:4px;">Tier: {_html.escape(tier_label)}'
        f' <span style="font-size:14px;font-weight:600;color:#4B4567;">(score {total_score}/16)</span></div>'
        f"</div>"
        f'<table role="presentation" style="border-collapse:collapse;width:100%;font-size:14px;color:#1A1330;margin:0 0 18px 0;">'
        f'<tr><td style="padding:6px 0;color:#4B4567;width:40%;">Target parent</td>'
        f'<td style="padding:6px 0;font-weight:600;">{_html.escape(target_display)}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#4B4567;">Coparent named</td>'
        f'<td style="padding:6px 0;font-weight:600;">{_html.escape(coparent_display)}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#4B4567;">Submitted</td>'
        f'<td style="padding:6px 0;font-weight:600;">{_html.escape(submitted_display)}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#4B4567;">Assessment ID</td>'
        f'<td style="padding:6px 0;font-family:monospace;font-size:12px;">{_html.escape(assessment_id)}</td></tr>'
        f"</table>"
        f'<p style="font-size:13px;line-height:1.55;color:#857E9C;margin:0 0 8px 0;">'
        f"Pull the full record: "
        f'<code style="background:#F1EEF7;padding:2px 6px;border-radius:6px;">'
        f"GET /api/nd-risk/assessment/{_html.escape(assessment_id)}"
        f"</code></p>"
        f'<p style="font-size:12px;color:#857E9C;line-height:1.55;margin:12px 0 0 0;font-style:italic;">'
        f"This alert re-fires at most once per 24 hours per parent per tier; "
        f"an escalation to a higher tier always re-fires immediately.</p>"
    )
    plain = (
        f"{reason_headline}\n"
        f"Score {total_score}/16 · Tier {tier_label}\n\n"
        f"Target parent : {target_display}\n"
        f"Coparent named: {coparent_display}\n"
        f"Submitted     : {submitted_display}\n"
        f"Assessment ID : {assessment_id}\n\n"
        f"Pull the full record: GET /api/nd-risk/assessment/{assessment_id}\n"
        f"(This alert re-fires at most once per 24h per parent per tier; "
        f"an escalation to a higher tier always re-fires immediately.)\n"
    )
    html = _branded_html(
        headline=reason_headline,
        body_html=body_html,
        cta_label="",
    )
    _send(
        to_email=to_email,
        subject=f"[SA CoParents · Coordinator] {reason_headline} · {target_display}",
        html=html,
        text=plain,
        failure_message="Couldn't dispatch the coordinator alert email right now.",
    )



def send_weekly_compliance_reminder(
    *,
    to_email: str,
    user_name: str,
    pending_items: List[Dict[str, Any]],
    pending_total: int,
    current_streak: int,
    compliance_pct: float,
    week_start: str,
    cta_url: str,
    wall_cheer_digest: Optional[Dict[str, Any]] = None,
) -> None:
    """Warm Monday nudge protecting the follow-through streak.

    Copy stays short and specific: "You have N unticked things this week,
    your K-week streak is still alive — here are the top few." No guilt
    trip, no dark patterns.
    """
    greeting = (
        f"Hi {user_name.split()[0] if user_name else 'there'},"
    )

    if current_streak >= 4:
        streak_line = (
            f"You're on a <strong>{current_streak}-week streak</strong> of 80%+ "
            f"follow-through. Nice work — keep the momentum this week."
        )
        streak_plain = (
            f"You're on a {current_streak}-week streak of 80%+ follow-through. "
            f"Nice work — keep the momentum this week."
        )
    elif current_streak >= 1:
        streak_line = (
            f"Your current streak is <strong>{current_streak} week"
            f"{'' if current_streak == 1 else 's'}</strong>. "
            f"One steady week keeps it alive."
        )
        streak_plain = (
            f"Your current streak is {current_streak} week"
            f"{'' if current_streak == 1 else 's'}. One steady week keeps it alive."
        )
    else:
        streak_line = (
            "Every kept promise this week is the first brick of a new streak."
        )
        streak_plain = streak_line

    items_html = ""
    items_plain = ""
    if pending_items:
        rows_html = "".join([
            f'<li style="padding:8px 0;border-bottom:1px solid #EFEBF6;'
            f'font-size:14px;color:#1A1330;line-height:1.5;">'
            f'{_html.escape(str(it.get("text") or ""))}'
            f'</li>'
            for it in pending_items
        ])
        items_html = (
            f'<div style="background:#FCFBFE;border-radius:16px;padding:14px 18px;'
            f'border:1px solid #E5E0EE;margin:14px 0 20px 0;">'
            f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;'
            f'color:#3D1A78;font-weight:800;margin-bottom:6px;">'
            f"Top of the list this week</div>"
            f'<ul style="margin:0;padding:0 0 0 18px;">{rows_html}</ul>'
            f"</div>"
        )
        overflow = pending_total - len(pending_items)
        if overflow > 0:
            items_html += (
                f'<p style="font-size:12px;color:#857E9C;margin:-8px 0 16px 0;'
                f'font-style:italic;">'
                f"+ {overflow} more waiting for you in the app.</p>"
            )
        items_plain = (
            "Top of the list this week:\n"
            + "\n".join([f"  · {it.get('text','')}" for it in pending_items])
            + (f"\n  · (+ {overflow} more in the app)\n" if overflow > 0 else "\n")
        )

    pct_line = ""
    if compliance_pct > 0:
        pct_line = (
            f'<p style="font-size:13px;color:#857E9C;margin:0 0 14px 0;">'
            f"You're at <strong style=\"color:#3D1A78;\">{compliance_pct:.0f}%</strong> "
            f"for the week of {_html.escape(week_start)}.</p>"
        )

    # Wall Cheer Digest — roll the week's cheers into the Monday email
    # so parents feel the community response alongside the reminder.
    cheers_html = ""
    cheers_plain = ""
    if wall_cheer_digest and int(wall_cheer_digest.get("cheer_count") or 0) > 0:
        n = int(wall_cheer_digest["cheer_count"])
        badges = wall_cheer_digest.get("top_badges") or []
        badge_rows_html = "".join([
            f'<li style="padding:6px 0;font-size:13px;color:#1A1330;line-height:1.5;">'
            f'<strong style="color:#3D1A78;">{int(b.get("cheer_count") or 0)} '
            f"cheer{'' if int(b.get('cheer_count') or 0) == 1 else 's'}</strong> "
            f'on your <em>{_html.escape(str(b.get("label") or ""))}</em>'
            f"</li>"
            for b in badges
        ])
        cheers_html = (
            f'<div style="background:linear-gradient(135deg,#F5F1FB 0%,#E0F7F5 100%);'
            f"border-radius:16px;padding:14px 18px;border:1px solid #C6BEE0;"
            f'margin:14px 0 20px 0;">'
            f'<div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;'
            f'color:#3D1A78;font-weight:800;margin-bottom:6px;">'
            f"Cheers you got this week</div>"
            f'<p style="font-size:14px;color:#1A1330;margin:0 0 6px 0;">'
            f"You received <strong>{n} cheer{'' if n == 1 else 's'}</strong> "
            f"from other parents on the Wall this week — proof someone else "
            f"is watching you show up.</p>"
            + (f'<ul style="margin:6px 0 0 0;padding:0 0 0 18px;">{badge_rows_html}</ul>'
               if badge_rows_html else "")
            + "</div>"
        )
        badge_plain = "\n".join([
            f"  · {int(b.get('cheer_count') or 0)} cheer(s) on your "
            f"{b.get('label') or ''}"
            for b in badges
        ])
        cheers_plain = (
            f"\nCheers you got this week: {n} from other parents.\n"
            + (badge_plain + "\n" if badge_plain else "")
        )

    body_html = (
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 12px 0;">'
        f"{_html.escape(greeting)}</p>"
        f'<p style="font-size:15px;line-height:1.55;color:#4B4567;margin:0 0 14px 0;">'
        f"You have <strong>{pending_total} intervention"
        f"{'' if pending_total == 1 else 's'}</strong> still un-ticked for this week. "
        f"{streak_line}</p>"
        f"{pct_line}"
        f"{cheers_html}"
        f"{items_html}"
        f'<p style="font-size:13px;color:#857E9C;margin:16px 0 0 0;">'
        f"Prefer not to get this Monday email? "
        f"<a href=\"{_html.escape(cta_url)}\" style=\"color:#3D1A78;\">"
        f"Turn it off in your compliance settings</a>.</p>"
    )

    plain = (
        f"{greeting}\n\n"
        f"You have {pending_total} intervention"
        f"{'' if pending_total == 1 else 's'} still un-ticked for this week. "
        f"{streak_plain}\n\n"
        + (f"You're at {compliance_pct:.0f}% for the week of {week_start}.\n\n"
           if compliance_pct > 0 else "")
        + cheers_plain
        + items_plain
        + f"\nTick them off: {cta_url}\n\n"
        + "Prefer not to get this Monday email? Turn it off in your compliance settings.\n"
    )

    html = _branded_html(
        headline=f"Monday check-in · {pending_total} to tick",
        body_html=body_html,
        cta_label="Open my compliance log",
        cta_url=cta_url,
    )
    _send(
        to_email=to_email,
        subject=f"Monday check-in · {pending_total} intervention"
        + ("" if pending_total == 1 else "s")
        + " still open",
        html=html,
        text=plain,
        failure_message="Couldn't send the weekly compliance reminder right now.",
    )
