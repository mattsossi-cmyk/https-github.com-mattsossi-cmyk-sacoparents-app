"""Authentication: JWT (email/password) + Emergent Google session exchange."""
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import UserRegister, UserLogin, UserPublic, TokenResponse, GuestClaimPayload, MagicLinkRequest, MagicLinkConsume, SignupFromToken
from email_service import send_magic_link, send_setup_link, EmailNotConfigured, EmailSendError

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


# DB dependency is set by server.py via app.state
def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def hash_password(plain: str) -> str:
    # bcrypt has a 72-byte limit
    return pwd_ctx.hash(plain[:72])


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(plain[:72], hashed)
    except Exception:
        return False


def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_jwt(token: str) -> Optional[str]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return data.get("sub")
    except jwt.PyJWTError:
        return None


def _serialize_user(doc: dict) -> UserPublic:
    return UserPublic(
        user_id=doc["user_id"],
        email=doc["email"],
        name=doc.get("name", ""),
        picture=doc.get("picture"),
        auth_method=doc.get("auth_method", "jwt"),
        children=doc.get("children", []),
        custody_situation=doc.get("custody_situation", ""),
        mediation_date=doc.get("mediation_date"),
        created_at=doc.get("created_at", datetime.now(timezone.utc).isoformat()),
        is_guest=bool(doc.get("is_guest", False)),
        guest_expires_at=doc.get("guest_expires_at"),
    )


def _is_guest_expired(doc: dict) -> bool:
    if not doc.get("is_guest"):
        return False
    exp = doc.get("guest_expires_at")
    if not exp:
        return False
    try:
        dt = datetime.fromisoformat(exp) if isinstance(exp, str) else exp
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


async def _user_by_id(db, user_id: Optional[str]) -> Optional[UserPublic]:
    if not user_id:
        return None
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return None
    if _is_guest_expired(doc):
        return None
    return _serialize_user(doc)


async def _user_from_session_token(db, token: Optional[str]) -> Optional[UserPublic]:
    """Look up a valid (non-expired) session token in user_sessions."""
    if not token:
        return None
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    exp = session["expires_at"]
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= datetime.now(timezone.utc):
        return None
    return await _user_by_id(db, session["user_id"])


async def _user_from_jwt_token(db, token: Optional[str]) -> Optional[UserPublic]:
    """Decode a JWT and return the corresponding user, or None."""
    if not token:
        return None
    return await _user_by_id(db, decode_jwt(token))


async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> UserPublic:
    """Resolve user from session_token cookie, JWT cookie, or Bearer header."""
    db = request.app.state.db
    bearer_token = creds.credentials if creds else None
    session_cookie = request.cookies.get("session_token")
    jwt_cookie = request.cookies.get(JWT_COOKIE_NAME)

    # (resolver, token) pairs — evaluated lazily so unused coroutines are
    # never created. Previously we built all four coroutines eagerly and the
    # unused ones leaked as "coroutine was never awaited" RuntimeWarnings.
    candidates = (
        (_user_from_session_token, session_cookie),
        (_user_from_jwt_token, jwt_cookie),
        (_user_from_jwt_token, bearer_token),
        (_user_from_session_token, bearer_token),
    )
    for resolver, token in candidates:
        if not token:
            continue
        user = await resolver(db, token)
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")


JWT_COOKIE_NAME = "auth_token"
JWT_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
SHARE_TOKEN_EXPIRE_DAYS = 7


def create_share_token(doc_type: str, doc_id: str, user_id: str) -> str:
    """Issue a short-lived signed token that lets anyone with the link download a PDF."""
    payload = {
        "kind": "share",
        "doc_type": doc_type,  # "summary" | "agreement"
        "doc_id": doc_id,
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=SHARE_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_share_token(token: str) -> Optional[dict]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        if data.get("kind") != "share":
            return None
        return data
    except jwt.PyJWTError:
        return None


def _set_jwt_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        max_age=JWT_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )


# ============ Routes ============
@router.post("/register", response_model=TokenResponse)
async def register(
    body: UserRegister,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    existing = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "email": body.email.lower(),
        "name": body.name,
        "hashed_password": hash_password(body.password),
        "auth_method": "jwt",
        "children": body.children or [],
        "custody_situation": body.custody_situation or "",
        "mediation_date": body.mediation_date,
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_jwt(user_id)
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(doc))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_jwt(user["user_id"])
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(user))


