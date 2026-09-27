"""Professional onboarding: admin invites by email + practice ZIP, credential requests/uploads, one-step acceptance."""
import secrets
import uuid
from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, EmailStr

from auth import get_current_user, public_user
from core import app_url, db, logger
from email_utils import EMAIL_FROM_NAME, send_email
from storage import ALLOWED, APP_NAME, MAX_UPLOAD, get_object, put_object

router = APIRouter()
CREDENTIAL_TYPES = ["Licensed Attorney (State Bar)", "LPC / LMFT / LCSW (Texas BHEC)", "Licensed Psychologist", "Certified Mediator", "Parenting Facilitator / Coordinator", "Other credential"]


class InviteIn(BaseModel):
    name: str
    email: EmailStr
    zip: str
    profession: str = ""


def _admin(user):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _btn(url: str, label: str) -> str:
    return f'<p style="margin:16px 0"><a href="{url}" style="background:#5B2A86;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block">{label}</a></p>'


def _wrap(body: str) -> str:
    return f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">{body}<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p></td></tr></table>'


async def _mail(to: str, subject: str, html: str) -> bool:
    try:
        await send_email(to=to, subject=subject, html=html, kind="pro_onboarding", to_role="Professional")
        return True
    except Exception as exc:
        logger.warning("onboarding email to %s failed: %s", to, exc)
        return False


async def _mail_detail(to: str, subject: str, html: str) -> dict:
    try:
        await send_email(to=to, subject=subject, html=html, kind="pro_onboarding", to_role="Professional")
        return {"email_sent": True, "email_error": ""}
    except HTTPException as exc:
        logger.warning("onboarding email to %s failed: %s", to, exc.detail)
        return {"email_sent": False, "email_error": str(exc.detail)}
    except Exception as exc:
        logger.warning("onboarding email to %s failed: %s", to, exc)
        return {"email_sent": False, "email_error": f"{type(exc).__name__}: {exc}"[:200]}


@router.post("/admin/email-health")
async def email_health(user=Depends(get_current_user)):
    """Admin-only: sends a real test email to the admin and reports which provider/key is configured and what happened."""
    import email_utils as eu
    _admin(user)
    cfg = {"resend_configured": bool(eu.RESEND_API_KEY and eu.RESEND_FROM_EMAIL), "resend_from": eu.RESEND_FROM_EMAIL or "", "emergent_email_key": bool(eu.EMAIL_KEY),
           "from_name": eu.EMAIL_FROM_NAME, "reply_to": eu.EMAIL_REPLY_TO or "", "app_url": app_url()}
    resend = {"attempted": cfg["resend_configured"], "ok": False, "status": None, "error": ""}
    if cfg["resend_configured"]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {eu.RESEND_API_KEY}"},
                                      json={"from": f"{eu.EMAIL_FROM_NAME} <{eu.RESEND_FROM_EMAIL}>", "to": [user["email"]], "subject": f"{eu.EMAIL_FROM_NAME} email health check",
                                            "html": _wrap(f"<p>Hi {escape(user.get('name', ''))},</p><p>This test confirms the custom-domain sender <strong>{escape(eu.RESEND_FROM_EMAIL)}</strong> can deliver mail from this deployment.</p>")})
            resend.update(ok=r.status_code < 300, status=r.status_code, error="" if r.status_code < 300 else r.text[:300])
        except Exception as exc:
            resend["error"] = f"{type(exc).__name__}: {exc}"[:300]
    fallback = {"attempted": not resend["ok"], "ok": False, "error": ""}
    if not resend["ok"]:
        try:
            await eu._post_email(eu._email_payload(user["email"], f"{eu.EMAIL_FROM_NAME} email health check (default sender)", _wrap("<p>This test confirms the default Align sender can deliver mail from this deployment.</p>"), None))
            fallback["ok"] = True
        except Exception as exc:
            fallback["error"] = f"{type(exc).__name__}: {getattr(getattr(exc, 'response', None), 'text', '') or exc}"[:300]
    hints = []
    if not cfg["resend_configured"]:
        hints.append("RESEND_API_KEY / RESEND_FROM_EMAIL are not set in this deployment's environment — custom-domain sending is off.")
    if resend["attempted"] and not resend["ok"]:
        hints.append("Resend rejected the send. Typical causes: domain not verified in the Resend dashboard (DNS records), a restricted/invalid API key, or FROM address on a different domain than the verified one.")
    if not cfg["emergent_email_key"]:
        hints.append("EMERGENT_EMAIL_KEY is missing — the default sender cannot be used.")
    if fallback["attempted"] and not fallback["ok"]:
        hints.append("Default sender also failed — check EMERGENT_EMAIL_KEY in the deployment environment.")
    return {"config": cfg, "resend": resend, "fallback": fallback, "delivered_via": "resend" if resend["ok"] else "emergent" if fallback["ok"] else "none", "sent_to": user["email"], "hints": hints}


