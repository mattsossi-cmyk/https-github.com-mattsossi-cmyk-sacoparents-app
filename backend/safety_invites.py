"""Safety-first invitations (owner spec Phase 2): two neutral templates, single-use 7-day link, reply-to the professional, cadence reminders."""
import uuid
from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import (
    INVITE_EXPIRY_DAYS,
    PRO_ROLES,
    _parse_iso,
    app_url,
    db,
    invite_link,
    logger,
)
from email_utils import EMAIL_FROM_NAME, NEUTRAL_SUBJECT, send_email

DEFAULT_CADENCE = {"reminder_days": [3, 6], "max_reminders": 2, "expiry_days": INVITE_EXPIRY_DAYS}
PRIVATE_DEVICE_LINE = "Please open this on a device only you can access. This link works once and expires in 7 days; after that your professional can send a fresh one."


def _wrap(inner: str) -> str:
    return ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">' + inner +
            f'<p>Please do not forward this message or share your sign-in details.</p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p></td></tr></table>')


def _button(link: str, text: str) -> str:
    return f'<p><a href="{link}" style="display:inline-block;background:#5B2A86;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:6px">{text}</a></p>'


def _verify_block(code: str) -> str:
    return (f'<table role="presentation" style="margin-top:8px"><tr><td style="vertical-align:top;padding-right:14px">'
            f'<img src="{app_url()}/api/verify/{escape(code)}/qr.png" width="96" height="96" alt="QR code to verify this professional" style="display:block;border:1px solid #ddd;border-radius:6px"></td>'
            f'<td style="vertical-align:top;font-size:13px;color:#444">Want to confirm who sent this? Scan the code or visit '
            f'<a href="{app_url()}/verify?code={escape(code)}" style="color:#5B2A86">{escape(app_url())}/verify</a> and enter case code <strong>{escape(code)}</strong>.</td></tr></table>')


def professional_template(name: str, pro_name: str, code: str, token: str) -> tuple[str, str]:
    """Template 1 — sent when a professional opens the case. Neutral: no screening, tier or co-parent wording."""
    link = invite_link(token)
    html = _wrap(
        f"<p>Hi {escape(name or 'there')},</p>"
        f"<p>{escape(pro_name)} has set up a private SA CoParents account for you. It begins with a short private check-in, then your own assessment, each completed on your own and in your own time.</p>"
        f"<p>{PRIVATE_DEVICE_LINE}</p>"
        f'<p>Your private participation code is:</p><p><strong style="font-size:18px;letter-spacing:2px">{escape(code)}</strong></p>'
        + _button(link, "Get started privately") +
        f"<p>Questions about this invitation? Reply to this email and it goes directly to {escape(pro_name)}.</p>"
        + _verify_block(code))
    return NEUTRAL_SUBJECT, html


def coparent_template(name: str, inviter_name: str, code: str, token: str) -> tuple[str, str]:
    """Template 2 — sent when a parent invites the other parent. Same neutral structure; no case details."""
    link = invite_link(token)
    html = _wrap(
        f"<p>Hi {escape(name or 'there')},</p>"
        f"<p>{escape(inviter_name)} has invited you to take part in an SA CoParents Joint Alignment Report. Each parent completes a short private check-in and their own assessment separately; nothing you enter is shown to the other parent.</p>"
        f"<p>{PRIVATE_DEVICE_LINE}</p>"
        f'<p>Your private participation code is:</p><p><strong style="font-size:18px;letter-spacing:2px">{escape(code)}</strong></p>'
        + _button(link, "Get started privately") + _verify_block(code))
    return NEUTRAL_SUBJECT, html


def reminder_template(name: str, token: str, n: int) -> tuple[str, str]:
    html = _wrap(
        f"<p>Hi {escape(name or 'there')},</p>"
        f"<p>A gentle reminder that your private SA CoParents invitation is still waiting. {PRIVATE_DEVICE_LINE}</p>"
        + _button(invite_link(token), "Get started privately") +
        f'<p style="font-size:12px;color:#888">Reminder {n} of {DEFAULT_CADENCE["max_reminders"]}.</p>')
    return NEUTRAL_SUBJECT, html