async def _fetch_emergent_oauth_data(session_id: str) -> dict:
    """Exchange Emergent OAuth session_id for the user data + session_token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id}
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    return r.json()


async def _upsert_oauth_user(
    db: AsyncIOMotorDatabase, email: str, name: str, picture: Optional[str]
) -> dict:
    """Create or update a user record from Google OAuth data."""
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"name": name, "picture": picture}},
        )
        user["name"] = name
        user["picture"] = picture
        return user

    user_doc = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": name,
        "picture": picture,
        "auth_method": "google",
        "hashed_password": None,
        "children": [],
        "custody_situation": "",
        "mediation_date": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    return user_doc


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )


@router.post("/google/session")
async def google_session(
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Exchange Emergent session_id -> session_token, create/update user, set cookie."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-ID")

    data = await _fetch_emergent_oauth_data(session_id)
    email = (data.get("email") or "").lower()
    name = data.get("name") or email
    picture = data.get("picture")
    session_token = data["session_token"]

    user = await _upsert_oauth_user(db, email, name, picture)

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one(
        {
            "user_id": user["user_id"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _set_session_cookie(response, session_token)
    return {"user": _serialize_user(user).dict(), "access_token": session_token}


@router.get("/me", response_model=UserPublic)
async def me(current=Depends(get_current_user)):
    return current


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_many({"session_token": token})
    response.delete_cookie("session_token", path="/")
    response.delete_cookie(JWT_COOKIE_NAME, path="/")
    return {"ok": True}


@router.delete("/account")
async def delete_account(
    request: Request,
    response: Response,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Permanently delete the authenticated user's account and ALL their data.

    Required by Google Play & Apple App Store for in-app account deletion.
    Wipes: users, user_sessions, prep_data, summaries, agreements,
    improvement_plans, mediator_emails, devices.
    """
    user_id = current.user_id
    collections = (
        "users",
        "user_sessions",
        "prep_data",
        "summaries",
        "agreements",
        "improvement_plans",
        "mediator_emails",
        "devices",
    )
    deleted = {}
    for name in collections:
        result = await db[name].delete_many({"user_id": user_id})
        deleted[name] = result.deleted_count
    # Make sure the user document itself is gone (queried by user_id above)
    await db.users.delete_one({"user_id": user_id})

    response.delete_cookie("session_token", path="/")
    response.delete_cookie(JWT_COOKIE_NAME, path="/")
    return {"ok": True, "deleted": deleted}


@router.patch("/profile", response_model=UserPublic)
async def update_profile(
    body: dict,
    request: Request,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    allowed = {"name", "children", "custody_situation", "mediation_date"}
    update = {k: v for k, v in body.items() if k in allowed}
    if update:
        await db.users.update_one({"user_id": current.user_id}, {"$set": update})
    user = await db.users.find_one({"user_id": current.user_id}, {"_id": 0})
    return _serialize_user(user)


# ============ Guest Sandbox ============
GUEST_LIFETIME_HOURS = int(os.environ.get("GUEST_LIFETIME_HOURS", "24"))
GUEST_RATE_LIMIT_PER_HOUR = int(os.environ.get("GUEST_RATE_LIMIT_PER_HOUR", "3"))


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/guest", response_model=TokenResponse)
async def start_guest_session(
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Spin up a temporary 24-hour guest account. Wizard works; premium
    features (AI summary, PDF, email, share) are gated behind /claim."""
    ip = _client_ip(request)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = await db.users.count_documents(
        {"is_guest": True, "guest_ip": ip, "created_at": {"$gte": one_hour_ago}}
    )
    if recent >= GUEST_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many demo sessions from this network. Please try again later or sign up.",
        )

    short = uuid.uuid4().hex[:8]
    user_id = f"guest_{short}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=GUEST_LIFETIME_HOURS)
    doc = {
        "user_id": user_id,
        "email": f"guest_{short}@demo.local",
        "name": "Demo user",
        "hashed_password": None,
        "auth_method": "guest",
        "is_guest": True,
        "guest_expires_at": expires_at.isoformat(),
        "guest_ip": ip,
        "children": [],
        "custody_situation": "",
        "mediation_date": None,
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_jwt(user_id)
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(doc))


@router.post("/claim", response_model=TokenResponse)
async def claim_guest_account(
    body: GuestClaimPayload,
    response: Response,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Convert the current guest session into a permanent account.
    All wizard data (prep_data, summaries, etc.) is keyed by user_id and
    therefore preserved automatically."""
    doc = await db.users.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc or not doc.get("is_guest"):
        raise HTTPException(status_code=400, detail="Not a guest session")

    email = body.email.lower()
    if await db.users.find_one({"email": email, "user_id": {"$ne": current.user_id}}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Email already registered")

    await db.users.update_one(
        {"user_id": current.user_id},
        {
            "$set": {
                "email": email,
                "name": body.name,
                "hashed_password": hash_password(body.password),
                "auth_method": "jwt",
            },
            "$unset": {
                "is_guest": "",
                "guest_expires_at": "",
                "guest_ip": "",
            },
        },
    )
    user = await db.users.find_one({"user_id": current.user_id}, {"_id": 0})
    token = create_jwt(current.user_id)
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(user))


def require_active_user(current=Depends(get_current_user)) -> UserPublic:
    """Like get_current_user but rejects guest sessions with 402 Payment Required.
    Use on endpoints gated behind sign-up (AI generation, PDF, email, share)."""
    if current.is_guest:
        raise HTTPException(
            status_code=402,
            detail="Save your work to unlock this feature. Create a free account to continue.",
        )
    return current


# ============ Magic Link Sign-In ============
MAGIC_LINK_LIFETIME_MINUTES = int(os.environ.get("MAGIC_LINK_LIFETIME_MINUTES", "15"))
MAGIC_LINK_RATE_LIMIT_PER_HOUR = int(os.environ.get("MAGIC_LINK_RATE_LIMIT_PER_HOUR", "5"))


def _frontend_origin(request: Request) -> str:
    """Best-effort detection of the origin to build the magic-link URL on."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        # strip path off referer
        from urllib.parse import urlparse
        p = urlparse(origin)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return os.environ.get("PUBLIC_APP_URL", "").rstrip("/") or "https://sacoparentsapp.online"


@router.post("/magic-link/request")
async def request_magic_link(
    body: MagicLinkRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Issue a short-lived sign-in token and email it.
    Always returns 200 so we don't leak which emails are registered."""
    email = body.email.lower().strip()

    # Rate limit per IP — same shape as guest endpoint
    ip = _client_ip(request)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = await db.magic_links.count_documents(
        {"ip": ip, "created_at": {"$gte": one_hour_ago}}
    )
    if recent >= MAGIC_LINK_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many sign-in links requested. Please try again later.",
        )

    user = await db.users.find_one({"email": email}, {"_id": 0})
    sent = False
    mode = "signin" if (user and not user.get("is_guest")) else "signup"

    raw_token = secrets.token_urlsafe(32)
    record = {
        "token": raw_token,
        "email": email,
        "mode": mode,
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_LIFETIME_MINUTES)).isoformat(),
        "used": False,
    }
    if mode == "signin":
        record["user_id"] = user["user_id"]

    await db.magic_links.insert_one(record)
    origin = _frontend_origin(request)
    if mode == "signin":
        link_url = f"{origin}/auth/magic?token={raw_token}"
    else:
        link_url = f"{origin}/auth/setup?token={raw_token}"

    try:
        if mode == "signin":
            send_magic_link(to_email=email, link_url=link_url, user_name=user.get("name"))
        else:
            send_setup_link(to_email=email, link_url=link_url)
        sent = True
    except EmailNotConfigured:
        await db.magic_links.delete_one({"token": raw_token})
        raise HTTPException(
            status_code=503,
            detail=(
                "Email sign-in isn't available right now. "
                "Please " + ("use your password instead." if mode == "signin" else "create an account directly.")
            ),
        )
    except EmailSendError as e:
        await db.magic_links.delete_one({"token": raw_token})
        raise HTTPException(status_code=502, detail=str(e))

    # Privacy: same shape whether signin or signup. The mode hint helps the UI
    # tailor the confirmation copy ("check your inbox to sign in" vs "...to set up").
    return {
        "ok": True,
        "sent": sent,
        "mode": mode,
        "message": (
            "If you already have an account, we sent a sign-in link. "
            "Otherwise, we sent a link to set up your account. It expires in 15 minutes."
        ),
    }


