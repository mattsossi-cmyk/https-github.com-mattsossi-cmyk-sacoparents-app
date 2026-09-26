"""Authentication, session cookies and account preferences."""
import os
import uuid

import hashlib
import re
import secrets

from datetime import datetime, timezone, timedelta

from html import escape


import jwt

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr











from auth_utils import JWT_ALGORITHM, jwt_secret, hash_password, verify_password, create_access_token, create_refresh_token
from email_utils import send_email, EMAIL_FROM_NAME, FIXTURE_EMAIL_RE
from core import db, logger, app_url, _parse_iso, PRO_ROLES

router = APIRouter()


def set_auth_cookies(response: Response, user_id: str, email: str):
    response.set_cookie(
        key="access_token", value=create_access_token(user_id, email),
        httponly=True, secure=True, samesite="none", max_age=1800, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=create_refresh_token(user_id),
        httponly=True, secure=True, samesite="none", max_age=604800, path="/",
    )


def public_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "email": u["email"],
        "name": u.get("name", ""),
        "role": u.get("role", "parent"),
        "approved": u.get("approved", True),
        "verification_level": u.get("verification_level", ""),
        "credentials_verified": u.get("verification_level") == "credentials_verified",
        "must_change_password": bool(u.get("must_change_password")),
        "profile": u.get("profile", {}),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user




def is_pro(user: dict) -> bool:
    return user.get("role") in PRO_ROLES


def require_approved_professional(user: dict, detail: str) -> None:
    if not is_pro(user):
        raise HTTPException(status_code=403, detail=detail)
    if not user.get("approved", True):
        raise HTTPException(status_code=403, detail="Your professional account is pending approval by SA CoParents. You will be able to create cases once your account is approved.")


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "professional"
    invite: str = ""
    agreements_accepted: bool = False
    phone: str = ""
    organization: str = ""
    pro_role: str = ""
    city: str = ""
    state: str = ""
    license_number: str = ""
    website: str = ""
    zip: str = ""
    credential_type: str = ""
    pro_invite: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


async def _validate_registration(body: RegisterIn, email: str, role: str) -> None:
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if role == "parent":
        raw = body.invite.strip()
        inv = await db.invitations.find_one({"status": "pending", "invitee_email": email, "$or": [{"token": raw}, {"code": raw.upper()}]}) if raw else None
        if not inv:
            raise HTTPException(status_code=403, detail="Parent accounts are created through a secure invitation from a professional. Please use the link or case code in your invitation email.")
    if role in ("professional", "judge") and not body.agreements_accepted:
        raise HTTPException(status_code=400, detail="Please accept the professional-use, confidentiality, privacy, and appropriate-use agreements to create a professional account.")
    if role == "judge" and not body.organization.strip() and not await db.court_invites.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="Please enter your court so SA CoParents can verify the account.")


def _professional_profile(body: RegisterIn) -> dict:
    return {
        "phone": body.phone.strip(),
        "organization": body.organization.strip(),
        "pro_role": body.pro_role.strip(),
        "city": body.city.strip(),
        "state": body.state.strip(),
        "license_number": body.license_number.strip(),
        "website": body.website.strip(),
        "zip": body.zip.strip()[:10],
        "credential_type": body.credential_type.strip()[:80],
    }


async def _notify_admin_new_professional(user: dict) -> None:
    try:
        await send_email(
            to=os.environ["ADMIN_EMAIL"],
            subject=f"New professional registration awaiting approval - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                "<p>A new professional account is awaiting approval:</p>"
                f"<p><strong>{escape(user['name'])}</strong><br/>{escape(user['email'])}</p>"
                f'<p><a href="{app_url()}/dashboard" style="color:#5B2A86">Open the admin dashboard to approve</a></p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Admin approval notification not sent for {user['email']}")


@router.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    role = body.role if body.role in ("parent", "professional", "judge") else "professional"
    await _validate_registration(body, email, role)
    uid = str(uuid.uuid4())
    user = {
        "_id": uid,
        "email": email,
        "name": body.name.strip(),
        "role": role,
        "approved": role == "parent",
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if role in ("professional", "judge"):
        user["verification_level"] = "credentials_pending"
        user["agreements_accepted_at"] = user["created_at"]
        user["profile"] = _professional_profile(body)
    if role == "judge":
        inv = await db.court_invites.find_one({"email": email})
        if inv:
            user["approved"] = True
            user["verification_level"] = "credentials_verified"
            user["invited_by"] = inv.get("invited_by")
            if not user["profile"].get("organization"):
                user["profile"]["organization"] = inv.get("court_name", "")
            await db.court_invites.update_one({"email": email}, {"$set": {"status": "registered", "registered_at": user["created_at"]}})
    if role == "professional" and body.pro_invite.strip():
        from pro_invites import consume_invite
        await consume_invite(body.pro_invite.strip(), user)
    await db.users.insert_one(user)
    if role in ("professional", "judge") and not FIXTURE_EMAIL_RE.search(email):
        await _notify_admin_new_professional(user)
    set_auth_cookies(response, uid, email)
    return public_user(user)


@router.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    identifier = f"{(request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or (request.client.host if request.client else 'unknown')}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {
                "$inc": {"count": 1},
                "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()},
            },
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    set_auth_cookies(response, user["_id"], email)
    return public_user(user)


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)


