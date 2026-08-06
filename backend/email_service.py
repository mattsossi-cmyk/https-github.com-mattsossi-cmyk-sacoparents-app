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
