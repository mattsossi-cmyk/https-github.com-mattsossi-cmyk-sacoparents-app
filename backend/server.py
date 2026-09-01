from dotenv import load_dotenv

load_dotenv()

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
import hashlib
import ipaddress
import re
import secrets
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr

from assessment_data import ASSESSMENT_TYPES, ORDERED_TYPE_KEYS, SCALE, demo_payload
from report_engine import generate_report

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


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


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
    role: str = "parent"


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
    uid = str(uuid.uuid4())
    user = {
        "_id": uid,
        "email": email,
        "name": body.name.strip(),
        "role": body.role if body.role in ("parent", "professional") else "parent",
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
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.cases.create_index("user_id")
    await db.password_resets.create_index("expires_at", expireAfterSeconds=0)
    await seed_admin()


app.include_router(api)

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