DIGEST_CHOICES = ("daily", "weekly", "off")


class PreferencesIn(BaseModel):
    digest_frequency: str | None = None
    weekly_summary: bool | None = None


def _prefs(user: dict) -> dict:
    return {"digest_frequency": user.get("digest_frequency") or "daily", "weekly_summary": user.get("weekly_summary", True)}


@router.get("/me/preferences")
async def get_preferences(user=Depends(get_current_user)):
    return _prefs(user)


@router.put("/me/preferences")
async def update_preferences(body: PreferencesIn, user=Depends(get_current_user)):
    update = {}
    if body.digest_frequency is not None:
        if body.digest_frequency not in DIGEST_CHOICES:
            raise HTTPException(status_code=400, detail="Choose daily, weekly, or off")
        update["digest_frequency"] = body.digest_frequency
    if body.weekly_summary is not None:
        update["weekly_summary"] = body.weekly_summary
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.users.update_one({"_id": user["_id"]}, {"$set": update})
    return {"ok": True, **_prefs({**user, **update})}


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    response.set_cookie(
        key="access_token", value=create_access_token(user["_id"], user["email"]),
        httponly=True, secure=True, samesite="none", max_age=1800, path="/",
    )
    return {"ok": True}


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    email: EmailStr | None = None
    code: str = ""
    token: str = ""
    new_password: str


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if user:
        recent = await db.password_resets.find_one({"email": email})
        if recent and (datetime.now(timezone.utc) - _parse_iso(recent.get("created_at"))).total_seconds() < 60:
            raise HTTPException(status_code=429, detail="A code was just sent. Please wait a minute before requesting another.")
        code = f"{secrets.randbelow(1000000):06d}"
        link_token = secrets.token_urlsafe(32)
        await db.password_resets.delete_many({"email": email})
        await db.password_resets.insert_one({
            "email": email,
            "code_hash": hash_code(code),
            "link_hash": hash_code(link_token),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        reset_url = f"{app_url()}/auth?mode=reset&rt={link_token}"
        name = user.get("name") or "there"
        subject = f"Your {EMAIL_FROM_NAME} verification code"
        html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;'
                f'font-family:Arial,sans-serif">'
                f'<p>Hi {escape(name)},</p>'
                f'<p>Use this verification code to set a new password for your '
                f'{escape(EMAIL_FROM_NAME)} account:</p>'
                f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px;margin:24px 0">{code}</p>'
                f'<p>Or skip the code and reset in one click:</p>'
                f'<p style="margin:16px 0"><a href="{reset_url}" style="background:#5B2A86;color:#fff;padding:12px 20px;'
                f'border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block">Reset my password</a></p>'
                f'<p>The code and link expire in 15 minutes and can be used once. If you did not request a password reset, '
                f'you can ignore this email.</p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never '
                f'ask for your password by email.</p></td></tr></table>')
        try:
            await send_email(to=email, subject=subject, html=html)
        except HTTPException as e:
            logger.warning(f"Password-reset email not sent for {email}")
            await db.password_resets.delete_many({"email": email})
            if e.status_code == 503:
                raise HTTPException(status_code=503, detail="We couldn't send your verification code right now because our email service is busy. Please try again in a few minutes.")
            raise HTTPException(status_code=502, detail="We couldn't send your verification code. Please try again shortly or contact support.")
    return {"ok": True, "detail": "If an account exists for that email, a verification code is on its way."}


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/auth/change-password")
async def change_password(body: ChangePasswordIn, user=Depends(get_current_user)):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="Choose a password different from your temporary one")
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(body.new_password), "password_reset_by_user": True, "password_changed_at": datetime.now(timezone.utc).isoformat()},
         "$unset": {"must_change_password": ""}},
    )
    return {"ok": True}



@router.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    token = body.token.strip()
    if token:
        doc = await db.password_resets.find_one({"link_hash": hash_code(token)})
    elif body.email:
        doc = await db.password_resets.find_one({"email": body.email.lower()})
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    email = doc["email"]
    expires = doc["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        await db.password_resets.delete_many({"email": email})
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if not token and doc["code_hash"] != hash_code(body.code.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(body.new_password), "password_reset_by_user": True}, "$unset": {"must_change_password": "", "invite_pending": ""}})
    await db.password_resets.delete_many({"email": email})
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{re.escape(email)}$"}})
    return {"ok": True}