def _invite_html(inv: dict, admin_name: str) -> str:
    url = f"{app_url()}/auth?mode=register&pi={inv['token']}"
    return _wrap(f"<p>Hi {escape(inv['name'])},</p><p>{escape(admin_name or 'The SA CoParents Align administrator')} has invited you to join <strong>{escape(EMAIL_FROM_NAME)}</strong> as a "
                 f"professional serving families near ZIP {escape(inv['zip'])}.</p><p>Create your account, enter your license or credential details, and our team will review and accept you.</p>"
                 + _btn(url, "Accept invitation & register") + f"<p>Your login email will be <strong>{escape(inv['email'])}</strong>.</p>")


@router.post("/admin/pro-invites")
async def create_invite(body: InviteIn, user=Depends(get_current_user)):
    _admin(user)
    email, z = body.email.lower(), body.zip.strip()[:10]
    if not body.name.strip() or len(z) < 5:
        raise HTTPException(status_code=400, detail="Name and a valid ZIP code are required")
    if await db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if await db.pro_invites.find_one({"email": email, "status": "invited"}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="This professional already has an open invitation — use Resend")
    inv = {"id": str(uuid.uuid4()), "token": secrets.token_urlsafe(24), "name": body.name.strip()[:120], "email": email, "zip": z, "profession": body.profession.strip()[:80],
           "status": "invited", "invited_by": user["_id"], "invited_by_name": user.get("name", ""), "created_at": _now(), "resent_at": None, "registered_at": None, "user_id": None}
    await db.pro_invites.insert_one(dict(inv))
    result = await _mail_detail(email, f"You're invited to join {EMAIL_FROM_NAME}", _invite_html(inv, user.get("name", "")))
    await db.pro_invites.update_one({"id": inv["id"]}, {"$set": {"email_sent": result["email_sent"], "email_error": result["email_error"], "last_email_at": _now()}})
    inv.update(result)
    return {k: v for k, v in inv.items() if k != "token"}


@router.get("/admin/pro-invites")
async def list_invites(user=Depends(get_current_user)):
    _admin(user)
    return await db.pro_invites.find({}, {"_id": 0, "token": 0}).sort("created_at", -1).to_list(300)