async def case_professional(report_id: str) -> dict | None:
    rep = await db.joint_reports.find_one({"id": report_id}, {"created_by": 1, "professional_id": 1})
    if not rep:
        return None
    for uid in (rep.get("professional_id"), rep.get("created_by")):
        if not uid:
            continue
        u = await db.users.find_one({"_id": uid}, {"name": 1, "email": 1, "role": 1})
        if u and u.get("role") in PRO_ROLES:
            return u
    return None


async def build_invite_email(report_id: str, invitee_name: str, inviter_name: str, code: str, token: str) -> tuple[str, str, str | None]:
    """Returns (subject, html, reply_to). Professional-opened cases use template 1 with reply-to the professional."""
    pro = await case_professional(report_id)
    if pro:
        subject, html = professional_template(invitee_name, pro.get("name") or inviter_name, code, token)
        return subject, html, pro.get("email")
    subject, html = coparent_template(invitee_name, inviter_name, code, token)
    return subject, html, None


def cadence_for(doc: dict) -> dict:
    return {**DEFAULT_CADENCE, **(doc.get("invite_cadence") or {})}


async def run_invite_reminders() -> int:
    """Daily: for pending, unexpired invitations send reminder N when created_at + reminder_days[N] has passed (max_reminders cap, one per day)."""
    now = datetime.now(timezone.utc)
    sent = 0
    async for inv in db.invitations.find({"status": "pending"}, {"_id": 0}):
        created = _parse_iso(inv.get("created_at"))
        if not created:
            continue
        rep = await db.joint_reports.find_one({"id": inv["report_id"]}, {"invite_cadence": 1, "is_demo": 1, "joint_paused": 1})
        if not rep or rep.get("is_demo") or rep.get("joint_paused"):
            continue
        cad = cadence_for(rep)
        if created + timedelta(days=cad["expiry_days"]) < now:
            continue
        n = int(inv.get("reminders_sent") or 0)
        if n >= cad["max_reminders"] or n >= len(cad["reminder_days"]):
            continue
        if now < created + timedelta(days=cad["reminder_days"][n]):
            continue
        last = _parse_iso(inv.get("last_reminder_at"))
        if last and now - last < timedelta(hours=20):
            continue
        subject, html = reminder_template(inv.get("invitee_name", ""), inv["token"], n + 1)
        pro = await case_professional(inv["report_id"])
        try:
            await send_email(to=inv["invitee_email"], subject=subject, html=html, reply_to=(pro or {}).get("email"), case_id=inv["report_id"], kind="invitation_reminder", to_role=f"Parent {inv['role'].upper()}")
        except Exception:
            logger.warning("invite reminder not sent for invitation %s", inv["id"])
            continue
        await db.invitations.update_one({"id": inv["id"]}, {"$set": {"reminders_sent": n + 1, "last_reminder_at": now.isoformat()}})
        sent += 1
    return sent


class CadenceIn(BaseModel):
    reminder_days: list[int] = Field(default_factory=lambda: list(DEFAULT_CADENCE["reminder_days"]))
    max_reminders: int = DEFAULT_CADENCE["max_reminders"]


def build_router(get_current_user, get_joint_report_doc, log_access, is_pro) -> APIRouter:
    r = APIRouter()

    @r.get("/joint/reports/{rid}/invite-cadence")
    async def get_cadence(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can view invitation settings")
        pend = await db.invitations.find({"report_id": rid, "status": "pending"}, {"_id": 0, "role": 1, "reminders_sent": 1, "last_reminder_at": 1, "created_at": 1}).to_list(10)
        return {"cadence": cadence_for(doc), "defaults": DEFAULT_CADENCE, "pending": pend}

    @r.put("/joint/reports/{rid}/invite-cadence")
    async def set_cadence(rid: str, body: CadenceIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can change invitation settings")
        days = sorted({d for d in body.reminder_days if 1 <= d < INVITE_EXPIRY_DAYS})
        mx = max(0, min(body.max_reminders, len(days), 2))
        cad = {"reminder_days": days, "max_reminders": mx, "expiry_days": INVITE_EXPIRY_DAYS}
        await db.joint_reports.update_one({"id": rid}, {"$set": {"invite_cadence": cad}})
        await log_access(doc, user, f"Invitation reminder cadence set: days {days}, max {mx}", "invite_cadence")
        return {"cadence": cad, "id": str(uuid.uuid4())}

    return r
