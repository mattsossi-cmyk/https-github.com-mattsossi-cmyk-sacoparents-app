from dotenv import load_dotenv, dotenv_values
from pathlib import Path

load_dotenv()  # platform/Kubernetes env vars take precedence

# The preview supervisor injects a stale APP_URL; the .env file carries the correct
# value in preview and the platform-managed value in production.
_APP_URL_FILE = dotenv_values(Path(__file__).resolve().parent / ".env").get("APP_URL")

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

import jwt
import hashlib
import re
import secrets
from html import escape

import asyncio
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr

from assessment_data import ASSESSMENT_TYPES, ORDERED_TYPE_KEYS, SCALE, demo_payload
from report_engine import generate_report
from joint_data import SUBJECTS, ORDERED_SUBJECT_KEYS, QUESTIONS, CONFIDENTIALITY_NOTICE, SAFETY_SUBJECT_KEYS, AGREEMENT_AREAS
from joint_engine import generate_joint_report, generate_agreement, sample_mediation_report, sample_report, sample_list
from pdf_report import build_joint_pdf, build_agreement_pdf, build_case_pdf, build_complete_pdf, build_methodology_pdf, verify_qr_png
from complete_engine import build_complete_report
from auth_utils import JWT_ALGORITHM, jwt_secret, hash_password, verify_password, create_access_token, create_refresh_token
from email_utils import send_email, EMAIL_FROM_NAME, FIXTURE_EMAIL_RE

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api = APIRouter(prefix="/api")
BUILD_ID = "2026-09-09.5"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WEBHOOK_CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]

EXTERNAL_APP_URL = os.environ["SACOPARENTS_APP_URL"].rstrip("/")
INTEGRATION_SECRET = os.environ["INTEGRATION_SHARED_SECRET"]
APP_ASSESSMENT_URL = os.environ.get("SACOPARENTS_APP_ASSESSMENT_URL", "").rstrip("/")


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


PRO_ROLES = ("professional", "admin")


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
    if role == "professional" and not body.agreements_accepted:
        raise HTTPException(status_code=400, detail="Please accept the professional-use, confidentiality, privacy, and appropriate-use agreements to create a professional account.")


