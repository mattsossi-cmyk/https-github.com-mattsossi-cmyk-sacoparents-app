"""Admin: professional/judge approvals, invitations and case archive/close."""
import os
import uuid



import secrets

from datetime import datetime, timezone, timedelta

from html import escape
from urllib.parse import quote



from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel, EmailStr









from pdf_report import build_closing_summary_pdf

from auth_utils import hash_password
from email_utils import send_email, send_email_detailed, EMAIL_FROM_NAME, FIXTURE_EMAIL_RE, RESEND_FROM_EMAIL
from core import BUILD_ID, db, logger, app_url, _pro_email_wrap
from auth import get_current_user, public_user, hash_code
from joint_helpers import case_status, _actor_label

router = APIRouter()


@router.post("/admin/email-test")
async def admin_email_test(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    provider_id, provider = await send_email_detailed(
        to=user["email"],
        subject=f"Delivery test - {EMAIL_FROM_NAME}",
        html=_pro_email_wrap(
            f"<p>Hi {escape(user.get('name') or 'there')},</p>"
            f"<p>This is a delivery test sent from {escape(EMAIL_FROM_NAME)} at {sent_at}. "
            "If you can read this, verification codes and invitations from this server can reach your inbox.</p>"
            "<p>If it landed in spam or junk, please mark it as safe so future codes arrive promptly.</p>"),
    )
    return {"ok": True, "to": user["email"], "provider_id": provider_id, "sent_at": sent_at, "build": BUILD_ID,
            "sender": f"{RESEND_FROM_EMAIL} via Resend" if provider == "resend" else "default sender (Resend not active — check API key / domain verification)"}


@router.get("/admin/professionals")
async def list_approved_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "approved": True}, {"password_hash": 0}).sort("name", 1).to_list(500)
    return [{**public_user(u), "profile": u.get("profile", {}), "credentials_verified_at": u.get("credentials_verified_at", ""), "invite_pending": bool(u.get("invite_pending")),
             "credentials_uploaded_at": u.get("credentials_uploaded_at"), "credentials_requested_at": u.get("credentials_requested_at")} for u in docs]


PROFESSIONS = ("Mediator", "Parenting Facilitator", "Parenting Coordinator", "Attorney", "Counselor / Therapist", "Custody Evaluator", "Other")


class AdminAddProIn(BaseModel):
    name: str
    email: EmailStr
    profession: str
    degrees: str = ""
    phone: str = ""
    organization: str = ""


@router.post("/admin/professionals")
async def admin_add_professional(body: AdminAddProIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    name, email = body.name.strip()[:120], body.email.lower()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if body.profession not in PROFESSIONS:
        raise HTTPException(status_code=400, detail="Choose a profession from the list")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    now = datetime.now(timezone.utc)
    doc = {"_id": str(uuid.uuid4()), "email": email, "name": name, "role": "professional", "approved": True, "verification_level": "credentials_pending",
           "password_hash": hash_password(secrets.token_urlsafe(32)), "created_at": now.isoformat(), "created_by_admin": user["_id"], "invite_pending": True,
           "profile": {"pro_role": body.profession, "degrees": body.degrees.strip()[:200], "phone": body.phone.strip()[:40], "organization": body.organization.strip()[:160],
                       "city": "", "state": "", "license_number": "", "website": ""}}
    await db.users.insert_one(doc)
    link_token = secrets.token_urlsafe(32)
    await db.password_resets.insert_one({"email": email, "code_hash": hash_code(secrets.token_urlsafe(16)), "link_hash": hash_code(link_token), "invite": True,
                                         "expires_at": now + timedelta(days=7), "created_at": now.isoformat()})
    url = f"{app_url()}/auth?mode=reset&rt={link_token}"
    html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif"><p>Hi {escape(name)},</p>'
            f'<p>{escape(user.get("name") or "The SA CoParents Align administrator")} has created your approved professional account on <strong>{escape(EMAIL_FROM_NAME)}</strong> '
            f'({escape(body.profession)}{", " + escape(body.degrees.strip()) if body.degrees.strip() else ""}).</p>'
            f'<p>Set your password to activate your account:</p>'
            f'<p style="margin:16px 0"><a href="{url}" style="background:#5B2A86;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block">Set my password</a></p>'
            f'<p>This link expires in 7 days. Your login email is <strong>{escape(email)}</strong>.</p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p></td></tr></table>')
    try:
        await send_email(to=email, subject=f"Your {EMAIL_FROM_NAME} professional account is ready", html=html)
        sent = True
    except HTTPException:
        logger.warning(f"Invite email not sent for {email}")
        sent = False
    return {**public_user(doc), "profile": doc["profile"], "invite_pending": True, "invite_sent": sent}


