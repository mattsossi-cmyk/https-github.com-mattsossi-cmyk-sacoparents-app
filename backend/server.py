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

import bcrypt
import jwt
import hashlib
import ipaddress
import re
import secrets
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import asyncio
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr

from assessment_data import ASSESSMENT_TYPES, ORDERED_TYPE_KEYS, SCALE, demo_payload
from report_engine import generate_report
from joint_data import SUBJECTS, ORDERED_SUBJECT_KEYS, QUESTIONS, CONFIDENTIALITY_NOTICE, NEXT_STEPS, SAFETY_SUBJECT_KEYS, AGREEMENT_AREAS
from joint_engine import generate_joint_report, generate_agreement, sample_mediation_report
from pdf_report import build_joint_pdf, build_agreement_pdf, build_case_pdf, build_complete_pdf
from complete_engine import build_complete_report

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

JWT_ALGORITHM = "HS256"

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ["EMERGENT_EMAIL_KEY"]
EMAIL_FROM_NAME = os.environ["EMAIL_FROM_NAME"]
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")
WEBHOOK_CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]

EXTERNAL_APP_URL = os.environ["SACOPARENTS_APP_URL"].rstrip("/")
INTEGRATION_SECRET = os.environ["INTEGRATION_SHARED_SECRET"]
APP_ASSESSMENT_URL = os.environ.get("SACOPARENTS_APP_ASSESSMENT_URL", "").rstrip("/")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _check_no_form_fields(tags) -> None:
    if tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")


def _check_no_credential_asks(subject: str, html: str) -> None:
    body = f"{subject}\n{html}".lower()
    for phrase in _CRED_ASK:
        if phrase in body:
            raise ValueError(f"Email asks the recipient for credentials: {phrase!r} (G2)")


def _check_link_url(url: str) -> None:
    low = url.strip().lower()
    if low.startswith(("mailto:", "tel:", "cid:", "#")):
        return
    if not low.startswith("https://"):
        raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
    host = urlparse(low).hostname or ""
    if not _host_ok(host) or urlparse(low).username is not None:
        raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")


def _check_anchor_matches_target(href: str, text: str) -> None:
    real = urlparse(href.strip().lower()).hostname or ""
    if not real:
        return
    for m in _HOSTISH.finditer(text):
        if not _same_site(m.group(1).lower(), real):
            raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    _check_no_form_fields(scan.tags)
    _check_no_credential_asks(subject, html)
    for url in scan.urls:
        _check_link_url(url)
    for href, text in scan.anchors:
        _check_anchor_matches_target(href, text)


async def send_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> str | None:
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if reply_to or EMAIL_REPLY_TO:
        payload["contact_email"] = reply_to or EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Failed to send email")
    except Exception as e:
        logger.error(f"Email send error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send email")


def jwt_secret():
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "type": "access",
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


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


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "professional"
    invite: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    role = body.role if body.role in ("parent", "professional") else "professional"
    if role == "parent":
        raw = body.invite.strip()
        inv = None
        if raw:
            inv = await db.invitations.find_one({"status": "pending", "invitee_email": email, "$or": [{"token": raw}, {"code": raw.upper()}]})
        if not inv:
            raise HTTPException(status_code=403, detail="Parent accounts are created through a secure invitation from a professional. Please use the link or case code in your invitation email.")
    uid = str(uuid.uuid4())
    user = {
        "_id": uid,
        "email": email,
        "name": body.name.strip(),
        "role": role,
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
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
        except Exception:
            logger.warning(f"Password-reset email not sent for {email}")
    return {"ok": True, "detail": "If an account exists for that email, a verification code is on its way."}


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
    await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(body.new_password)}})
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
            "name": "Admin",
            "role": "admin",
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
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


def _pending_public(pending: list) -> list:
    return [
        {"id": i["id"], "role": i["role"], "invitee_email": i["invitee_email"], "invitee_name": i.get("invitee_name", ""), "status": i["status"]}
        for i in pending
    ]


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


async def send_invite_email(spec: InviteSpec, token: str):
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
        "<p>Please do not forward this invitation or share your sign-in credentials.</p>"
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. If the button does not '
        "work, sign in and enter your participation code instead.</p></td></tr></table>"
    )
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


def resolve_subjects(body_subject: str, body_subjects: list, custom: str):
    subject_keys = body_subjects or [body_subject]
    if not subject_keys or any(k not in SUBJECTS for k in subject_keys):
        raise HTTPException(status_code=400, detail="Unknown subject")
    if len(subject_keys) > 1:
        label = "Customized Report: " + " + ".join(SUBJECTS[k]["label"] for k in subject_keys[:3]) + ("…" if len(subject_keys) > 3 else "")
        return "multi", subject_keys, label
    subject = subject_keys[0]
    label = custom.strip() if subject == "custom" else SUBJECTS[subject]["label"]
    if subject == "custom" and not label:
        label = "Custom Subject"
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
    if user.get("role") != "professional":
        raise HTTPException(status_code=403, detail="Joint reports are initiated by an authorized professional. Parents participate through a secure invitation.")
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
    if user.get("role") != "professional":
        raise HTTPException(status_code=403, detail="Only professional accounts can create reports for two parents")
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