@router.post("/admin/pro-invites/{iid}/resend")
async def resend_invite(iid: str, user=Depends(get_current_user)):
    _admin(user)
    inv = await db.pro_invites.find_one({"id": iid, "status": "invited"}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Open invitation not found")
    retry = inv.get("email_sent") is False
    subject = f"You're invited to join {EMAIL_FROM_NAME}" if retry else f"Reminder: your invitation to {EMAIL_FROM_NAME}"
    result = await _mail_detail(inv["email"], subject, _invite_html(inv, user.get("name", "")))
    await db.pro_invites.update_one({"id": iid}, {"$set": {"resent_at": _now(), "email_sent": result["email_sent"], "email_error": result["email_error"], "last_email_at": _now()}})
    return {"ok": result["email_sent"], "retry": retry, **result}


@router.get("/admin/email-status")
async def email_status(user=Depends(get_current_user)):
    """Cheap, no-send sender status for the dashboard badge: config presence + last real send outcome."""
    import email_utils as eu
    _admin(user)
    last = await db.pro_invites.find_one({"last_email_at": {"$ne": None}}, {"_id": 0, "email_sent": 1, "email_error": 1, "last_email_at": 1}, sort=[("last_email_at", -1)])
    resend_ok, emergent_ok = bool(eu.RESEND_API_KEY and eu.RESEND_FROM_EMAIL), bool(eu.EMAIL_KEY)
    failed_count = await db.pro_invites.count_documents({"status": "invited", "email_sent": False})
    level = "red" if not (resend_ok or emergent_ok) or (last and last.get("email_sent") is False) else "amber" if not resend_ok else "green"
    label = {"green": f"Email sender ready · {eu.RESEND_FROM_EMAIL}", "amber": "Email via default Align sender (custom domain not configured)", "red": "Email sending is failing"}[level]
    return {"level": level, "label": label, "resend_configured": resend_ok, "resend_from": eu.RESEND_FROM_EMAIL or "", "emergent_configured": emergent_ok,
            "last_send": last, "failed_invites": failed_count}


@router.get("/auth/pro-invite/{token}")
async def invite_prefill(token: str):
    inv = await db.pro_invites.find_one({"token": token, "status": "invited"}, {"_id": 0, "name": 1, "email": 1, "zip": 1, "profession": 1})
    if not inv:
        raise HTTPException(status_code=404, detail="This invitation link is no longer valid")
    return {**inv, "credential_types": CREDENTIAL_TYPES}


# ---- credentials request / upload / acceptance ----
@router.post("/admin/professionals/{uid}/request-credentials")
async def request_credentials(uid: str, user=Depends(get_current_user)):
    _admin(user)
    pro = await db.users.find_one({"_id": uid, "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="Professional not found")
    await db.users.update_one({"_id": uid}, {"$set": {"credentials_requested_at": _now(), "credentials_requested_by": user["_id"]}})
    html = _wrap(f"<p>Hi {escape(pro.get('name') or 'there')},</p><p>To complete your {escape(EMAIL_FROM_NAME)} professional account, please upload a copy of your license or certification "
                 f"(PDF or image) so our team can verify your credentials.</p>" + _btn(f"{app_url()}/dashboard#credentials", "Upload my credentials") +
                 "<p>Your documents are stored securely and are visible only to SA CoParents Align administrators.</p>")
    return {"ok": await _mail(pro["email"], f"Action needed: upload your credentials — {EMAIL_FROM_NAME}", html)}


def _file_pub(f: dict) -> dict:
    return {k: f.get(k) for k in ("id", "original_filename", "content_type", "size", "created_at")}


@router.post("/me/credentials")
async def upload_credential(file: UploadFile = File(...), user=Depends(get_current_user)):
    if user.get("role") != "professional":
        raise HTTPException(status_code=403, detail="Professional accounts only")
    ct = (file.content_type or "").split(";")[0]
    if ct not in ALLOWED:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG or WebP files are accepted")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="File too large (10 MB max)")
    if await db.credential_files.count_documents({"user_id": user["_id"], "is_deleted": False}) >= 5:
        raise HTTPException(status_code=400, detail="Up to 5 credential documents")
    fid = str(uuid.uuid4())
    try:
        res = put_object(f"{APP_NAME}/credentials/{user['_id']}/{fid}.{ALLOWED[ct]}", data, ct)
    except Exception as exc:
        logger.warning("credential upload failed: %s", exc)
        raise HTTPException(status_code=502, detail="File storage is unavailable right now")
    rec = {"id": fid, "user_id": user["_id"], "storage_path": res["path"], "original_filename": (file.filename or "credential")[:200], "content_type": ct, "size": res.get("size", len(data)), "is_deleted": False, "created_at": _now()}
    await db.credential_files.insert_one(dict(rec))
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"credentials_uploaded_at": rec["created_at"]}})
    return _file_pub(rec)


@router.get("/me/credentials")
async def my_credentials(user=Depends(get_current_user)):
    files = [_file_pub(f) async for f in db.credential_files.find({"user_id": user["_id"], "is_deleted": False}, {"_id": 0})]
    return {"files": files, "requested_at": user.get("credentials_requested_at"), "credential_types": CREDENTIAL_TYPES}


@router.get("/admin/professionals/{uid}/credentials")
async def pro_credentials(uid: str, user=Depends(get_current_user)):
    _admin(user)
    return {"files": [_file_pub(f) async for f in db.credential_files.find({"user_id": uid, "is_deleted": False}, {"_id": 0})]}


@router.get("/credential-files/{fid}")
async def download_credential(fid: str, user=Depends(get_current_user)):
    rec = await db.credential_files.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
    if not rec or (rec["user_id"] != user["_id"] and user.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="File not found")
    data, ct = get_object(rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type") or ct, headers={"Content-Disposition": f'inline; filename="{rec["original_filename"]}"'})


@router.post("/admin/accept-professional/{uid}")
async def accept_professional(uid: str, user=Depends(get_current_user)):
    """Approve + mark credentials verified in one step, then notify."""
    _admin(user)
    now = _now()
    res = await db.users.update_one({"_id": uid, "role": "professional"}, {"$set": {"approved": True, "verification_level": "credentials_verified", "credentials_verified_at": now, "credentials_verified_by": user["_id"], "accepted_at": now},
                                                                          "$unset": {"declined": "", "declined_reason": ""}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Professional not found")
    pro = await db.users.find_one({"_id": uid})
    await db.pro_invites.update_one({"user_id": uid}, {"$set": {"status": "accepted", "accepted_at": now}})
    await _mail(pro["email"], f"You're accepted — {EMAIL_FROM_NAME}", _wrap(f"<p>Hi {escape(pro.get('name') or 'there')},</p><p>Your credentials have been verified and your professional account is accepted. "
                                                                          f"You can now open Joint Alignment Cases and invite parents from your dashboard.</p>" + _btn(f"{app_url()}/dashboard", "Go to my dashboard")))
    return {**public_user(pro), "credentials_verified_at": now}
