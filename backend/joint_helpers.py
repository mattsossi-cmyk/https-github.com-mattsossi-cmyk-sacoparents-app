"""Joint case helpers shared by the joint, admin, cron and integration route modules."""

import uuid



import secrets

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from html import escape




from fastapi import HTTPException







from court_workflow import court_stage





from email_utils import send_email, EMAIL_FROM_NAME, MINIMAL_NOTIFICATIONS
from joint_engine import REDACTION_NOTICE
from core import db, logger, app_url, _parse_iso, invite_link, INVITE_EXPIRY_DAYS


def new_code():
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


CASE_STATUS_ORDER = ["DRAFT", "INVITED", "ONE_COMPLETE", "READY_FOR_ALIGNMENT", "REPORT_GENERATED", "CLOSED"]


def case_status(doc: dict) -> str:
    if doc.get("closed_at"):
        return "CLOSED"
    if doc.get("report_generated_at"):
        return "REPORT_GENERATED"
    done = sum(1 for r in ("a", "b") if doc.get("responses", {}).get(r))
    if done == 2:
        return "READY_FOR_ALIGNMENT"
    if done == 1:
        return "ONE_COMPLETE"
    return "INVITED" if doc.get("status") != "draft" else "DRAFT"


def report_role(doc, user_id):
    for role in ("a", "b"):
        p = doc["participants"].get(role) or {}
        if p.get("user_id") == user_id:
            return role
    return None


def can_view_report(doc, user_id):
    return (
        report_role(doc, user_id) is not None
        or doc.get("professional_id") == user_id
        or user_id in doc.get("shared_with", [])
    )


def _participants_public(doc: dict) -> dict:
    out = {}
    for r in ("a", "b"):
        p = doc["participants"][r]
        out[r] = {
            "name": p.get("name", ""),
            "accepted": bool(p.get("user_id")),
            "completed": bool(doc.get("responses", {}).get(r)),
            "imported": bool((doc.get("responses", {}).get(r) or {}).get("imported")),
        }
    return out


def _invitation_public(invitation: dict) -> dict:
    return {
        "id": invitation["id"],
        "code": invitation["code"],
        "link": invite_link(invitation["token"]),
        "invitee_email": invitation["invitee_email"],
        "status": invitation["status"],
    }




def invite_expired(inv: dict) -> bool:
    created = _parse_iso(inv.get("created_at"))
    if created is None:
        return False
    return created + timedelta(days=INVITE_EXPIRY_DAYS) < datetime.now(timezone.utc)


def _pending_public(pending: list) -> list:
    out = []
    for i in pending:
        created = i.get("created_at", "")
        expires_at = ""
        try:
            expires_at = (datetime.fromisoformat(created) + timedelta(days=INVITE_EXPIRY_DAYS)).isoformat()
        except ValueError:
            pass
        out.append({"id": i["id"], "role": i["role"], "invitee_email": i["invitee_email"], "invitee_name": i.get("invitee_name", ""), "status": i["status"], "created_at": created, "expires_at": expires_at, "expired": invite_expired(i)})
    return out


def joint_public(doc: dict, user: dict, invitation: dict | None = None, pending: list | None = None) -> dict:
    uid = user["_id"]
    role = report_role(doc, uid)
    out = {
        "id": doc["id"],
        "subject": doc["subject"],
        "subject_label": doc["subject_label"],
        "child_name": doc["child_name"],
        "status": doc["status"],
        "created_at": doc["created_at"],
        "my_role": role,
        "is_creator": doc.get("created_by") == uid,
        "professional_name": doc.get("professional_name"),
        "is_safety": bool(doc.get("is_safety")),
        "subjects": doc.get("subjects") or [doc["subject"]],
        "kind": doc.get("kind", "joint_report"),
        "shared_with_me": uid in doc.get("shared_with", []),
        "case_code": doc.get("case_code"),
        "case_status": case_status(doc),
        "closed_at": doc.get("closed_at"),
        "archived": bool(doc.get("archived")),
        "participants": _participants_public(doc),
        "is_demo": bool(doc.get("is_demo")),
    }
    if doc.get("case_reference") and doc.get("created_by") == uid:
        out["case_reference"] = doc["case_reference"]
    if doc.get("created_by") == uid:
        out["session_outcome"] = doc.get("session_outcome")
        out["court"] = doc.get("court")
        out["court_stage"] = court_stage(doc)
        out["court_submissions"] = doc.get("court_submissions") or []
    if role:
        my = doc.get("responses", {}).get(role)
        out["my_answers"] = my.get("answers") if my else None
    if doc.get("created_by") == uid:
        out["foundation_statements"] = [{"side": side, "parent": (doc.get("participants", {}).get(side) or {}).get("name") or f"Parent {side.upper()}", "title": s.get("title", "Foundation Statement"), "content": s.get("content", ""), "structured": bool(s.get("structured"))}
                                        for side in ("a", "b") for s in (doc.get("responses", {}).get(side) or {}).get("foundation") or []]
        out["safety_route"] = any((doc.get("responses", {}).get(s) or {}).get("safety_route") or (doc.get("safety_flags") or {}).get(s) for s in ("a", "b"))
        out["safety_case_id"] = doc.get("safety_case_id")
        if invitation:
            out["invitation"] = _invitation_public(invitation)
        if pending:
            out["pending_invitations"] = _pending_public(pending)
    if role:
        out["my_foundation_shared"] = bool((doc.get("responses", {}).get(role) or {}).get("foundation"))
    return out


