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