@router.post("/admin/professionals/{user_id}/resend-invite")
async def admin_resend_invite(user_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    target = await db.users.find_one({"_id": user_id, "role": "professional", "invite_pending": True})
    if not target:
        raise HTTPException(status_code=404, detail="No pending invitation for this professional")
    now = datetime.now(timezone.utc)
    link_token = secrets.token_urlsafe(32)
    await db.password_resets.delete_many({"email": target["email"]})
    await db.password_resets.insert_one({"email": target["email"], "code_hash": hash_code(secrets.token_urlsafe(16)), "link_hash": hash_code(link_token), "invite": True,
                                         "expires_at": now + timedelta(days=7), "created_at": now.isoformat()})
    url = f"{app_url()}/auth?mode=reset&rt={link_token}"
    await send_email(to=target["email"], subject=f"Reminder: set your {EMAIL_FROM_NAME} password",
                     html=(f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif"><p>Hi {escape(target.get("name") or "there")},</p>'
                           f'<p>Your approved professional account on {escape(EMAIL_FROM_NAME)} is waiting for you. Set your password to activate it:</p>'
                           f'<p style="margin:16px 0"><a href="{url}" style="background:#5B2A86;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block">Set my password</a></p>'
                           f'<p>This link expires in 7 days.</p></td></tr></table>'))
    return {"ok": True}


class VerifyIn(BaseModel):
    verified: bool = True


@router.post("/admin/verify-credentials/{user_id}")
async def verify_credentials(user_id: str, body: VerifyIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    now = datetime.now(timezone.utc).isoformat()
    update = (
        {"verification_level": "credentials_verified", "credentials_verified_at": now, "credentials_verified_by": user["_id"]}
        if body.verified else
        {"verification_level": "credentials_pending", "credentials_verified_at": "", "credentials_verified_by": ""}
    )
    res = await db.users.update_one({"_id": user_id, "role": "professional", "approved": True}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Approved professional not found")
    return {"ok": True, "credentials_verified": body.verified}


@router.get("/admin/pending-professionals")
async def list_pending_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "approved": False, "declined": {"$ne": True}}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    return [{**public_user(u), "profile": u.get("profile", {}), "created_at": u.get("created_at", ""), "verification_level": u.get("verification_level", "")} for u in docs]


@router.get("/admin/declined-professionals")
async def list_declined_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "declined": True}, {"password_hash": 0}).sort("declined_at", -1).to_list(200)
    return [{**public_user(u), "profile": u.get("profile", {}), "created_at": u.get("created_at", ""), "declined_at": u.get("declined_at", ""), "declined_reason": u.get("declined_reason", "")} for u in docs]