@dataclass
class InviteSpec:
    report_id: str
    role: str
    invitee_name: str
    invitee_email: str
    inviter_name: str
    child_name: str
    subject_label: str
    code: str = ""
    via_professional: bool = False


def _invite_email_content(spec: InviteSpec, token: str) -> tuple[str, str]:
    link = invite_link(token)
    subject = "An invitation from SA CoParents" if MINIMAL_NOTIFICATIONS else "Invitation to Complete Your SA CoParents Assessment"
    closing = (
        "After both parents have completed the requested assessment, SA CoParents Align will prepare "
        "the Joint Alignment Report for the authorized professional."
        if spec.via_professional else
        "After both parents have completed the requested assessment, SA CoParents Align will prepare "
        "the Joint Alignment Report."
    )
    closing += f" {REDACTION_NOTICE}"
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(spec.invitee_name or 'there')},</p>"
        "<p>You have been invited to participate in an SA CoParents Joint Alignment Report regarding "
        f"<strong>{escape(spec.child_name)}</strong> ({escape(spec.subject_label)}), at the request of {escape(spec.inviter_name)}.</p>"
        "<p>Your private participation code is:</p>"
        f'<p><strong style="font-size:18px;letter-spacing:2px">{escape(spec.code)}</strong></p>'
        "<p>Please use the link below to complete your individual SA CoParents assessment.</p>"
        "<p>Your individual responses are completed privately. Your co-parent will complete their own "
        "assessment separately. The Joint Alignment process is designed to identify areas of shared "
        "understanding, differences in perspective, and issues that may benefit from further discussion.</p>"
        f'<p><a href="{link}" style="display:inline-block;background:#5B2A86;color:#ffffff;'
        'padding:12px 24px;text-decoration:none;border-radius:6px">Complete My Assessment</a></p>'
        f"<p>{closing}</p>"
        f'<table role="presentation" style="margin-top:8px"><tr><td style="vertical-align:top;padding-right:14px">'
        f'<img src="{app_url()}/api/verify/{escape(spec.code)}/qr.png" width="96" height="96" alt="QR code to verify this professional" style="display:block;border:1px solid #ddd;border-radius:6px"></td>'
        f'<td style="vertical-align:top;font-size:13px;color:#444">Want to confirm who sent this? Scan the code or visit '
        f'<a href="{app_url()}/verify?code={escape(spec.code)}" style="color:#5B2A86">{escape(app_url())}/verify</a> and enter case code <strong>{escape(spec.code)}</strong> '
        "to see the professional's approval and credential status.</td></tr></table>"
        "<p>Please do not forward this invitation or share your sign-in credentials.</p>"
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. If the button does not '
        "work, sign in and enter your participation code instead.</p></td></tr></table>"
    )
    return subject, html


async def send_invite_email(spec: InviteSpec, token: str):
    subject, html = _invite_email_content(spec, token)
    await send_email(to=spec.invitee_email, subject=subject, html=html, case_id=spec.report_id, kind="invitation", to_role=f"Parent {spec.role.upper()}")


async def create_invitation(spec: InviteSpec):
    iid = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    spec.invitee_email = spec.invitee_email.lower()
    code = spec.code or new_code()
    doc = {
        "id": iid,
        "report_id": spec.report_id,
        "role": spec.role,
        "invitee_name": spec.invitee_name.strip(),
        "invitee_email": spec.invitee_email,
        "inviter_name": spec.inviter_name,
        "token": token,
        "code": code,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if (await db.joint_reports.find_one({"id": spec.report_id}, {"joint_paused": 1}) or {}).get("joint_paused"):
        raise HTTPException(status_code=423, detail="This step isn't available right now. Your professional will follow up.")
    await db.invitations.insert_one(doc)
    try:
        await send_invite_email(spec, token)
    except Exception:
        logger.warning(f"Invitation email not sent to {spec.invitee_email}")
    return doc



async def get_joint_report_doc(rid, user):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or not can_view_report(doc, user["_id"]):
        raise HTTPException(status_code=404, detail="Joint report not found")
    return doc

def _actor_label(doc: dict, user: dict) -> str:
    if doc.get("created_by") == user["_id"] or doc.get("professional_id") == user["_id"]:
        return "Assigned professional"
    role = report_role(doc, user["_id"])
    if role:
        return f"Parent {'1' if role == 'a' else '2'}"
    return "Shared professional"