def _validated_answers(doc: dict, body: JointResponsesIn) -> dict:
    valid = {k for k, _, _ in AGREEMENT_AREAS} if doc.get("kind") == "agreement" else {k for k, _, _ in QUESTIONS}
    answers = {k: (body.answers.get(k) or "").strip() for k in valid}
    if any(not v for v in answers.values()):
        raise HTTPException(status_code=400, detail="Please answer all questions")
    payload = {"answers": answers, "completed_at": datetime.now(timezone.utc).isoformat()}
    if doc.get("kind") == "agreement" and body.foundation:
        payload["foundation"] = [
            {"title": str(s.get("title", "Foundation Statement"))[:120], "content": str(s.get("content", ""))[:5000]}
            for s in body.foundation if isinstance(s, dict)
        ]
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
    pdf_bytes = build_joint_pdf(generate_joint_report(doc))
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
    docs = await db.connections.find({"user_ids": user["_id"]}, {"_id": 0}).to_list(100)
    other_ids = [oid for c in docs for oid in [next((u for u in c["user_ids"] if u != user["_id"]), None)] if oid]
    user_map = {}
    if other_ids:
        async for u in db.users.find({"_id": {"$in": other_ids}}, {"name": 1, "email": 1}):
            user_map[u["_id"]] = u
    out = []
    for c in docs:
        other_id = next((u for u in c["user_ids"] if u != user["_id"]), None)
        other = user_map.get(other_id) or {}
        out.append({"id": c["id"], "other_name": other.get("name", "Co-parent"), "other_email": other.get("email", ""), "child_name": c.get("child_name", "")})
    return out


