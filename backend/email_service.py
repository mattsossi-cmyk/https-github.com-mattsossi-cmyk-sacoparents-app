"""Email service for sending PDF documents to mediators via SMTP."""
import os
import smtplib
import logging
from email.message import EmailMessage
from typing import List, Optional, Tuple


logger = logging.getLogger(__name__)


class EmailNotConfigured(Exception):
    """SMTP credentials are missing — feature should be reported as disabled."""


class EmailSendError(Exception):
    """SMTP send failed — surface a friendly message to the user."""


def _config() -> dict:
    cfg = {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT") or 587),
        "username": os.environ.get("SMTP_USERNAME", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "from_email": os.environ.get("SMTP_FROM_EMAIL", "").strip()
        or os.environ.get("SMTP_USERNAME", "").strip(),
        "from_name": os.environ.get("SMTP_FROM_NAME", "SA Coparents").strip(),
    }
    return cfg


def is_configured() -> bool:
    c = _config()
    return bool(c["host"] and c["username"] and c["password"] and c["from_email"])


def _cover_note(
    user_name: str,
    user_email: str,
    mediator_name: Optional[str],
    doc_labels: List[str],
) -> Tuple[str, str]:
    """Return (plain_text, html) cover note."""
    greeting = f"Hi {mediator_name}," if mediator_name else "Hello,"
    docs_phrase = (
        doc_labels[0]
        if len(doc_labels) == 1
        else (" and ".join(doc_labels) if len(doc_labels) == 2 else ", ".join(doc_labels[:-1]) + ", and " + doc_labels[-1])
    )
    display_name = user_name or user_email

    plain = (
        f"{greeting}\n\n"
        f"{display_name} has completed preparation for your upcoming relational "
        f"mediation session using SA Coparents, and would like to share the "
        f"attached {docs_phrase} with you ahead of time.\n\n"
        f"These documents include their child-centered goals, top concerns, "
        f"priority agenda, communication preferences, and readiness reflection — "
        f"intended to help your session start from a focused, child-centered "
        f"place.\n\n"
        f"Please feel free to reply directly to this email "
        f"({user_email}) with any questions or scheduling notes.\n\n"
        f"Warmly,\n"
        f"SA Coparents — Relational Mediation Prep\n"
        f"This email was sent on behalf of {display_name} via the SA Coparents app."
    )

    html = f"""<!doctype html>
<html><body style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:#2A3631; line-height:1.55; max-width:560px; margin:0 auto; padding:24px;">
  <div style="background:#F5F3E9; border-radius:14px; padding:24px 22px; margin-bottom:20px;">
    <div style="color:#849D8E; font-size:11px; letter-spacing:.2em; text-transform:uppercase; margin-bottom:6px;">SA Coparents</div>
    <div style="font-family: Georgia, 'Times New Roman', serif; font-size:22px; color:#2A3631;">Relational mediation prep — shared by {display_name}</div>
  </div>

  <p>{greeting}</p>

  <p>{display_name} has completed preparation for your upcoming relational
  mediation session using <strong>SA Coparents</strong>, and would like to share
  the attached <strong>{docs_phrase}</strong> with you ahead of time.</p>

  <p>These documents include their child-centered goals, top concerns, priority
  agenda, communication preferences, and readiness reflection — intended to help
  your session start from a focused, child-centered place.</p>

  <p>Please feel free to reply directly to this email
  (<a href="mailto:{user_email}" style="color:#5C7A6A;">{user_email}</a>)
  with any questions or scheduling notes.</p>

  <p style="margin-top:28px;">Warmly,<br/>
  <span style="color:#5C6B64;">SA Coparents — Relational Mediation Prep</span></p>

  <hr style="border:none; border-top:1px solid #E8ECE9; margin:24px 0;"/>
  <p style="font-size:12px; color:#8A9A92; font-style:italic;">
    This email was sent on behalf of {display_name} via the SA Coparents app.
    Replies will go directly to {user_email}.
  </p>
</body></html>"""

    return plain, html


def send_mediator_email(
    *,
    to_email: str,
    mediator_name: Optional[str],
    user_name: str,
    user_email: str,
    attachments: List[Tuple[str, bytes]],  # (filename, pdf_bytes)
    doc_labels: List[str],
) -> None:
    """Send PDFs to a mediator. Raises EmailNotConfigured or EmailSendError."""
    if not is_configured():
        raise EmailNotConfigured(
            "Email sending is not configured yet. Please contact the app administrator."
        )
    if not attachments:
        raise EmailSendError("No documents selected to send.")

    cfg = _config()
    plain, html = _cover_note(user_name, user_email, mediator_name, doc_labels)

    msg = EmailMessage()
    msg["Subject"] = f"Mediation prep from {user_name or user_email}"
    msg["From"] = f'"{cfg["from_name"]}" <{cfg["from_email"]}>'
    msg["To"] = to_email
    if user_email:
        msg["Reply-To"] = user_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    for filename, data in attachments:
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(cfg["username"], cfg["password"])
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        logger.exception("SMTP auth failed")
        raise EmailSendError(
            "Email service authentication failed. Please verify SMTP credentials."
        ) from e
    except (smtplib.SMTPException, OSError) as e:
        logger.exception("SMTP send failed")
        raise EmailSendError(
            "Could not send email right now. Please try again in a moment."
        ) from e