def _professional_profile(body: RegisterIn) -> dict:
    return {
        "phone": body.phone.strip(),
        "organization": body.organization.strip(),
        "pro_role": body.pro_role.strip(),
        "city": body.city.strip(),
        "state": body.state.strip(),
        "license_number": body.license_number.strip(),
        "website": body.website.strip(),
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


@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    role = body.role if body.role in ("parent", "professional") else "professional"
    await _validate_registration(body, email, role)
    uid = str(uuid.uuid4())
    user = {
        "_id": uid,
        "email": email,
        "name": body.name.strip(),
        "role": role,
        "approved": role != "professional",
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if role == "professional":
        user["verification_level"] = "credentials_pending"
        user["agreements_accepted_at"] = user["created_at"]
        user["profile"] = _professional_profile(body)
    await db.users.insert_one(user)
    if role == "professional" and not FIXTURE_EMAIL_RE.search(email):
        await _notify_admin_new_professional(user)
    set_auth_cookies(response, uid, email)
    return public_user(user)


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    identifier = f"{request.client.host if request.client else 'unknown'}:{email}"
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


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)


DIGEST_CHOICES = ("daily", "weekly", "off")


class PreferencesIn(BaseModel):
    digest_frequency: str | None = None
    weekly_summary: bool | None = None


def _prefs(user: dict) -> dict:
    return {"digest_frequency": user.get("digest_frequency") or "daily", "weekly_summary": user.get("weekly_summary", True)}


@api.get("/me/preferences")
async def get_preferences(user=Depends(get_current_user)):
    return _prefs(user)


@api.put("/me/preferences")
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


@api.post("/auth/refresh")
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
    email: EmailStr
    code: str
    new_password: str


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if user:
        recent = await db.password_resets.find_one({"email": email})
        if recent and (datetime.now(timezone.utc) - _parse_iso(recent.get("created_at"))).total_seconds() < 60:
            raise HTTPException(status_code=429, detail="A code was just sent. Please wait a minute before requesting another.")
        code = f"{secrets.randbelow(1000000):06d}"
        await db.password_resets.delete_many({"email": email})
        await db.password_resets.insert_one({
            "email": email,
            "code_hash": hash_code(code),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        name = user.get("name") or "there"
        subject = f"Your {EMAIL_FROM_NAME} verification code"
        html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;'
                f'font-family:Arial,sans-serif">'
                f'<p>Hi {escape(name)},</p>'
                f'<p>Use this verification code to set a new password for your '
                f'{escape(EMAIL_FROM_NAME)} account:</p>'
                f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px;margin:24px 0">{code}</p>'
                f'<p>This code expires in 10 minutes. If you did not request a password reset, '
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


@api.post("/auth/change-password")
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



@api.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    email = body.email.lower()
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    doc = await db.password_resets.find_one({"email": email})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    expires = doc["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        await db.password_resets.delete_many({"email": email})
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if doc["code_hash"] != hash_code(body.code.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(body.new_password), "password_reset_by_user": True}, "$unset": {"must_change_password": ""}})
    await db.password_resets.delete_many({"email": email})
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{re.escape(email)}$"}})
    return {"ok": True}


@api.get("/assessment-types")
async def list_types():
    return [
        {
            "key": k,
            "title": ASSESSMENT_TYPES[k]["title"],
            "description": ASSESSMENT_TYPES[k]["description"],
            "topic_count": len(ASSESSMENT_TYPES[k]["topics"]),
        }
        for k in ORDERED_TYPE_KEYS
    ]


@api.get("/assessment-types/{key}")
async def get_type(key: str):
    cfg = ASSESSMENT_TYPES.get(key)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown assessment type")
    return {
        "key": cfg["key"],
        "title": cfg["title"],
        "description": cfg["description"],
        "central_question": cfg["central_question"],
        "scale": SCALE,
        "shared_goal_options": cfg["shared_goal_options"],
        "topics": [{"key": t["key"], "label": t["label"], "question": t["question"]} for t in cfg["topics"]],
    }


def case_public(c: dict) -> dict:
    return {
        "id": c["id"],
        "type": c["type"],
        "type_title": ASSESSMENT_TYPES[c["type"]]["title"],
        "child_name": c.get("child_name", ""),
        "parent_a_name": c.get("parent_a_name", "Parent A"),
        "parent_b_name": c.get("parent_b_name", "Parent B"),
        "has_a": bool(c.get("responses", {}).get("a")),
        "has_b": bool(c.get("responses", {}).get("b")),
        "is_demo": c.get("is_demo", False),
        "created_at": c["created_at"],
    }


class CaseIn(BaseModel):
    type: str
    child_name: str = ""
    parent_a_name: str = "Parent A"
    parent_b_name: str = "Parent B"


class ResponsesIn(BaseModel):
    answers: dict
    primary_concern: str = ""
    goals: list[str] = []


@api.post("/cases")
async def create_case(body: CaseIn, user=Depends(get_current_user)):
    if body.type not in ASSESSMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unknown assessment type")
    cid = str(uuid.uuid4())
    doc = {
        "id": cid,
        "user_id": user["_id"],
        "type": body.type,
        "child_name": body.child_name.strip(),
        "parent_a_name": body.parent_a_name.strip() or "Parent A",
        "parent_b_name": body.parent_b_name.strip() or "Parent B",
        "responses": {},
        "is_demo": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cases.insert_one(doc)
    return case_public(doc)


@api.get("/cases")
async def list_cases(user=Depends(get_current_user)):
    cases = await db.cases.find({"user_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [case_public(c) for c in cases]


async def get_owned_case(case_id: str, user: dict) -> dict:
    c = await db.cases.find_one({"id": case_id, "user_id": user["_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return c


@api.get("/cases/{case_id}")
async def get_case(case_id: str, user=Depends(get_current_user)):
    return case_public(await get_owned_case(case_id, user))


@api.put("/cases/{case_id}/responses/{parent}")
async def save_responses(case_id: str, parent: str, body: ResponsesIn, user=Depends(get_current_user)):
    if parent not in ("a", "b"):
        raise HTTPException(status_code=400, detail="Parent must be 'a' or 'b'")
    c = await get_owned_case(case_id, user)
    cfg = ASSESSMENT_TYPES[c["type"]]
    valid_keys = {t["key"] for t in cfg["topics"]}
    answers = {k: v for k, v in body.answers.items() if k in valid_keys and v in SCALE}
    if set(answers.keys()) != valid_keys:
        raise HTTPException(status_code=400, detail="All questions must be answered")
    payload = {
        "answers": answers,
        "primary_concern": body.primary_concern.strip(),
        "goals": body.goals,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cases.update_one({"id": case_id}, {"$set": {f"responses.{parent}": payload, "is_demo": False}})
    c = await get_owned_case(case_id, user)
    return case_public(c)


@api.post("/cases/{case_id}/demo")
async def fill_demo(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    demo = demo_payload(c["type"])
    await db.cases.update_one(
        {"id": case_id},
        {
            "$set": {
                "responses.a": {**demo["a"], "completed_at": datetime.now(timezone.utc).isoformat()},
                "responses.b": {**demo["b"], "completed_at": datetime.now(timezone.utc).isoformat()},
                "child_name": c.get("child_name") or demo["child_name"],
                "is_demo": True,
            }
        },
    )
    return case_public(await get_owned_case(case_id, user))


@api.get("/cases/{case_id}/report")
async def get_report(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    if not (c.get("responses", {}).get("a") and c.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Both parents must complete the assessment before the report can be generated")
    return generate_report(c)


@api.get("/cases/{case_id}/pdf")
async def case_report_pdf(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    if not (c.get("responses", {}).get("a") and c.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Both parents must complete the assessment before the PDF can be generated")
    child = re.sub(r"[^a-z0-9-]", "", (c.get("child_name") or "child").lower().replace(" ", "-")) or "child"
    return Response(
        content=build_case_pdf(generate_report(c)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="alignment-report-{child}.pdf"'},
    )


@api.delete("/cases/{case_id}")
async def delete_case(case_id: str, user=Depends(get_current_user)):
    result = await db.cases.delete_one({"id": case_id, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"ok": True}


ADMIN_PROFILE = {
    "name": "Matt Sossi",
    "pro_role": "Attorney, Family Law Mediator, Parent Facilitator & Amicus Attorney",
    "organization": "Law Office of Matt Sossi",
    "address": "16607 Blanco #703",
    "city": "San Antonio",
    "state": "Texas 78232",
    "phone": "210-224-1667",
    "license_number": "Texas Attorney",
}

SEEDED_PROFESSIONALS = [
    {
        "email": "joy@bsossi.com",
        "name": "Joy Curbow, MS",
        "password_env": "JOY_TEMP_PASSWORD",
        "profile": {
            "pro_role": "Family Law Mediator",
            "organization": "Law Office of Matt Sossi",
            "address": "16607 Blanco #703",
            "city": "San Antonio",
            "state": "Texas 78232",
            "phone": "210-224-1667",
            "license_number": "",
        },
    },
]


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return
    existing = await db.users.find_one({"email": admin_email.lower()})
    if existing is None:
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "email": admin_email.lower(),
            "name": ADMIN_PROFILE["name"],
            "role": "admin",
            "approved": True,
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not existing.get("password_reset_by_user") and not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )
        await db.login_attempts.delete_many({"identifier": {"$regex": f":{admin_email.lower()}$"}})
    if not (existing or {}).get("profile", {}).get("pro_role"):
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"name": ADMIN_PROFILE["name"], "approved": True, "verification_level": "credentials_verified",
                      "credentials_verified_at": datetime.now(timezone.utc).isoformat(),
                      "profile": {k: v for k, v in ADMIN_PROFILE.items() if k != "name"}}},
        )


async def seed_professionals():
    for spec in SEEDED_PROFESSIONALS:
        temp_password = os.environ.get(spec["password_env"])
        if not temp_password or await db.users.find_one({"email": spec["email"]}):
            continue
        now = datetime.now(timezone.utc).isoformat()
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "email": spec["email"],
            "name": spec["name"],
            "role": "professional",
            "approved": True,
            "approved_at": now,
            "verification_level": "credentials_verified",
            "credentials_verified_at": now,
            "profile": spec["profile"],
            "must_change_password": True,
            "password_hash": hash_password(temp_password),
            "created_at": now,
        })


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.cases.create_index("user_id")
    await db.joint_reports.create_index("created_by")
    await db.invitations.create_index("code")
    await db.invitations.create_index("token")
    await db.account_links.create_index("user_id", unique=True)
    await seed_admin()
    await seed_professionals()


# ---------- Joint Report Builder ----------

class JointReportIn(BaseModel):
    subject: str
    custom_subject: str = ""
    subjects: list[str] = []
    child_name: str
    co_parent_name: str
    co_parent_email: EmailStr
    mediator_email: EmailStr | None = None


class ProJointReportIn(BaseModel):
    subject: str
    custom_subject: str = ""
    subjects: list[str] = []
    child_name: str
    parent_a_name: str
    parent_a_email: EmailStr
    parent_b_name: str
    parent_b_email: EmailStr
    case_reference: str = ""


class JointResponsesIn(BaseModel):
    answers: dict
    foundation: list | None = None


class AcceptIn(BaseModel):
    code: str


class ShareIn(BaseModel):
    email: EmailStr


class PatchInvitationIn(BaseModel):
    subject: str
    custom_subject: str = ""


def app_url():
    return (_APP_URL_FILE or os.environ["APP_URL"]).rstrip("/")


def new_code():
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


SUBJECT_CODE_PREFIX = {
    "communication": "COM", "schedule": "SCH", "education": "EDU", "medical": "MED",
    "psychological": "PSY", "activities": "ACT", "transitions": "TRA", "decision_making": "DEC",
    "holidays": "HOL", "technology": "TEC", "routine": "ROU", "co_parenting": "COP",
    "child_needs": "CHD", "special_needs": "SPN", "safety": "SAF", "risk": "RSK",
    "safety_communication": "SCO", "safeguards": "SGR", "mediation": "MDN", "custom": "CUS",
    "multi": "ALN",
}


def new_case_code(subject, kind="joint_report"):
    prefix = "AGR" if kind == "agreement" else SUBJECT_CODE_PREFIX.get(subject, "ALN")
    return f"SA-{prefix}-{secrets.randbelow(900000) + 100000}"


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
        "link": f"{app_url()}/join/{invitation['token']}",
        "invitee_email": invitation["invitee_email"],
        "status": invitation["status"],
    }


INVITE_EXPIRY_DAYS = 14
INVITE_EXPIRING_SOON_DAYS = 4


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
        "archived": bool(doc.get("archived")),
        "participants": _participants_public(doc),
    }
    if doc.get("case_reference") and doc.get("created_by") == uid:
        out["case_reference"] = doc["case_reference"]
    if role:
        my = doc.get("responses", {}).get(role)
        out["my_answers"] = my["answers"] if my else None
    if doc.get("created_by") == uid:
        if invitation:
            out["invitation"] = _invitation_public(invitation)
        if pending:
            out["pending_invitations"] = _pending_public(pending)
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
    link = f"{APP_ASSESSMENT_URL}/assessment?invite={token}" if APP_ASSESSMENT_URL else f"{app_url()}/join/{token}"
    subject = "Invitation to Complete Your SA CoParents Assessment"
    closing = (
        "After both parents have completed the requested assessment, SA CoParents Align will prepare "
        "the Joint Alignment Report for the authorized professional."
        if spec.via_professional else
        "After both parents have completed the requested assessment, SA CoParents Align will prepare "
        "the Joint Alignment Report."
    )
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
    await send_email(to=spec.invitee_email, subject=subject, html=html)


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
    await db.invitations.insert_one(doc)
    try:
        await send_invite_email(spec, token)
    except Exception:
        logger.warning(f"Invitation email not sent to {spec.invitee_email}")
    return doc


@api.get("/joint/config")
async def joint_config():
    return {
        "subjects": [{"key": k, "label": SUBJECTS[k]["label"]} for k in ORDERED_SUBJECT_KEYS],
        "questions": [{"key": k, "area": a, "question": q} for k, a, q in QUESTIONS],
        "confidentiality_notice": CONFIDENTIALITY_NOTICE,
        "agreement_areas": [{"key": k, "label": l, "question": q} for k, l, q in AGREEMENT_AREAS],
    }


def _multi_label(subject_keys: list) -> str:
    label = "Customized Report: " + " + ".join(SUBJECTS[k]["label"] for k in subject_keys[:3])
    return label + ("…" if len(subject_keys) > 3 else "")


def resolve_subjects(body_subject: str, body_subjects: list, custom: str) -> tuple:
    subject_keys = body_subjects or [body_subject]
    if not subject_keys or any(k not in SUBJECTS for k in subject_keys):
        raise HTTPException(status_code=400, detail="Unknown subject")
    if len(subject_keys) > 1:
        return "multi", subject_keys, _multi_label(subject_keys)
    subject = subject_keys[0]
    label = (custom.strip() or "Custom Subject") if subject == "custom" else SUBJECTS[subject]["label"]
    return subject, subject_keys, label


async def _resolve_mediator(body: JointReportIn, user: dict) -> dict | None:
    if not body.mediator_email:
        raise HTTPException(status_code=400, detail="Family violence reports are prepared with a third-party mediator. Please provide the mediator's email.")
    mediator = await db.users.find_one({"email": body.mediator_email.lower(), "role": "professional"})
    if not mediator:
        raise HTTPException(status_code=404, detail="No professional account found with that email. Ask your mediator to create a free professional account first.")
    if mediator["_id"] == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot designate yourself as the mediator.")
    return mediator


async def _notify_mediator(mediator: dict, user: dict, doc: dict, label: str) -> None:
    try:
        await send_email(
            to=mediator["email"],
            subject=f"Family violence Joint Report facilitation requested - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(mediator.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has requested your third-party "
                f"facilitation of a family-violence Joint Report regarding "
                f"<strong>{escape(doc['child_name'])}</strong> ({escape(label)}).</p>"
                "<p>Both parents' individual responses remain confidential and are not shared between the "
                "parties. You will see the completed comparison once both parents finish.</p>"
                f'<p><a href="{app_url()}/dashboard" style="color:#5B2A86">Open your dashboard</a></p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Mediator notification not sent to {mediator['email']}")


@api.post("/joint/reports")
async def create_joint_report(body: JointReportIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Joint reports are initiated by an authorized professional. Parents participate through a secure invitation.")
    subject, subject_keys, label = resolve_subjects(body.subject, body.subjects, body.custom_subject)
    is_safety = all(k in SAFETY_SUBJECT_KEYS for k in subject_keys)
    mediator = await _resolve_mediator(body, user) if is_safety else None
    rid = str(uuid.uuid4())
    case_code = new_case_code(subject)
    doc = {
        "id": rid,
        "subject": subject,
        "subjects": subject_keys,
        "subject_label": label,
        "is_safety": is_safety,
        "case_code": case_code,
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "parent",
        "professional_id": mediator["_id"] if mediator else None,
        "professional_name": (mediator.get("name") or mediator["email"]) if mediator else None,
        "shared_with": [],
        "participants": {
            "a": {"user_id": user["_id"], "name": user.get("name", ""), "email": user["email"]},
            "b": {"user_id": None, "name": body.co_parent_name.strip(), "email": body.co_parent_email.lower()},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.joint_reports.insert_one(doc)
    inv = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.co_parent_name, invitee_email=body.co_parent_email, inviter_name=user.get("name", "Your co-parent"), child_name=doc["child_name"], subject_label=label, code=case_code))
    if mediator:
        await _notify_mediator(mediator, user, doc, label)
    return {**joint_public(doc, user), "invitation": {"id": inv["id"], "code": inv["code"], "link": f"{app_url()}/join/{inv['token']}", "invitee_email": inv["invitee_email"], "status": "pending"}}


@api.post("/joint/reports/professional")
async def create_pro_joint_report(body: ProJointReportIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Only professional accounts can create reports for two parents")
    subject, subject_keys, label = resolve_subjects(body.subject, body.subjects, body.custom_subject)
    rid = str(uuid.uuid4())
    case_code = new_case_code(subject)
    doc = {
        "id": rid,
        "subject": subject,
        "subjects": subject_keys,
        "subject_label": label,
        "is_safety": all(k in SAFETY_SUBJECT_KEYS for k in subject_keys),
        "case_code": case_code,
        "case_reference": body.case_reference.strip()[:120],
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": body.parent_a_name.strip(), "email": body.parent_a_email.lower()},
            "b": {"user_id": None, "name": body.parent_b_name.strip(), "email": body.parent_b_email.lower()},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.joint_reports.insert_one(doc)
    inv_a = await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=body.parent_a_name, invitee_email=body.parent_a_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label=label, code=case_code, via_professional=True))
    inv_b = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.parent_b_name, invitee_email=body.parent_b_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label=label, code=case_code, via_professional=True))
    return {**joint_public(doc, user), "invitations": [
        {"role": i["role"], "code": i["code"], "link": f"{app_url()}/join/{i['token']}", "invitee_email": i["invitee_email"], "invitee_name": i["invitee_name"], "status": "pending"}
        for i in (inv_a, inv_b)
    ]}


@api.get("/joint/reports")
async def list_joint_reports(user=Depends(get_current_user)):
    uid = user["_id"]
    docs = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    own_ids = [d["id"] for d in docs if d.get("created_by") == uid]
    inv_map = {}
    if own_ids:
        async for i in db.invitations.find({"report_id": {"$in": own_ids}, "status": "pending"}, {"_id": 0}):
            inv_map.setdefault(i["report_id"], []).append(i)
    return [
        joint_public(
            d, user,
            (inv_map.get(d["id"]) or [None])[0] if d.get("created_by") == uid else None,
            pending=inv_map.get(d["id"]) if d.get("created_by") == uid else None,
        )
        for d in docs
    ]


def _verify_info(doc: dict) -> dict | None:
    code = doc.get("case_code")
    if not code:
        return None
    return {"case_code": code, "url": f"{app_url()}/verify?code={code}"}


async def _report_professional(doc: dict) -> dict | None:
    pid = doc.get("professional_id") or doc.get("created_by")
    pro = await db.users.find_one({"_id": pid, "role": "professional"}, {"name": 1, "verification_level": 1}) if pid else None
    if not pro:
        return None
    return {"name": pro.get("name", ""), "credentials_verified": pro.get("verification_level") == "credentials_verified"}


async def get_joint_report_doc(rid, user):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or not can_view_report(doc, user["_id"]):
        raise HTTPException(status_code=404, detail="Joint report not found")
    return doc


@api.get("/joint/reports/{rid}")
async def get_joint_report(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    pend = await db.invitations.find({"report_id": rid, "status": "pending"}, {"_id": 0}).to_list(10)
    return joint_public(doc, user, pend[0] if pend else None, pending=pend)


def _foundation_payload(body: JointResponsesIn) -> list:
    return [
        {"title": str(s.get("title", "Foundation Statement"))[:120], "content": str(s.get("content", ""))[:5000]}
        for s in (body.foundation or []) if isinstance(s, dict)
    ]


def _validated_answers(doc: dict, body: JointResponsesIn) -> dict:
    valid = {k for k, _, _ in AGREEMENT_AREAS} if doc.get("kind") == "agreement" else {k for k, _, _ in QUESTIONS}
    answers = {k: (body.answers.get(k) or "").strip() for k in valid}
    if any(not v for v in answers.values()):
        raise HTTPException(status_code=400, detail="Please answer all questions")
    payload = {"answers": answers, "completed_at": datetime.now(timezone.utc).isoformat()}
    if doc.get("kind") == "agreement" and body.foundation:
        payload["foundation"] = _foundation_payload(body)
    return payload


@api.put("/joint/reports/{rid}/responses")
async def save_joint_responses(rid: str, body: JointResponsesIn, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    role = report_role(doc, user["_id"])
    if role is None:
        raise HTTPException(status_code=403, detail="Only invited parents can submit responses")
    payload = _validated_answers(doc, body)
    updates = {f"responses.{role}": payload}
    other = "b" if role == "a" else "a"
    if doc.get("responses", {}).get(other):
        updates["status"] = "ready"
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    doc = await get_joint_report_doc(rid, user)
    return joint_public(doc, user)


@api.get("/joint/reports/{rid}/report")
async def get_joint_report_output(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="The Joint Report becomes available when both parents have completed their assessments")
    if doc.get("kind") == "agreement":
        return generate_agreement(doc)
    return generate_joint_report(doc)


@api.get("/joint/reports/{rid}/pdf")
async def joint_report_pdf(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="The Joint Report PDF becomes available when both parents have completed their assessments")
    child = re.sub(r"[^a-z0-9-]", "", (doc.get("child_name") or "child").lower().replace(" ", "-")) or "child"
    if doc.get("kind") == "agreement":
        return Response(
            content=build_agreement_pdf(generate_agreement(doc)),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="coparenting-agreement-{child}.pdf"'},
        )
    pdf_bytes = build_joint_pdf({**generate_joint_report(doc), "professional": await _report_professional(doc), "verify": _verify_info(doc)})
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="joint-report-{child}.pdf"'},
    )


@api.get("/joint/sample/mediation")
async def sample_mediation():
    return sample_mediation_report()


@api.get("/joint/sample/mediation/pdf")
async def sample_mediation_pdf():
    return Response(
        content=build_joint_pdf(sample_mediation_report()),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sample-mediation-statement.pdf"'},
    )


@api.get("/joint/samples")
async def list_sample_reports():
    return sample_list()


@api.get("/joint/sample/{key}")
async def sample_report_json(key: str):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    return report


@api.get("/joint/sample/{key}/pdf")
async def sample_report_pdf(key: str):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    return Response(
        content=build_joint_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sample-{key}-report.pdf"'},
    )


@api.get("/methodology/pdf")
async def methodology_pdf():
    return Response(
        content=build_methodology_pdf(app_url()),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sa-coparents-align-methodology.pdf"'},
    )


class EmailSampleIn(BaseModel):
    email: EmailStr


@api.post("/joint/sample/{key}/email")
async def email_sample_report(key: str, body: EmailSampleIn):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    label = report["subject_label"]
    view_link = f"{app_url()}/samples/{key}"
    pdf_link = f"{app_url()}/api/joint/sample/{key}/pdf"
    await send_email(
        to=str(body.email).lower(),
        subject=f"Sample report: {label} - {EMAIL_FROM_NAME}",
        html=(
            '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            "<p>Hello,</p>"
            f"<p>Here is the sample <strong>{escape(label)}</strong> report from SA CoParents Align — an example of the "
            "neutral, child-focused format professionals use to compare parent perspectives.</p>"
            f'<p><a href="{view_link}" style="color:#5B2A86">View the sample report online</a></p>'
            f'<p><a href="{pdf_link}" style="color:#5B2A86">Download the sample PDF</a></p>'
            f'<p style="font-size:12px;color:#888">Sample uses fictional data. Sent by {escape(EMAIL_FROM_NAME)} via the public sample-sharing form.</p>'
            "</td></tr></table>"
        ),
    )
    return {"ok": True}

@api.post("/joint/reports/{rid}/share")
async def share_joint_report(rid: str, body: ShareIn, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if report_role(doc, user["_id"]) is None:
        raise HTTPException(status_code=403, detail="Only a participating parent can share this report")
    pro = await db.users.find_one({"email": body.email.lower(), "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional account found with that email")
    await db.joint_reports.update_one({"id": rid}, {"$addToSet": {"shared_with": pro["_id"]}})
    try:
        await send_email(
            to=pro["email"],
            subject=f"A joint report has been shared with you - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has shared the "
                f"{escape(doc.get('subject_label', 'Joint Report'))} for <strong>{escape(doc.get('child_name') or 'their child')}</strong> with you.</p>"
                f'<p><a href="{app_url()}/joint/{rid}" style="color:#5B2A86">Open the shared report</a></p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Share notification not sent to {pro['email']}")
    return {"ok": True, "shared_with": pro.get("name", body.email.lower())}


@api.get("/joint/connections")
async def list_connections(user=Depends(get_current_user)):
    uid = user["_id"]
    docs = await db.connections.find({"user_ids": uid}, {"_id": 0}).to_list(100)
    other_of = {c["id"]: next((u for u in c["user_ids"] if u != uid), None) for c in docs}
    other_ids = [oid for oid in other_of.values() if oid]
    user_map = {u["_id"]: u async for u in db.users.find({"_id": {"$in": other_ids}}, {"name": 1, "email": 1})} if other_ids else {}
    return [
        {
            "id": c["id"],
            "other_name": user_map.get(other_of[c["id"]], {}).get("name", "Co-parent"),
            "other_email": user_map.get(other_of[c["id"]], {}).get("email", ""),
            "child_name": c.get("child_name", ""),
        }
        for c in docs
    ]


@api.get("/joint/invitations/lookup/{token}")
async def lookup_invitation(token: str):
    inv = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not inv or inv["status"] != "pending":
        raise HTTPException(status_code=404, detail="This invitation is no longer valid")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Please ask the professional to send a fresh invitation.")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    pro = await db.users.find_one({"_id": report["created_by"]}, {"verification_level": 1}) if report and report.get("created_by") else None
    return {
        "inviter_name": inv["inviter_name"],
        "invitee_name": inv["invitee_name"],
        "invitee_email": inv["invitee_email"],
        "child_name": report["child_name"] if report else "",
        "subject_label": report["subject_label"] if report else "",
        "professional_verified": bool(pro and pro.get("verification_level") == "credentials_verified"),
    }


@api.post("/joint/invitations/accept")
async def accept_invitation(body: AcceptIn, user=Depends(get_current_user)):
    raw = body.code.strip()
    inv = await db.invitations.find_one({"status": "pending", "token": raw})
    if not inv:
        inv = await db.invitations.find_one({"status": "pending", "code": raw.upper(), "invitee_email": user["email"].lower()})
    if not inv:
        other = await db.invitations.find_one({"status": "pending", "code": raw.upper()})
        if other:
            raise HTTPException(status_code=403, detail="This invitation was sent to a different email address. Sign in with the email the invitation was sent to.")
        raise HTTPException(status_code=404, detail="Invalid or expired invitation code")
    if inv["invitee_email"] != user["email"].lower():
        raise HTTPException(status_code=403, detail="This invitation was sent to a different email address. Sign in with the email the invitation was sent to.")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Please ask the professional to send a fresh invitation.")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Joint report not found")
    role = inv["role"]
    await db.joint_reports.update_one(
        {"id": report["id"]},
        {"$set": {
            f"participants.{role}.user_id": user["_id"],
            f"participants.{role}.name": user.get("name") or inv["invitee_name"],
            "status": "in_progress",
        }},
    )
    await db.invitations.update_one(
        {"id": inv["id"]},
        {"$set": {"status": "accepted", "accepted_by": user["_id"], "accepted_at": datetime.now(timezone.utc).isoformat()}},
    )
    other_role = "b" if role == "a" else "a"
    other = report["participants"][other_role]
    if other.get("user_id"):
        pair = sorted([user["_id"], other["user_id"]])
        await db.connections.update_one(
            {"user_ids": pair},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "user_ids": pair, "child_name": report["child_name"], "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"ok": True, "report_id": report["id"]}


@api.post("/joint/invitations/{iid}/resend")
async def resend_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can resend the invitation")
    if inv["status"] != "pending":
        raise HTTPException(status_code=400, detail="This invitation is no longer pending")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Reissue a fresh invitation instead.")
    try:
        await send_invite_email(InviteSpec(
            report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
            invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
            child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
        ), inv["token"])
    except Exception:
        logger.warning(f"Invitation resend email not sent to {inv['invitee_email']}")
    return {"ok": True}


@api.post("/joint/invitations/{iid}/reissue")
async def reissue_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can reissue the invitation")
    if inv["status"] != "pending":
        raise HTTPException(status_code=400, detail="This invitation is no longer pending")
    now = datetime.now(timezone.utc).isoformat()
    await db.invitations.update_one({"id": iid}, {"$set": {"status": "expired", "expired_at": now}})
    new_inv = await create_invitation(InviteSpec(
        report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
        invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
        child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
    ))
    await db.access_events.insert_one({"report_id": report["id"], "action": f"Invitation reissued to Parent {'1' if inv['role'] == 'a' else '2'}", "at": now, "by": user["_id"]})
    return {"ok": True, **_pending_public([new_inv])[0]}


@api.get("/joint/invitations/{iid}/reminder-preview")
async def reminder_preview(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can preview the reminder")
    subject, html = _invite_email_content(InviteSpec(
        report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
        invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
        child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
    ), inv["token"])
    return {"to": inv["invitee_email"], "subject": subject, "html": html}


class NoteIn(BaseModel):
    text: str


@api.post("/joint/reports/{rid}/notes")
async def add_professional_note(rid: str, body: NoteIn, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can add notes")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Note text is required")
    note = {"id": str(uuid.uuid4()), "report_id": rid, "author_id": user["_id"],
            "text": body.text.strip(), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.professional_notes.insert_one(note)
    return {"ok": True, "id": note["id"]}


@api.get("/joint/reports/{rid}/notes")
async def list_professional_notes(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can view notes")
    return await db.professional_notes.find(
        {"report_id": rid, "author_id": user["_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)


@api.put("/joint/reports/{rid}/notes/{nid}")
async def edit_professional_note(rid: str, nid: str, body: NoteIn, user=Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note text is required")
    note = await db.professional_notes.find_one({"id": nid, "report_id": rid, "author_id": user["_id"]}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note["text"] == text:
        return {"ok": True, "unchanged": True}
    now = datetime.now(timezone.utc).isoformat()
    revision = {"text": note["text"], "at": note.get("updated_at") or note["created_at"]}
    await db.professional_notes.update_one({"id": nid}, {"$set": {"text": text, "updated_at": now}, "$push": {"revisions": revision}})
    return {"ok": True, "updated_at": now}


@api.delete("/joint/reports/{rid}/notes/{nid}")
async def delete_professional_note(rid: str, nid: str, user=Depends(get_current_user)):
    res = await db.professional_notes.delete_one({"id": nid, "report_id": rid, "author_id": user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@api.get("/verify/{case_code}/qr.png")
async def public_verify_qr(case_code: str):
    code = re.sub(r"[^A-Z0-9-]", "", case_code.strip().upper())[:20]
    if len(code) < 6:
        raise HTTPException(status_code=400, detail="Invalid case code")
    return Response(content=verify_qr_png(f"{app_url()}/verify?code={code}"), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@api.get("/verify/{case_code}")
async def public_verify_case(case_code: str):
    code = re.sub(r"[^A-Z0-9-]", "", case_code.strip().upper())[:20]
    if len(code) < 6:
        raise HTTPException(status_code=400, detail="Enter the case code from your invitation (e.g. SA-EDU-123456)")
    report = await db.joint_reports.find_one({"case_code": code}, {"_id": 0, "created_by": 1, "professional_id": 1, "subject_label": 1, "archived": 1, "created_at": 1})
    if not report:
        raise HTTPException(status_code=404, detail="No Professional Alignment Case matches that code. Check the code in your invitation email.")
    pro_id = report.get("professional_id") or report.get("created_by")
    pro = await db.users.find_one({"_id": pro_id, "role": "professional"}, {"name": 1, "approved": 1, "verification_level": 1, "profile": 1})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional is assigned to this case.")
    profile = pro.get("profile") or {}
    return {
        "case_code": code,
        "subject_label": report.get("subject_label", ""),
        "case_active": not report.get("archived"),
        "professional_name": pro.get("name", ""),
        "professional_role": profile.get("pro_role", ""),
        "organization": profile.get("organization", ""),
        "account_approved": bool(pro.get("approved")),
        "credentials_verified": pro.get("verification_level") == "credentials_verified",
    }


@api.get("/notes/search")
async def search_professional_notes(q: str = "", user=Depends(get_current_user)):
    needle = q.strip()
    if len(needle) < 2:
        return []
    notes = await db.professional_notes.find(
        {"author_id": user["_id"], "text": {"$regex": re.escape(needle), "$options": "i"}}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    rids = list({n["report_id"] for n in notes})
    reports = {r["id"]: r async for r in db.joint_reports.find({"id": {"$in": rids}}, {"_id": 0, "id": 1, "case_code": 1, "subject_label": 1, "child_name": 1, "archived": 1})}
    out = []
    for n in notes:
        r = reports.get(n["report_id"], {})
        child = (r.get("child_name") or "").strip()
        out.append({**n, "case_code": r.get("case_code", ""), "subject_label": r.get("subject_label", ""), "child_ref": f"{child[0].upper()}." if child else "", "archived": bool(r.get("archived"))})
    return out


@api.get("/joint/reports/{rid}/activity")
async def report_activity(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can view activity")
    invs = await db.invitations.find({"report_id": rid}, {"_id": 0, "token": 0}).to_list(20)
    events = await db.access_events.find({"report_id": rid}, {"_id": 0}).sort("at", -1).to_list(200)
    return {
        "invitations": invs, "access_events": events,
        "created_at": report.get("created_at"), "status": report.get("status"),
    }


@api.post("/joint/invitations/{iid}/cancel")
async def cancel_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can cancel the invitation")
    await db.invitations.update_one({"id": iid}, {"$set": {"status": "cancelled"}})
    return {"ok": True}


@api.patch("/joint/invitations/{iid}")
async def change_invitation_subject(iid: str, body: PatchInvitationIn, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can change the subject")
    if body.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail="Unknown subject")
    if report["subject"] == "multi":
        raise HTTPException(status_code=400, detail="Subject change is not available for customized reports")
    if report["status"] == "ready":
        raise HTTPException(status_code=400, detail="The subject cannot be changed after both parents have completed")
    label = body.custom_subject.strip() if body.subject == "custom" else SUBJECTS[body.subject]["label"]
    if body.subject == "custom" and not label:
        label = "Custom Subject"
    await db.joint_reports.update_one({"id": report["id"]}, {"$set": {"subject": body.subject, "subject_label": label}})
    return {"ok": True, "subject_label": label}


# ---------- Joint Alignment Case integration (sacoparentsapp.online → Align) ----------


def check_integration_key(request: Request):
    if request.headers.get("x-integration-key") != INTEGRATION_SECRET:
        raise HTTPException(status_code=401, detail="Invalid integration key")


@api.get("/integrations/case-invite/{token}")
async def integration_case_invite(token: str, request: Request):
    check_integration_key(request)
    inv = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation token")
    if inv["status"] == "pending" and invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "case_id": report.get("case_code") or report["id"],
        "report_id": report["id"],
        "assessment_type": report["subject_label"],
        "child_name": report.get("child_name", ""),
        "parent_role": inv["role"],
        "parent_name": inv.get("invitee_name", ""),
        "parent_email": inv["invitee_email"],
        "professional_name": report.get("professional_name"),
        "requested_by": inv.get("inviter_name", ""),
        "invitation_status": inv["status"],
        "case_status": report["status"],
    }


class CaseUpdateIn(BaseModel):
    token: str
    status: str
    assessment_id: str = ""
    responses: dict | None = None


def _compute_case_updates(report: dict, role: str, body: "CaseUpdateIn", now: str) -> dict:
    if body.status == "started":
        return {"status": "in_progress"} if report["status"] == "pending_invite" else {}
    if body.status != "completed":
        raise HTTPException(status_code=400, detail="Unknown status — use 'started' or 'completed'")
    answers = {k: str(v)[:5000] for k, v in (body.responses or {}).items()}
    updates = {
        f"responses.{role}": {
            "answers": answers,
            "completed_at": now,
            "imported": True,
            "external": {
                "assessment_id": body.assessment_id,
                "source": "sacoparentsapp.online",
                "assessments": [{"title": report["subject_label"], "responses": answers}],
            },
        }
    }
    other = "b" if role == "a" else "a"
    if (report.get("responses") or {}).get(other):
        updates["status"] = "ready"
    elif report["status"] == "pending_invite":
        updates["status"] = "in_progress"
    return updates


async def _notify_case_ready(report: dict) -> None:
    notify_id = report.get("professional_id") or report.get("created_by")
    notify = await db.users.find_one({"_id": notify_id}) if notify_id else None
    if not notify:
        return
    try:
        await send_email(
            to=notify["email"],
            subject=f"Joint Alignment Report ready - {report.get('case_code') or report['id']} - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(notify.get('name') or 'there')},</p>"
                f"<p>Both parents have completed their private assessments for case "
                f"<strong>{escape(report.get('case_code') or report['id'])}</strong> "
                f"({escape(report['subject_label'])}, {escape(report.get('child_name') or 'child')}).</p>"
                f'<p><a href="{app_url()}/joint/{report["id"]}" style="display:inline-block;background:#5B2A86;color:#ffffff;'
                'padding:12px 24px;text-decoration:none;border-radius:6px">Generate Joint Alignment Report</a></p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Case-ready notification not sent for {report['id']}")


@api.post("/integrations/case-update")
async def integration_case_update(body: CaseUpdateIn, request: Request):
    check_integration_key(request)
    inv = await db.invitations.find_one({"token": body.token}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Case not found")
    now = datetime.now(timezone.utc).isoformat()
    updates = _compute_case_updates(report, inv["role"], body, now)
    if inv["status"] == "pending":
        await db.invitations.update_one({"id": inv["id"]}, {"$set": {"status": "accepted", "accepted_at": now}})
    if updates:
        await db.joint_reports.update_one({"id": report["id"]}, {"$set": updates})
    if updates.get("status") == "ready":
        await _notify_case_ready(report)
    return {"ok": True, "case_status": updates.get("status", report["status"])}


# ---------- External account linking (sacoparentsapp.online) ----------

class LinkIn(BaseModel):
    code: str


@api.post("/external/link")
async def link_external_account(body: LinkIn, user=Depends(get_current_user)):
    code = body.code.strip().upper()
    try:
        async with httpx.AsyncClient(timeout=30) as client_http:
            resp = await client_http.post(
                f"{EXTERNAL_APP_URL}/api/integrations/verify-link-code",
                headers={"X-Integration-Key": INTEGRATION_SECRET},
                json={"code": code},
            )
    except Exception as e:
        logger.error(f"External link verify error: {e}")
        raise HTTPException(status_code=502, detail="Could not reach the SA CoParents service. Try again later.")
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid or expired link code")
    data = resp.json()
    ext_email = (data.get("email") or "").lower()
    if not ext_email:
        raise HTTPException(status_code=502, detail="Unexpected response from the SA CoParents service")
    await db.account_links.update_one(
        {"user_id": user["_id"]},
        {"$set": {"external_email": ext_email, "linked_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "external_email": ext_email}


@api.get("/external/link")
async def get_external_link(user=Depends(get_current_user)):
    link = await db.account_links.find_one({"user_id": user["_id"]}, {"_id": 0})
    if not link:
        return {"linked": False}
    return {"linked": True, "external_email": link["external_email"], "linked_at": link["linked_at"]}


@api.delete("/external/link")
async def unlink_external_account(user=Depends(get_current_user)):
    await db.account_links.delete_one({"user_id": user["_id"]})
    return {"ok": True}


async def fetch_external_export(email: str):
    try:
        async with httpx.AsyncClient(timeout=30) as client_http:
            resp = await client_http.get(
                f"{EXTERNAL_APP_URL}/api/integrations/export-assessments",
                headers={"X-Integration-Key": INTEGRATION_SECRET},
                params={"email": email},
            )
    except Exception as e:
        logger.error(f"External export error: {e}")
        raise HTTPException(status_code=502, detail="Could not reach the SA CoParents service. Try again later.")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="No completed assessments found on your sacoparentsapp.online account")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not retrieve your assessments from SA CoParents")
    return resp.json()


@api.get("/external/assessments")
async def get_external_assessments(user=Depends(get_current_user)):
    link = await db.account_links.find_one({"user_id": user["_id"]})
    if not link:
        raise HTTPException(status_code=400, detail="Link your sacoparentsapp.online account first")
    payload = await fetch_external_export(link["external_email"])
    return {"assessments": payload.get("assessments", []), "statements": payload.get("statements", [])}


@api.post("/joint/reports/{rid}/import")
async def import_external_assessment(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    role = report_role(doc, user["_id"])
    if role is None:
        raise HTTPException(status_code=403, detail="Only invited parents can import an assessment")
    link = await db.account_links.find_one({"user_id": user["_id"]})
    if not link:
        raise HTTPException(status_code=400, detail="Link your sacoparentsapp.online account first")
    payload = await fetch_external_export(link["external_email"])
    updates = {
        f"responses.{role}": {
            "answers": {},
            "imported": True,
            "external": payload,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    other = "b" if role == "a" else "a"
    if doc.get("responses", {}).get(other):
        updates["status"] = "ready"
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    doc = await get_joint_report_doc(rid, user)
    return joint_public(doc, user)


@api.get("/reports/complete")
async def complete_alignment_report(user=Depends(get_current_user)):
    uid = user["_id"]
    cases = await db.cases.find({"user_id": uid}, {"_id": 0}).to_list(200)
    joints = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).to_list(200)
    return build_complete_report(cases, joints, user.get("name", ""))


@api.get("/reports/complete/pdf")
async def complete_alignment_report_pdf(user=Depends(get_current_user)):
    uid = user["_id"]
    cases = await db.cases.find({"user_id": uid}, {"_id": 0}).to_list(200)
    joints = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).to_list(200)
    report = build_complete_report(cases, joints, user.get("name", ""))
    if report["is_empty"]:
        raise HTTPException(status_code=400, detail="The Complete Report PDF becomes available once at least one assessment or joint report is complete")
    return Response(
        content=build_complete_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="complete-alignment-report.pdf"'},
    )


class AgreementIn(BaseModel):
    child_name: str
    parent_a_name: str
    parent_a_email: EmailStr
    parent_b_name: str
    parent_b_email: EmailStr


@api.post("/joint/agreements")
async def create_agreement(body: AgreementIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Co-parenting agreements are initiated by an authorized professional. Parents participate through a secure invitation.")
    rid = str(uuid.uuid4())
    case_code = new_case_code("co_parenting", kind="agreement")
    pa_email = str(body.parent_a_email).lower()
    pb_email = str(body.parent_b_email).lower()
    doc = {
        "id": rid,
        "kind": "agreement",
        "subject": "co_parenting",
        "subjects": ["co_parenting"],
        "subject_label": "Co-Parenting Agreement",
        "is_safety": False,
        "case_code": case_code,
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": body.parent_a_name.strip(), "email": pa_email},
            "b": {"user_id": None, "name": body.parent_b_name.strip(), "email": pb_email},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.joint_reports.insert_one(doc)
    inv_a = await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=body.parent_a_name, invitee_email=pa_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label="Co-Parenting Agreement", code=case_code, via_professional=True))
    inv_b = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.parent_b_name, invitee_email=pb_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label="Co-Parenting Agreement", code=case_code, via_professional=True))
    return {**joint_public(doc, user), "invitations": [
        {"id": inv_a["id"], "role": "a", "code": inv_a["code"], "link": f"{app_url()}/join/{inv_a['token']}", "invitee_email": inv_a["invitee_email"], "email": inv_a["invitee_email"], "status": "pending"},
        {"id": inv_b["id"], "role": "b", "code": inv_b["code"], "link": f"{app_url()}/join/{inv_b['token']}", "invitee_email": inv_b["invitee_email"], "email": inv_b["invitee_email"], "status": "pending"},
    ]}


class ProRequestIn(BaseModel):
    professional_email: EmailStr
    child_name: str
    co_parent_name: str = ""
    co_parent_email: EmailStr | None = None


class PrepareIn(BaseModel):
    parent_a_email: EmailStr | None = None
    parent_b_email: EmailStr | None = None
    parent_b_name: str | None = None


@api.get("/professionals")
async def list_professionals(user=Depends(get_current_user)):
    return await db.users.find({"role": "professional", "approved": {"$ne": False}}, {"_id": 0, "name": 1, "email": 1, "verification_level": 1}).sort("name", 1).to_list(5000)


@api.get("/admin/professionals")
async def list_approved_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "approved": True}, {"password_hash": 0}).sort("name", 1).to_list(500)
    return [{**public_user(u), "profile": u.get("profile", {}), "credentials_verified_at": u.get("credentials_verified_at", "")} for u in docs]


class VerifyIn(BaseModel):
    verified: bool = True


@api.post("/admin/verify-credentials/{user_id}")
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


@api.get("/admin/pending-professionals")
async def list_pending_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "approved": False, "declined": {"$ne": True}}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    return [{**public_user(u), "profile": u.get("profile", {}), "created_at": u.get("created_at", ""), "verification_level": u.get("verification_level", "")} for u in docs]


@api.get("/admin/declined-professionals")
async def list_declined_professionals(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.users.find({"role": "professional", "declined": True}, {"password_hash": 0}).sort("declined_at", -1).to_list(200)
    return [{**public_user(u), "profile": u.get("profile", {}), "created_at": u.get("created_at", ""), "declined_at": u.get("declined_at", ""), "declined_reason": u.get("declined_reason", "")} for u in docs]


@api.post("/admin/reconsider-professional/{user_id}")
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


@api.post("/admin/approve-professional/{user_id}")
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


@api.post("/admin/decline-professional/{user_id}")
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


class ArchiveIn(BaseModel):
    archived: bool = True


@api.patch("/joint/reports/{rid}/archive")
async def archive_joint_report(rid: str, body: ArchiveIn, user=Depends(get_current_user)):
    doc = await db.joint_reports.find_one({"id": rid}, {"_id": 0})
    if not doc or (doc.get("created_by") != user["_id"] and doc.get("professional_id") != user["_id"]):
        raise HTTPException(status_code=404, detail="Report not found")
    await db.joint_reports.update_one({"id": rid}, {"$set": {"archived": body.archived, "archived_at": datetime.now(timezone.utc).isoformat() if body.archived else None}})
    return {"ok": True, "archived": body.archived}


PRO_INVITE_TTL_HOURS = 72


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _pro_req_status(d: dict) -> str:
    if d["status"] == "pending" and d.get("expires_at") and d["expires_at"] < datetime.now(timezone.utc).isoformat():
        return "expired"
    return d["status"]


def _pro_req_public(d: dict) -> dict:
    return {
        "id": d["id"], "child_name": d["child_name"], "parent_name": d["parent_name"],
        "parent_email": d["parent_email"], "co_parent_name": d["co_parent_name"],
        "co_parent_email": d.get("co_parent_email"), "professional_name": d.get("professional_name", ""),
        "status": _pro_req_status(d), "created_at": d["created_at"], "expires_at": d.get("expires_at"),
        "decided_at": d.get("decided_at"), "events": d.get("events", []),
    }


def _pro_email_wrap(inner: str) -> str:
    return ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            + inner + f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>')


async def _notify_parent(req: dict, subject: str, inner_html: str) -> None:
    try:
        await send_email(to=req["parent_email"], subject=f"{subject} - {EMAIL_FROM_NAME}", html=_pro_email_wrap(inner_html))
    except Exception:
        logger.warning(f"Parent notification not sent to {req['parent_email']}")


@api.post("/joint/professional-requests")
async def create_pro_request(body: ProRequestIn, user=Depends(get_current_user)):
    pro = await db.users.find_one({"email": body.professional_email.lower(), "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional account found with that email")
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    req = {
        "id": str(uuid.uuid4()),
        "parent_id": user["_id"],
        "parent_name": user.get("name", ""),
        "parent_email": user["email"],
        "co_parent_name": body.co_parent_name.strip(),
        "co_parent_email": body.co_parent_email.lower() if body.co_parent_email else None,
        "child_name": body.child_name.strip(),
        "professional_id": pro["_id"],
        "professional_email": pro["email"].lower(),
        "professional_name": pro.get("name", ""),
        "status": "pending",
        "token_hash": _hash_token(token),
        "token_used_at": None,
        "expires_at": (now + timedelta(hours=PRO_INVITE_TTL_HOURS)).isoformat(),
        "events": [{"type": "sent", "at": now.isoformat(), "by": "parent"}],
        "created_at": now.isoformat(),
    }
    await db.professional_requests.insert_one(req)
    try:
        await send_email(
            to=pro["email"],
            subject=f"Family violence assessment facilitation request - {EMAIL_FROM_NAME}",
            html=_pro_email_wrap(
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has asked you to facilitate a joint "
                f"family violence co-parenting assessment regarding <strong>{escape(req['child_name'])}</strong>.</p>"
                "<p>Full parent details are shown after you open the secure invitation while signed in with your "
                f"verified professional account (<strong>{escape(pro['email'])}</strong>).</p>"
                f'<p><a href="{app_url()}/accept-invite?token={token}" style="color:#5B2A86;font-weight:bold">Review this invitation</a></p>'
                f"<p style=\"font-size:13px;color:#555\">This link is single-use and expires in {PRO_INVITE_TTL_HOURS} hours. "
                "Please do not forward it — it is tied to your professional email address. You may accept, decline, "
                "request more information, or report a conflict of interest.</p>"
            ),
        )
    except Exception:
        logger.warning(f"Professional request email not sent to {pro['email']}")
    return {"ok": True, "id": req["id"]}


@api.get("/joint/professional-requests/lookup")
async def lookup_pro_request(token: str, user=Depends(get_current_user)):
    req = await db.professional_requests.find_one({"token_hash": _hash_token(token)}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="This invitation link is not valid")
    if (user.get("email") or "").lower() != req.get("professional_email"):
        raise HTTPException(status_code=403, detail="This invitation was sent to a different professional email address. Sign in with the invited account.")
    status = _pro_req_status(req)
    if status == "expired":
        raise HTTPException(status_code=410, detail=f"This invitation expired after {PRO_INVITE_TTL_HOURS} hours. Ask the parent to send a new one.")
    if req.get("token_used_at") or status != "pending":
        raise HTTPException(status_code=410, detail="This invitation link has already been used")
    return {"id": req["id"], "parent_name": req["parent_name"], "child_name": req["child_name"],
            "created_at": req["created_at"], "expires_at": req["expires_at"], "status": status}


@api.get("/joint/professional-requests")
async def list_pro_requests(user=Depends(get_current_user)):
    if is_pro(user):
        docs = await db.professional_requests.find({"professional_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        docs = await db.professional_requests.find({"parent_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [_pro_req_public(d) for d in docs]


class DecisionIn(BaseModel):
    reason: str = ""


async def _load_pending_pro_request(req_id: str, user: dict) -> dict:
    require_approved_professional(user, "Only professional accounts can respond to invitations")
    req = await db.professional_requests.find_one({"id": req_id, "professional_id": user["_id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    status = _pro_req_status(req)
    if status == "expired":
        raise HTTPException(status_code=410, detail=f"This invitation expired after {PRO_INVITE_TTL_HOURS} hours")
    if status != "pending":
        raise HTTPException(status_code=400, detail="This invitation has already been answered")
    return req


async def _decide_pro_request(req: dict, new_status: str, event: str, reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req["id"]},
        {"$set": {"status": new_status, "decided_at": now, "token_used_at": now},
         "$push": {"events": {"type": event, "at": now, "by": "professional", "note": reason[:500]}}},
    )


@api.post("/joint/professional-requests/{req_id}/decline")
async def decline_pro_request(req_id: str, body: DecisionIn | None = None, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    reason = (body.reason if body else "").strip()
    await _decide_pro_request(req, "declined", "declined", reason)
    await _notify_parent(req, "Professional unable to accept your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> is unable to facilitate the assessment you requested "
        f"regarding <strong>{escape(req['child_name'])}</strong>.</p>"
        + (f"<p><strong>Note from the professional:</strong> {escape(reason)}</p>" if reason else "")
        + "<p>You may invite a different professional from your dashboard.</p>")
    return {"ok": True, "status": "declined"}


@api.post("/joint/professional-requests/{req_id}/request-info")
async def request_info_pro_request(req_id: str, body: DecisionIn, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    message = body.reason.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please describe what additional information you need")
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req["id"]},
        {"$push": {"events": {"type": "info_requested", "at": now, "by": "professional", "note": message[:1000]}}},
    )
    await _notify_parent(req, "A professional has a question about your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> needs more information before deciding on your "
        f"request regarding <strong>{escape(req['child_name'])}</strong>:</p>"
        f"<blockquote style=\"border-left:3px solid #5B2A86;padding-left:12px;color:#333\">{escape(message)}</blockquote>"
        f"<p>Reply to this email or contact the professional directly. The invitation remains open until {escape(str(req['expires_at'])[:16].replace('T', ' '))} UTC.</p>")
    return {"ok": True, "status": "pending"}


@api.post("/joint/professional-requests/{req_id}/conflict")
async def conflict_pro_request(req_id: str, body: DecisionIn | None = None, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    await _decide_pro_request(req, "declined_conflict", "conflict_reported", (body.reason if body else "").strip())
    await _notify_parent(req, "Professional unable to accept your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> is unable to facilitate the assessment you requested "
        f"regarding <strong>{escape(req['child_name'])}</strong> because of a potential conflict of interest.</p>"
        "<p>This is a routine professional safeguard. You may invite a different professional from your dashboard.</p>")
    return {"ok": True, "status": "declined_conflict"}


def _first_email(*candidates) -> str:
    for c in candidates:
        if c:
            return str(c).lower()
    return ""


def _resolve_prepare_parties(req: dict, body: "PrepareIn | None") -> tuple:
    pa_email = _first_email(body.parent_a_email if body else None, req["parent_email"])
    pb_email = _first_email(body.parent_b_email if body else None, req.get("co_parent_email"))
    pb_name = ((body.parent_b_name or "").strip() if body else "") or req.get("co_parent_name") or "Co-parent"
    if not pb_email:
        raise HTTPException(status_code=400, detail="Please provide both parents' email addresses so each receives their private assessment")
    return pa_email, pb_email, pb_name


def _safety_case_doc(user: dict, req: dict, pa_email: str, pb_email: str, pb_name: str) -> dict:
    rid = str(uuid.uuid4())
    return {
        "id": rid,
        "kind": "joint_report",
        "subject": "multi",
        "subjects": sorted(SAFETY_SUBJECT_KEYS),
        "subject_label": "Family Violence & Safety Assessment",
        "is_safety": True,
        "case_code": new_case_code("safety"),
        "child_name": req["child_name"],
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": req["parent_name"], "email": pa_email},
            "b": {"user_id": None, "name": pb_name, "email": pb_email},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@api.post("/joint/professional-requests/{req_id}/prepare")
async def prepare_pro_request(req_id: str, body: PrepareIn | None = None, user=Depends(get_current_user)):
    require_approved_professional(user, "Only professional accounts can prepare assessments")
    req = await _load_pending_pro_request(req_id, user)
    pa_email, pb_email, pb_name = _resolve_prepare_parties(req, body)
    doc = _safety_case_doc(user, req, pa_email, pb_email, pb_name)
    rid = doc["id"]
    case_code = doc["case_code"]
    await db.joint_reports.insert_one(doc)
    await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=req["parent_name"], invitee_email=pa_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=pb_name, invitee_email=pb_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req_id},
        {"$set": {"status": "prepared", "report_id": rid, "prepared_at": now, "decided_at": now, "token_used_at": now},
         "$push": {"events": {"type": "accepted", "at": now, "by": "professional"}}},
    )
    return {"ok": True, "report_id": rid}


# ---------- Scheduled completion notifications ----------

async def _cron_accept(request: Request, job: str) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not secrets.compare_digest(token, WEBHOOK_CRON_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    run_id = (envelope or {}).get("run_id") or request.headers.get("x-webhook-id")
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id, "job": job}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": job, "at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True}


@api.post("/cron/completion-nudge")
async def cron_completion_nudge(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "completion-nudge")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_completion_nudges())
    return ack


@api.post("/cron/expiry-digest")
async def cron_expiry_digest(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "expiry-digest")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_expiry_digests())
    return ack


def _digest_row(report: dict, inv: dict, now: datetime) -> str:
    expires = _parse_iso(inv["created_at"]) + timedelta(days=INVITE_EXPIRY_DAYS)
    days = (expires - now).days
    when = "has expired" if expires <= now else ("expires today" if days == 0 else f"expires in {days} day{'s' if days != 1 else ''}")
    child = (report.get("child_name") or "").strip()
    child_ref = f"{child[0].upper()}." if child else "child"
    parent = "Parent 1" if inv["role"] == "a" else "Parent 2"
    return f"<li><strong>{escape(report.get('case_code') or report['id'])}</strong> ({escape(report.get('subject_label', ''))}, matter for {escape(child_ref)}) &mdash; invitation to {parent} {when}</li>"


@api.post("/cron/weekly-summary")
async def cron_weekly_summary(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "weekly-summary")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_weekly_summaries())
    return ack


def _matter_state(report: dict, pending: list, now: datetime) -> tuple[str, str]:
    if report.get("status") == "ready":
        return "ready", "Report ready"
    a = bool(report.get("responses", {}).get("a"))
    b = bool(report.get("responses", {}).get("b"))
    states = {(True, False): ("awaiting_b", "Awaiting Parent 2"), (False, True): ("awaiting_a", "Awaiting Parent 1")}
    key, label = states.get((a, b), ("awaiting_both", "Awaiting both parents"))
    expiring = [i for i in pending if _parse_iso(i["created_at"]) + timedelta(days=INVITE_EXPIRY_DAYS - INVITE_EXPIRING_SOON_DAYS) <= now]
    if expiring:
        label += f" &middot; {len(expiring)} invitation{'s' if len(expiring) != 1 else ''} expiring/expired"
    return key, label


def _summary_row(report: dict, label: str) -> str:
    child = (report.get("child_name") or "").strip()
    child_ref = f"{child[0].upper()}." if child else "child"
    return (
        f"<tr><td style=\"padding:6px 8px;border-bottom:1px solid #eee\"><strong>{escape(report.get('case_code') or report['id'][:8])}</strong><br>"
        f"<span style=\"color:#666;font-size:12px\">{escape(report.get('subject_label', ''))} &middot; matter for {escape(child_ref)}</span></td>"
        f"<td style=\"padding:6px 8px;border-bottom:1px solid #eee\">{label}</td></tr>"
    )


async def _weekly_summary_html(pro: dict, reports: list, now: datetime) -> str:
    rids = [r["id"] for r in reports]
    pending: dict[str, list] = {}
    async for i in db.invitations.find({"report_id": {"$in": rids}, "status": "pending"}, {"_id": 0}):
        pending.setdefault(i["report_id"], []).append(i)
    week_ago = (now - timedelta(days=7)).isoformat()
    new_notes = await db.professional_notes.count_documents({"author_id": pro["_id"], "created_at": {"$gte": week_ago}})
    counts = {"ready": 0, "awaiting_a": 0, "awaiting_b": 0, "awaiting_both": 0}
    rows = []
    for r in sorted(reports, key=lambda x: x.get("created_at", "")):
        key, label = _matter_state(r, pending.get(r["id"], []), now)
        counts[key] += 1
        rows.append(_summary_row(r, label))
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
        f"<p>Here is your Monday overview of <strong>{len(reports)} active family matter{'s' if len(reports) != 1 else ''}</strong>.</p>"
        f"<p style=\"font-size:14px\"><strong>{counts['ready']}</strong> report{'s' if counts['ready'] != 1 else ''} ready &middot; "
        f"<strong>{counts['awaiting_a'] + counts['awaiting_b']}</strong> awaiting one parent &middot; "
        f"<strong>{counts['awaiting_both']}</strong> awaiting both parents &middot; "
        f"<strong>{new_notes}</strong> private note{'s' if new_notes != 1 else ''} added this week</p>"
        f"<table style=\"border-collapse:collapse;width:100%;font-size:14px\">{''.join(rows)}</table>"
        f'<p><a href="{app_url()}/matters" style="display:inline-block;background:#5B2A86;color:#ffffff;'
        'padding:12px 24px;text-decoration:none;border-radius:6px;margin-top:12px">Open Family Matters</a></p>'
        f'<p style="font-size:12px;color:#888">Weekly caseload summary sent by {escape(EMAIL_FROM_NAME)}. '
        f'Turn this off at {app_url()}/matters. Children are shown by initial only; parent responses are never included in email.</p>'
        "</td></tr></table>"
    )


async def run_weekly_summaries() -> None:
    now = datetime.now(timezone.utc)
    week = now.strftime("%G-W%V")
    by_pro: dict[str, list] = {}
    async for r in db.joint_reports.find({"archived": {"$ne": True}, "created_by": {"$ne": None}}, {"_id": 0}):
        by_pro.setdefault(r["created_by"], []).append(r)
    for pro_id, reports in by_pro.items():
        if await db.cron_runs.find_one({"job": "weekly-summary-sent", "pro_id": pro_id, "week": week}):
            continue
        pro = await db.users.find_one({"_id": pro_id, "role": "professional", "approved": True})
        if not pro or not pro.get("weekly_summary", True) or pro["email"].endswith("@example.com"):
            continue
        try:
            await send_email(
                to=pro["email"],
                subject=f"Weekly caseload summary: {len(reports)} active matter{'s' if len(reports) != 1 else ''} - {EMAIL_FROM_NAME}",
                html=await _weekly_summary_html(pro, reports, now),
            )
            await db.cron_runs.insert_one({"job": "weekly-summary-sent", "pro_id": pro_id, "week": week, "count": len(reports), "at": now.isoformat()})
        except Exception:
            logger.warning(f"Weekly summary not sent to {pro['email']}")


def _digest_html(pro: dict, rows: list[str], freq: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
        f"<p>The following parent invitations expire within {INVITE_EXPIRING_SOON_DAYS} days or have already expired. "
        "You can send a reminder or reissue a fresh invitation from your Family Matters page.</p>"
        f"<ul>{''.join(rows)}</ul>"
        f'<p><a href="{app_url()}/matters?filter=expiring" style="display:inline-block;background:#5B2A86;color:#ffffff;'
        'padding:12px 24px;text-decoration:none;border-radius:6px">Open Family Matters</a></p>'
        f'<p style="font-size:12px;color:#888">{"Weekly" if freq == "weekly" else "Daily"} digest sent by {escape(EMAIL_FROM_NAME)}. '
        f'Change how often you receive this at {app_url()}/matters. Parent responses are never included in email.</p>'
        "</td></tr></table>"
    )


async def _expiring_rows_by_pro(now: datetime) -> dict[str, list[str]]:
    cutoff = (now - timedelta(days=INVITE_EXPIRY_DAYS - INVITE_EXPIRING_SOON_DAYS)).isoformat()
    invs = await db.invitations.find({"status": "pending", "created_at": {"$lte": cutoff}}, {"_id": 0}).to_list(2000)
    if not invs:
        return {}
    rids = list({i["report_id"] for i in invs})
    reports = {r["id"]: r async for r in db.joint_reports.find({"id": {"$in": rids}, "archived": {"$ne": True}}, {"_id": 0})}
    by_pro: dict[str, list[str]] = {}
    for inv in invs:
        report = reports.get(inv["report_id"])
        if report and report.get("created_by"):
            by_pro.setdefault(report["created_by"], []).append(_digest_row(report, inv, now))
    return by_pro


def _digest_due(pro: dict, now: datetime) -> str | None:
    freq = pro.get("digest_frequency") or "daily"
    if freq == "off" or (freq == "weekly" and now.weekday() != 0):
        return None
    return freq


async def _send_digest(pro_id: str, rows: list[str], now: datetime) -> None:
    today = now.date().isoformat()
    if await db.cron_runs.find_one({"job": "expiry-digest-sent", "pro_id": pro_id, "day": today}):
        return
    pro = await db.users.find_one({"_id": pro_id, "role": "professional"})
    freq = _digest_due(pro, now) if pro else None
    if not freq:
        return
    try:
        await send_email(
            to=pro["email"],
            subject=f"{len(rows)} parent invitation{'s' if len(rows) != 1 else ''} expiring soon - {EMAIL_FROM_NAME}",
            html=_digest_html(pro, rows, freq),
        )
        await db.cron_runs.insert_one({"job": "expiry-digest-sent", "pro_id": pro_id, "day": today, "count": len(rows), "at": now.isoformat()})
    except Exception:
        logger.warning(f"Expiry digest not sent to {pro['email']}")


async def run_expiry_digests() -> None:
    now = datetime.now(timezone.utc)
    for pro_id, rows in (await _expiring_rows_by_pro(now)).items():
        await _send_digest(pro_id, rows, now)


def _parse_iso(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except Exception:
        return None


def _ready_email_html(name: str, child: str, label: str, link: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(name)},</p>"
        f"<p>Both parents have completed their assessments for <strong>{escape(child)}</strong> ({escape(label)}). "
        "Your Joint Report is ready to view.</p>"
        f'<p><a href="{link}" style="color:#5B2A86">Open your Joint Report</a></p>'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
        "</td></tr></table>"
    )


def _ready_window_open(doc: dict, now: datetime) -> bool:
    ra, rb = doc["responses"]["a"], doc["responses"]["b"]
    done_a, done_b = _parse_iso(ra.get("completed_at")), _parse_iso(rb.get("completed_at"))
    return bool(done_a and done_b) and (now - max(done_a, done_b)) <= timedelta(hours=48)


async def _send_ready_notifications(doc: dict, now: datetime) -> None:
    if not _ready_window_open(doc, now):
        return
    sent = doc.get("ready_notified")
    if not isinstance(sent, dict):
        sent = {}
    label = doc.get("subject_label", "Joint Report")
    child = doc.get("child_name") or "your child"
    link = f"{app_url()}/joint/{doc['id']}"
    updates = {}
    for side, p in (("a", doc["participants"]["a"]), ("b", doc["participants"]["b"])):
        if sent.get(side) or not p.get("email"):
            continue
        try:
            await send_email(
                to=p["email"],
                subject=f"Your Joint Report is ready - {EMAIL_FROM_NAME}",
                html=_ready_email_html(p.get("name") or "there", child, label, link),
            )
            updates[side] = now.isoformat()
        except Exception:
            logger.warning(f"Ready notification not sent to {p['email']}")
    if updates:
        await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {"ready_notified": {**sent, **updates}}})


def _nudge_target(doc: dict, now: datetime) -> tuple[dict, dict, str] | None:
    """Returns (done_participant, other_participant, side_to_nudge) when a nudge is due."""
    ra = doc.get("responses", {}).get("a")
    rb = doc.get("responses", {}).get("b")
    if bool(ra) == bool(rb):
        return None
    pa, pb = doc["participants"]["a"], doc["participants"]["b"]
    done, other, side = (pa, pb, "b") if ra else (pb, pa, "a")
    if doc.get("nudges", {}).get(side) or not other.get("email"):
        return None
    done_at = _parse_iso((ra or rb).get("completed_at"))
    if not done_at or not (timedelta(minutes=15) <= (now - done_at) <= timedelta(hours=48)):
        return None
    return done, other, side


def _nudge_email_html(done_name: str, other_name: str, child: str, label: str, link: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(other_name)},</p>"
        f"<p><strong>{escape(done_name)}</strong> has completed their half of the "
        f"{escape(label)} for <strong>{escape(child)}</strong>. Once you complete yours, the Joint Report "
        "will be generated for both of you.</p>"
        f'<p><a href="{link}" style="color:#5B2A86">Complete your half</a></p>'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
        "</td></tr></table>"
    )


async def _send_completion_nudge(doc: dict, now: datetime) -> None:
    target = _nudge_target(doc, now)
    if target is None:
        return
    done, other, side = target
    label = doc.get("subject_label", "Joint Report")
    child = doc.get("child_name") or "your child"
    link = f"{app_url()}/joint/{doc['id']}"
    try:
        await send_email(
            to=other["email"],
            subject=f"Your co-parent has completed their half - {EMAIL_FROM_NAME}",
            html=_nudge_email_html(done.get("name") or "Your co-parent", other.get("name") or "there", child, label, link),
        )
        await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {f"nudges.{side}": now.isoformat()}})
    except Exception:
        logger.warning(f"Completion nudge not sent to {other['email']}")


async def run_completion_nudges():
    now = datetime.now(timezone.utc)
    docs = await db.joint_reports.find({"status": {"$in": ["in_progress", "ready"]}}, {"_id": 0}).to_list(500)
    for doc in docs:
        try:
            if doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b"):
                await _send_ready_notifications(doc, now)
            else:
                await _send_completion_nudge(doc, now)
        except Exception as e:
            logger.error(f"Nudge processing error for {doc.get('id')}: {e}")


@api.get("/health")
async def api_health():
    return {"status": "healthy", "build": BUILD_ID}


app.include_router(api)


@app.get("/health")
async def health():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