@api.get("/joint/invitations/lookup/{token}")
async def lookup_invitation(token: str):
    inv = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not inv or inv["status"] != "pending":
        raise HTTPException(status_code=404, detail="This invitation is no longer valid")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    return {
        "inviter_name": inv["inviter_name"],
        "invitee_name": inv["invitee_name"],
        "invitee_email": inv["invitee_email"],
        "child_name": report["child_name"] if report else "",
        "subject_label": report["subject_label"] if report else "",
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
    try:
        await send_invite_email(InviteSpec(
            report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
            invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
            child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
        ), inv["token"])
    except Exception:
        logger.warning(f"Invitation resend email not sent to {inv['invitee_email']}")
    return {"ok": True}


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
    if user.get("role") != "professional":
        raise HTTPException(status_code=403, detail="Co-parenting agreements are initiated by an authorized professional. Parents participate through a secure invitation.")
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
    return await db.users.find({"role": "professional"}, {"_id": 0, "name": 1, "email": 1}).sort("name", 1).to_list(500)


@api.post("/joint/professional-requests")
async def create_pro_request(body: ProRequestIn, user=Depends(get_current_user)):
    pro = await db.users.find_one({"email": body.professional_email.lower(), "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional account found with that email")
    req = {
        "id": str(uuid.uuid4()),
        "parent_id": user["_id"],
        "parent_name": user.get("name", ""),
        "parent_email": user["email"],
        "co_parent_name": body.co_parent_name.strip(),
        "co_parent_email": body.co_parent_email.lower() if body.co_parent_email else None,
        "child_name": body.child_name.strip(),
        "professional_id": pro["_id"],
        "professional_name": pro.get("name", ""),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.professional_requests.insert_one(req)
    try:
        await send_email(
            to=pro["email"],
            subject=f"Family violence assessment facilitation request - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has asked you to prepare a joint "
                f"family violence co-parenting assessment regarding <strong>{escape(req['child_name'])}</strong>.</p>"
                f"<p>Requesting parent: {escape(req['parent_name'])} ({escape(req['parent_email'])})."
                + (f" Other parent: {escape(req['co_parent_name'])} ({escape(req['co_parent_email'])})." if req.get("co_parent_email") else " The other parent's details are collected privately when you prepare the assessment.")
                + "</p>"
                "<p>Both parents' individual responses remain confidential and are not shared between the "
                "parties. You will see the completed comparison once both parents finish.</p>"
                f'<p><a href="{app_url()}/dashboard" style="color:#5B2A86">Open your dashboard to prepare the assessment</a></p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Professional request email not sent to {pro['email']}")
    return {"ok": True, "id": req["id"]}


@api.get("/joint/professional-requests")
async def list_pro_requests(user=Depends(get_current_user)):
    if user.get("role") == "professional":
        docs = await db.professional_requests.find({"professional_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        docs = await db.professional_requests.find({"parent_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [
        {
            "id": d["id"], "child_name": d["child_name"], "parent_name": d["parent_name"],
            "parent_email": d["parent_email"], "co_parent_name": d["co_parent_name"],
            "co_parent_email": d.get("co_parent_email"), "professional_name": d.get("professional_name", ""),
            "status": d["status"], "created_at": d["created_at"],
        }
        for d in docs
    ]


def _resolve_prepare_parties(req: dict, body: "PrepareIn | None") -> tuple:
    pa_email = str(body.parent_a_email).lower() if body and body.parent_a_email else req["parent_email"]
    pb_email = str(body.parent_b_email).lower() if body and body.parent_b_email else (req.get("co_parent_email") or "")
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
    if user.get("role") != "professional":
        raise HTTPException(status_code=403, detail="Only professional accounts can prepare assessments")
    req = await db.professional_requests.find_one({"id": req_id, "professional_id": user["_id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail="This request has already been prepared")
    pa_email, pb_email, pb_name = _resolve_prepare_parties(req, body)
    doc = _safety_case_doc(user, req, pa_email, pb_email, pb_name)
    rid = doc["id"]
    case_code = doc["case_code"]
    await db.joint_reports.insert_one(doc)
    await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=req["parent_name"], invitee_email=pa_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=pb_name, invitee_email=pb_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    await db.professional_requests.update_one(
        {"id": req_id},
        {"$set": {"status": "prepared", "report_id": rid, "prepared_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "report_id": rid}


# ---------- Scheduled completion notifications ----------

@api.post("/cron/completion-nudge")
async def cron_completion_nudge(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
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
        if await db.cron_runs.find_one({"run_id": run_id, "job": "completion-nudge"}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": "completion-nudge", "at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(run_completion_nudges())
    return {"ok": True}


async def run_completion_nudges():
    now = datetime.now(timezone.utc)
    docs = await db.joint_reports.find({"status": {"$in": ["in_progress", "ready"]}}, {"_id": 0}).to_list(500)
    for doc in docs:
        try:
            ra = doc.get("responses", {}).get("a")
            rb = doc.get("responses", {}).get("b")
            pa, pb = doc["participants"]["a"], doc["participants"]["b"]
            label = doc.get("subject_label", "Joint Report")
            child = doc.get("child_name") or "your child"
            link = f"{app_url()}/joint/{doc['id']}"
            if ra and rb:
                try:
                    done_at = max(
                        datetime.fromisoformat(str(ra.get("completed_at", "")).replace("Z", "+00:00")),
                        datetime.fromisoformat(str(rb.get("completed_at", "")).replace("Z", "+00:00")),
                    )
                except Exception:
                    continue
                if (now - done_at) > timedelta(hours=48):
                    continue
                sent = doc.get("ready_notified")
                if not isinstance(sent, dict):
                    sent = {}
                updates = {}
                for side, p in (("a", pa), ("b", pb)):
                    if sent.get(side) or not p.get("email"):
                        continue
                    try:
                        await send_email(
                            to=p["email"],
                            subject=f"Your Joint Report is ready - {EMAIL_FROM_NAME}",
                            html=(
                                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                f"<p>Hi {escape(p.get('name') or 'there')},</p>"
                                f"<p>Both parents have completed their assessments for <strong>{escape(child)}</strong> ({escape(label)}). "
                                "Your Joint Report is ready to view.</p>"
                                f'<p><a href="{link}" style="color:#5B2A86">Open your Joint Report</a></p>'
                                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
                                "</td></tr></table>"
                            ),
                        )
                        updates[side] = now.isoformat()
                    except Exception:
                        logger.warning(f"Ready notification not sent to {p['email']}")
                if updates:
                    await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {"ready_notified": {**sent, **updates}}})
                continue
            if bool(ra) == bool(rb):
                continue
            done, other, side = (pa, pb, "b") if ra else (pb, pa, "a")
            completed = ra if ra else rb
            if doc.get("nudges", {}).get(side) or not other.get("email"):
                continue
            try:
                done_at = datetime.fromisoformat(str(completed.get("completed_at", "")).replace("Z", "+00:00"))
            except Exception:
                continue
            if not (timedelta(minutes=15) <= (now - done_at) <= timedelta(hours=48)):
                continue
            try:
                await send_email(
                    to=other["email"],
                    subject=f"Your co-parent has completed their half - {EMAIL_FROM_NAME}",
                    html=(
                        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                        f"<p>Hi {escape(other.get('name') or 'there')},</p>"
                        f"<p><strong>{escape(done.get('name') or 'Your co-parent')}</strong> has completed their half of the "
                        f"{escape(label)} for <strong>{escape(child)}</strong>. Once you complete yours, the Joint Report "
                        "will be generated for both of you.</p>"
                        f'<p><a href="{link}" style="color:#5B2A86">Complete your half</a></p>'
                        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
                        "</td></tr></table>"
                    ),
                )
                await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {f"nudges.{side}": now.isoformat()}})
            except Exception:
                logger.warning(f"Completion nudge not sent to {other['email']}")
        except Exception as e:
            logger.error(f"Nudge processing error for {doc.get('id')}: {e}")


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