@router.post("/admin/reconsider-professional/{user_id}")
async def reconsider_professional(user_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    res = await db.users.update_one(
        {"_id": user_id, "role": "professional", "declined": True},
        {"$set": {"declined": False, "verification_level": "credentials_pending", "reconsidered_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Declined professional not found")
    return {"ok": True}


@router.post("/admin/approve-professional/{user_id}")
async def approve_professional(user_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    res = await db.users.update_one({"_id": user_id, "role": "professional"}, {"$set": {"approved": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Professional not found")
    pro = await db.users.find_one({"_id": user_id})
    if pro:
        try:
            await send_email(
                to=pro["email"],
                subject=f"Your professional account is approved - {EMAIL_FROM_NAME}",
                html=(
                    '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                    f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                    "<p>Your SA CoParents Align professional account has been approved. You can now create "
                    "Joint Alignment Cases and invite parents from your dashboard.</p>"
                    f'<p><a href="{app_url()}/dashboard" style="display:inline-block;background:#5B2A86;color:#ffffff;'
                    'padding:12px 24px;text-decoration:none;border-radius:6px">Open your dashboard</a></p>'
                    f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p>'
                    "</td></tr></table>"
                ),
            )
        except Exception:
            logger.warning(f"Approval email not sent to {pro['email']}")
    return {"ok": True}


class DeclineIn(BaseModel):
    reason: str = ""


class JudgeInviteIn(BaseModel):
    name: str
    email: EmailStr
    court_name: str = ""


@router.post("/admin/judges/invite")
async def admin_invite_judge(body: JudgeInviteIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    email = body.email.lower()
    if await db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="An account with that email already exists")
    now = datetime.now(timezone.utc).isoformat()
    inv = {"id": str(uuid.uuid4()), "name": body.name.strip()[:120], "email": email, "court_name": body.court_name.strip()[:160], "invited_by": user["_id"],
           "invited_by_name": user.get("name", ""), "created_at": now, "status": "sent"}
    await db.court_invites.update_one({"email": email}, {"$set": inv}, upsert=True)
    link = f"{app_url()}/auth?mode=register&court=1&email={quote(email)}"
    await send_email(
        to=email, subject=f"Invitation to the SA CoParents Align court portal - {inv['court_name'] or 'court access'}",
        html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
              f"<p>Dear {escape(inv['name'])},</p>"
              f"<p>{escape(user.get('name', 'SA CoParents'))} has invited you to the SA CoParents Align court portal{' for ' + escape(inv['court_name']) if inv['court_name'] else ''}. "
              "From your Court Dashboard you can refer co-parenting matters to approved professionals and receive the Joint Alignment Report together with the professional's "
              "Assessment Statement when they are submitted - read-only, timestamped and logged.</p>"
              f'<p><a href="{link}" style="color:#5B2A86">Create your court account</a></p>'
              "<p>Because this invitation was issued by SA CoParents, your account is activated as soon as you register with this email address.</p>"
              f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>'))
    return {"ok": True, "invite": {k: inv[k] for k in ("id", "name", "email", "court_name", "created_at", "status")}, "link": link}


@router.get("/admin/judges/invites")
async def admin_list_judge_invites(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.court_invites.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@router.get("/admin/judges")
async def admin_list_judges(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "judge", "declined": {"$ne": True}}, {"password_hash": 0}).sort("created_at", -1).to_list(300)
    return [{**public_user(d), "created_at": d.get("created_at"), "declined": False} for d in docs]


@router.post("/admin/judges/{user_id}/approve")
async def admin_approve_judge(user_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    res = await db.users.update_one({"_id": user_id, "role": "judge"}, {"$set": {"approved": True, "verification_level": "credentials_verified", "declined": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Court account not found")
    j = await db.users.find_one({"_id": user_id}, {"password_hash": 0})
    if not FIXTURE_EMAIL_RE.search(j["email"]):
        try:
            await send_email(to=j["email"], subject=f"Your court account is approved - {EMAIL_FROM_NAME}",
                             html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                   f"<p>Hi {escape(j.get('name', ''))},</p><p>Your SA CoParents Align court account has been approved. Court Packets addressed to {escape(j['email'])} now appear in your Court Dashboard.</p>"
                                   f'<p><a href="{app_url()}/court-dashboard" style="color:#5B2A86">Open the Court Dashboard</a></p></td></tr></table>'))
        except Exception:
            logger.warning("judge approval email not sent")
    return public_user(j)


@router.post("/admin/judges/{user_id}/decline")
async def admin_decline_judge(user_id: str, body: DeclineIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    reason = body.reason.strip()[:500]
    if not reason:
        raise HTTPException(status_code=400, detail="Please provide a brief reason")
    res = await db.users.update_one({"_id": user_id, "role": "judge"}, {"$set": {"approved": False, "declined": True, "declined_reason": reason,
                                                                                "declined_at": datetime.now(timezone.utc).isoformat(), "verification_level": "declined"}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Court account not found")
    return {"ok": True}


@router.post("/admin/decline-professional/{user_id}")
async def decline_professional(user_id: str, body: DeclineIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    reason = body.reason.strip()[:500]
    if not reason:
        raise HTTPException(status_code=400, detail="Please provide a brief reason for declining")
    res = await db.users.update_one(
        {"_id": user_id, "role": "professional", "approved": False},
        {"$set": {"declined": True, "declined_reason": reason, "declined_at": datetime.now(timezone.utc).isoformat(), "verification_level": "declined"}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pending professional not found")
    pro = await db.users.find_one({"_id": user_id})
    if pro:
        try:
            await send_email(
                to=pro["email"],
                subject=f"Update on your professional account request - {EMAIL_FROM_NAME}",
                html=(
                    '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                    f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                    "<p>Thank you for your interest in SA CoParents Align. We were unable to approve your professional account at this time.</p>"
                    f"<p><strong>Reason:</strong> {escape(reason)}</p>"
                    f"<p>If you believe this was in error or can provide additional credential information, reply to this email or contact {escape(os.environ['ADMIN_EMAIL'])}.</p>"
                    f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p>'
                    "</td></tr></table>"
                ),
            )
        except Exception:
            logger.warning(f"Decline email not sent to {pro['email']}")
    return {"ok": True}


@router.post("/admin/revoke-professional/{user_id}")
async def revoke_professional(user_id: str, body: DeclineIn, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if user_id == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot revoke your own access")
    reason = body.reason.strip()[:500]
    if not reason:
        raise HTTPException(status_code=400, detail="Please provide a brief reason for revoking approval")
    now = datetime.now(timezone.utc).isoformat()
    res = await db.users.update_one(
        {"_id": user_id, "role": "professional", "approved": True},
        {"$set": {"approved": False, "declined": True, "declined_reason": reason, "declined_at": now,
                  "revoked_at": now, "revoked_by": user["_id"], "verification_level": "declined"}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Approved professional not found")
    logger.info(f"Professional approval revoked for {user_id} by {user['_id']}: {reason}")
    return {"ok": True}


class ArchiveIn(BaseModel):
    archived: bool = True


@router.patch("/joint/reports/{rid}/archive")
async def archive_joint_report(rid: str, body: ArchiveIn, user=Depends(get_current_user)):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or (doc.get("created_by") != user["_id"] and doc.get("professional_id") != user["_id"]):
        raise HTTPException(status_code=404, detail="Report not found")
    await db.joint_reports.update_one({"id": rid}, {"$set": {"archived": body.archived, "archived_at": datetime.now(timezone.utc).isoformat() if body.archived else None}})
    return {"ok": True, "archived": body.archived}


class CloseIn(BaseModel):
    closed: bool = True
    note: str = ""


@router.patch("/joint/reports/{rid}/close")
async def close_joint_report(rid: str, body: CloseIn, user=Depends(get_current_user)):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or (doc.get("created_by") != user["_id"] and doc.get("professional_id") != user["_id"]):
        raise HTTPException(status_code=404, detail="Report not found")
    now = datetime.now(timezone.utc).isoformat()
    if body.closed:
        updates = {"closed_at": now, "closed_by": user["_id"], "closed_note": body.note.strip()[:500], "archived": True, "archived_at": now}
    else:
        updates = {"closed_at": None, "closed_by": None, "closed_note": "", "archived": False, "archived_at": None}
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    await db.access_events.insert_one({
        "report_id": rid, "kind": "lifecycle", "action": "Case closed" if body.closed else "Case reopened",
        "note": body.note.strip()[:500] if body.closed else "", "at": now,
        "by": user["_id"], "by_name": user.get("name", ""), "by_role": _actor_label(doc, user),
    })
    return {"ok": True, "closed": body.closed, "case_status": case_status({**doc, **updates})}


@router.get("/joint/reports/{rid}/closing-summary.pdf")
async def closing_summary_pdf(rid: str, user=Depends(get_current_user)):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or (doc.get("created_by") != user["_id"] and doc.get("professional_id") != user["_id"]):
        raise HTTPException(status_code=404, detail="Report not found")
    if not doc.get("closed_at"):
        raise HTTPException(status_code=400, detail="Close the case first to generate its closing summary")
    events = await db.access_events.find({"report_id": rid}, {"_id": 0}).sort("at", 1).to_list(500)
    closer = await db.users.find_one({"_id": doc.get("closed_by")}, {"name": 1}) if doc.get("closed_by") else None
    data = {
        **doc, "subject_label": doc.get("subject_label", "Joint Alignment Report"), "professional_name": user.get("name", ""),
        "closed_by_name": (closer or {}).get("name", ""),
        "view_count": sum(1 for e in events if e.get("kind") == "view"),
        "download_count": sum(1 for e in events if e.get("kind") == "download"),
        "lifecycle": [e for e in events if e.get("kind") == "lifecycle"],
    }
    return Response(content=build_closing_summary_pdf(data), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="closing-summary-{doc.get("case_code", rid[:8])}.pdf"'})