@router.post("/magic-link/consume", response_model=TokenResponse)
async def consume_magic_link(
    body: MagicLinkConsume,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    rec = await db.magic_links.find_one({"token": body.token}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired sign-in link.")
    if rec.get("mode") == "signup":
        raise HTTPException(
            status_code=400,
            detail="This link is for creating an account. Open it from your email to finish setup.",
        )
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="This sign-in link has already been used.")
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This sign-in link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid sign-in link.") from None

    user = await db.users.find_one({"user_id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=400, detail="Account no longer exists.")

    await db.magic_links.update_one({"token": body.token}, {"$set": {"used": True}})
    # Invalidate any other outstanding links for this user — single active link policy
    await db.magic_links.update_many(
        {"user_id": user["user_id"], "used": False, "token": {"$ne": body.token}},
        {"$set": {"used": True}},
    )
    token = create_jwt(user["user_id"])
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.get("/magic-link/preview")
async def preview_magic_link(
    token: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Validate a token and return the email it was issued for, so the
    /auth/setup page can pre-fill it and show context to the user.
    Does NOT mark the token as used."""
    rec = await db.magic_links.find_one({"token": token}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired link.")
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="This link has already been used.")
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid link.") from None
    return {"email": rec["email"], "mode": rec.get("mode", "signin")}


@router.post("/signup-from-token", response_model=TokenResponse)
async def signup_from_token(
    body: SignupFromToken,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new account using a verified email (via a magic link in signup mode).
    Idempotent against double-clicks: if the token was just used, returns the same user."""
    rec = await db.magic_links.find_one({"token": body.token}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired link.")
    if rec.get("mode") != "signup":
        raise HTTPException(status_code=400, detail="This link can't be used to create an account.")
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="This link has already been used.")
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid link.") from None

    email = rec["email"]
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing and not existing.get("is_guest"):
        raise HTTPException(status_code=400, detail="An account already exists for this email. Please sign in.")

    user_id = uuid.uuid4().hex
    doc = {
        "user_id": user_id,
        "email": email,
        "name": body.name.strip(),
        "hashed_password": hash_password(body.password),
        "auth_method": "jwt",
        "children": [],
        "custody_situation": "",
        "mediation_date": None,
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    await db.magic_links.update_one({"token": body.token}, {"$set": {"used": True}})
    token = create_jwt(user_id)
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(doc))
