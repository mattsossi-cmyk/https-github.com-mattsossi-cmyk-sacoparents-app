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

import secure_docs
from privacy_consent import consent_fields, has_current_consent, log_consent
from ai_notice import has_ai_notice

from models import UserRegister, UserLogin, UserPublic, TokenResponse, GuestClaimPayload, MagicLinkRequest, MagicLinkConsume, SignupFromToken, PasswordResetRequest, PasswordResetConfirm, EmailVerifyConfirm, EmailCodeSend, EmailCodeConfirm, PasswordResetCodeConfirm
from email_service import send_magic_link, send_setup_link, send_password_reset_link, send_verification_link, send_verification_code, send_password_reset_code, EmailNotConfigured, EmailSendError

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
        email_verified=bool(doc.get("email_verified", False)),
        email_bounced=bool(doc.get("email_bounced", False)),
        email_complained=bool(doc.get("email_complained", False)),
        consent_current=has_current_consent(doc),
        ai_notice_current=has_ai_notice(doc),
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
    # Suspended accounts cannot use the app — treated as logged-out.
    if doc.get("suspended"):
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
            secure_docs.set_sender(user, _frontend_origin(request))
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")


JWT_COOKIE_NAME = "auth_token"
JWT_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
SHARE_TOKEN_EXPIRE_DAYS = 7
# Allowed expiry windows for user-selectable share-link durations.
# Must match the {1, 7, 14, 30} choice set advertised by the joint
# artefact route dialogs (joint_agreement_routes / joint_professional_
# report_routes) and the frontend share-link modals. Missing values
# would silently downgrade to SHARE_TOKEN_EXPIRE_DAYS.
# None = "never" (still revocable via the revocation list).
SHARE_TOKEN_WINDOWS = {1, 7, 14, 30, None}


def create_share_token(
    doc_type: str,
    doc_id: str,
    user_id: str,
    excluded_sections: Optional[list] = None,
    expire_days: Optional[int] = SHARE_TOKEN_EXPIRE_DAYS,
) -> str:
    """Issue a signed token that lets anyone with the link download a PDF.

    `expire_days` controls the JWT `exp` claim. None = no expiry (still
    revocable via `revoked_share_tokens` in Mongo).

    `excluded_sections` snapshots the user's section-visibility choice at share
    time so revoking or changing preferences later doesn't retroactively alter
    already-shared links. Recipients see exactly the view the parent chose.

    Each token carries a unique `jti` so it can be revoked individually.
    """
    if expire_days not in SHARE_TOKEN_WINDOWS:
        expire_days = SHARE_TOKEN_EXPIRE_DAYS
    now = datetime.now(timezone.utc)
    payload = {
        "kind": "share",
        "doc_type": doc_type,  # "cp_report" | "summary" | "agreement" | "safety" | "edu_deep_share"
        "doc_id": doc_id,
        "sub": user_id,
        "jti": uuid.uuid4().hex,
        "iat": now,
    }
    if expire_days is not None:
        payload["exp"] = now + timedelta(days=int(expire_days))
    if excluded_sections:
        # Store as a stable sorted list — keeps the token deterministic for tests.
        payload["ex"] = sorted({str(x) for x in excluded_sections})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_share_token(token: str) -> Optional[dict]:
    try:
        # `exp` claim is optional (no-expiry links). PyJWT verifies it when present.
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO],
                          options={"require": ["kind"]})
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
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    consent = consent_fields(body.ack_privacy_notice, body.consent_sensitive_info)
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
        "email_verified": False,
        # HB 300 §181.154 acknowledgement — captured at signup by
        # accepting the Privacy Practices + HB 300 Notice referenced
        # on the sign-up page. Marketing communications default OFF
        # per §181.152 (affirmative opt-in required).
        "hb300_ack_version": "2026-02-21",
        "hb300_ack_at":      datetime.now(timezone.utc).isoformat(),
        "marketing_opt_in":  False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **consent,
    }
    await db.users.insert_one(doc)
    await log_consent(db, doc, consent, "register", request)

    # Best-effort: send a verification email. Failure here doesn't block signup.
    try:
        await _issue_verification_link(
            db,
            user_id=user_id,
            email=doc["email"],
            name=body.name,
            origin=_frontend_origin(request),
        )
    except Exception:  # pragma: no cover - never block signup
        import logging as _logging
        _logging.getLogger(__name__).exception("Failed to issue verification link during register")

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
    if user.get("suspended"):
        raise HTTPException(
            status_code=403,
            detail="This account is suspended. Please contact support.",
        )
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
        "email_verified": True,
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
    """Permanently delete the authenticated user's account and ALL their data (see account_purge.py).

    Required by Google Play & Apple App Store for in-app account deletion.
    """
    from account_purge import purge_account

    deleted = await purge_account(db, current.user_id, current.email)

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
# 1 year by default — matches the original spec's "1-year Demo Sandbox". Override
# via the GUEST_LIFETIME_HOURS env var if needed.
GUEST_LIFETIME_HOURS = int(os.environ.get("GUEST_LIFETIME_HOURS", str(24 * 365)))
GUEST_RATE_LIMIT_PER_HOUR = int(os.environ.get("GUEST_RATE_LIMIT_PER_HOUR", "30"))


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
    """Spin up a 1-year demo guest account. Wizard works; premium
    features behave the same as a permanent account — the demo is full
    read+write, it just expires after the lifetime. After expiry the user
    can `/claim` to keep their data."""
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
    request: Request,
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
    consent = consent_fields(body.ack_privacy_notice, body.consent_sensitive_info)

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
                **consent,
            },
            "$unset": {
                "is_guest": "",
                "guest_expires_at": "",
                "guest_ip": "",
            },
        },
    )
    user = await db.users.find_one({"user_id": current.user_id}, {"_id": 0})
    await log_consent(db, user, consent, "claim", request)
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
    # Magic-link sign-in proves the user controls this email — mark it verified.
    if not user.get("email_verified"):
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"email_verified": True}},
        )
        user["email_verified"] = True
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
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new account using a verified email (via a magic link in signup mode).
    Idempotent against double-clicks: if the token was just used, returns the same user."""
    consent = consent_fields(body.ack_privacy_notice, body.consent_sensitive_info)
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
        "email_verified": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **consent,
    }
    await db.users.insert_one(doc)
    await log_consent(db, doc, consent, "magic_link_setup", request)
    await db.magic_links.update_one({"token": body.token}, {"$set": {"used": True}})
    token = create_jwt(user_id)
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(doc))



# ============ Password Reset ============
@router.post("/password-reset/request")
async def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Email a short-lived password-reset link.
    Always returns 200 (privacy: don't leak which emails exist)."""
    email = body.email.lower().strip()

    # Rate limit per IP — reuses the magic_links collection
    ip = _client_ip(request)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = await db.magic_links.count_documents(
        {"ip": ip, "created_at": {"$gte": one_hour_ago}}
    )
    if recent >= MAGIC_LINK_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many reset requests. Please try again later.",
        )

    user = await db.users.find_one({"email": email}, {"_id": 0})
    # Only send if a real (non-guest) account exists.
    if not user or user.get("is_guest") or user.get("suspended"):
        # Privacy: pretend we sent it.
        return {
            "ok": True,
            "sent": False,
            "message": "If an account exists for that email, we sent a reset link. It expires in 15 minutes.",
        }

    raw_token = secrets.token_urlsafe(32)
    record = {
        "token": raw_token,
        "email": email,
        "mode": "reset",
        "ip": ip,
        "user_id": user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_LIFETIME_MINUTES)).isoformat(),
        "used": False,
    }
    await db.magic_links.insert_one(record)
    origin = _frontend_origin(request)
    link_url = f"{origin}/reset-password?token={raw_token}"

    try:
        send_password_reset_link(to_email=email, link_url=link_url, user_name=user.get("name"))
        # Log the EVENT ONLY — never the token or link. Anyone with log
        # access could otherwise take over the account within 15 minutes.
        import logging as _logging
        _logging.getLogger(__name__).info(
            "Password reset link sent for user_id=%s", user.get("user_id"),
        )
    except EmailNotConfigured:
        # Same non-leaky log line. Preview/dev environments should
        # retrieve the token from the DB `magic_links` collection, not
        # from application logs.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Password reset requested but SMTP not configured for user_id=%s "
            "(token stored in magic_links)", user.get("user_id"),
        )
    except EmailSendError as e:
        # Never log the reset link or token — anyone with log access could
        # take over the account within the 15-minute window. Log user_id +
        # outcome only. Token is retrievable from the magic_links collection.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Password reset email send failed for user_id=%s (error_type=%s)",
            user.get("user_id"),
            type(e).__name__,
        )

    return {
        "ok": True,
        "sent": True,
        "message": "If an account exists for that email, we sent a reset link. It expires in 15 minutes.",
    }


@router.post("/password-reset/confirm", response_model=TokenResponse)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Set a new password using a reset token, then sign the user in."""
    rec = await db.magic_links.find_one({"token": body.token}, {"_id": 0})
    if not rec or rec.get("mode") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="This reset link has already been used.")
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This reset link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid reset link.") from None

    user = await db.users.find_one({"user_id": rec["user_id"]}, {"_id": 0})
    if not user or user.get("suspended"):
        raise HTTPException(status_code=400, detail="Account not available.")

    # Update password; ensure user can authenticate via JWT going forward.
    # Password reset via emailed link proves email ownership, so mark verified.
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "hashed_password": hash_password(body.password),
                "auth_method": user.get("auth_method") or "jwt",
                "password_changed_at": datetime.now(timezone.utc).isoformat(),
                "email_verified": True,
            }
        },
    )
    # Burn this token + invalidate any other outstanding links for this user.
    await db.magic_links.update_one({"token": body.token}, {"$set": {"used": True}})
    await db.magic_links.update_many(
        {"user_id": user["user_id"], "used": False, "token": {"$ne": body.token}},
        {"$set": {"used": True}},
    )

    # Sign them in.
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    token = create_jwt(user["user_id"])
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(fresh))


@router.get("/password-reset/preview")
async def preview_password_reset(
    token: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Validate a reset token (without consuming it) so the page can show the email."""
    rec = await db.magic_links.find_one({"token": token}, {"_id": 0})
    if not rec or rec.get("mode") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="This reset link has already been used.")
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This reset link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid reset link.") from None
    return {"email": rec["email"]}



# ============ Email Verification ============
EMAIL_VERIFY_LIFETIME_HOURS = 24


async def _issue_verification_link(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    email: str,
    name: Optional[str],
    origin: str,
) -> tuple[bool, Optional[str]]:
    """Create a verification token, persist it, and try to email it.
    Returns (sent, fallback_link). `sent` is True only if SMTP send succeeded."""
    raw_token = secrets.token_urlsafe(32)
    record = {
        "token": raw_token,
        "email": email.lower(),
        "user_id": user_id,
        "mode": "verify",
        "used": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFY_LIFETIME_HOURS)
        ).isoformat(),
    }
    await db.magic_links.insert_one(record)
    link_url = f"{origin}/verify-email?token={raw_token}"
    try:
        send_verification_link(to_email=email, link_url=link_url, user_name=name)
        return True, None
    except EmailNotConfigured:
        # Log user_id + outcome only. Token is available in magic_links
        # collection for dev/preview retrieval — never log the link itself.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Verification link generated but SMTP not configured for user_id=%s "
            "(token stored in magic_links)",
            user_id,
        )
        return False, link_url
    except EmailSendError as e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Verification email send failed for user_id=%s (error_type=%s)",
            user_id,
            type(e).__name__,
        )
        return False, link_url


@router.post("/verify-email/send")
async def send_verify_email(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send (or re-send) the email verification link to the signed-in user."""
    if current.is_guest:
        raise HTTPException(status_code=400, detail="Guest accounts don't have email verification.")
    if current.email_verified:
        return {"ok": True, "sent": False, "already_verified": True, "message": "Email already verified."}

    # Lightweight rate limit: at most 3 verification links per user per hour.
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = await db.magic_links.count_documents(
        {"user_id": current.user_id, "mode": "verify", "created_at": {"$gte": one_hour_ago}}
    )
    if recent >= 3:
        raise HTTPException(status_code=429, detail="Too many verification emails. Please try again later.")

    origin = _frontend_origin(request)
    user_doc = await db.users.find_one({"user_id": current.user_id}, {"_id": 0})
    sent, _link = await _issue_verification_link(
        db,
        user_id=current.user_id,
        email=current.email,
        name=(user_doc or {}).get("name"),
        origin=origin,
    )
    return {
        "ok": True,
        "sent": sent,
        "message": (
            "Verification email sent. It expires in 24 hours."
            if sent
            else "Verification link generated but email is not configured in this environment."
        ),
    }


@router.post("/verify-email/confirm")
async def confirm_verify_email(
    body: EmailVerifyConfirm,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Consume a verification token and mark the user as email_verified."""
    rec = await db.magic_links.find_one({"token": body.token}, {"_id": 0})
    if not rec or rec.get("mode") != "verify":
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
    if rec.get("used"):
        # Idempotent: a refreshed page or double-click shouldn't show an error.
        return {"ok": True, "already_used": True}
    exp = rec.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This verification link has expired.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid verification link.") from None

    await db.users.update_one(
        {"user_id": rec["user_id"]},
        {"$set": {"email_verified": True, "email_verified_at": datetime.now(timezone.utc).isoformat()}},
    )
    await db.magic_links.update_one({"token": body.token}, {"$set": {"used": True}})
    return {"ok": True, "email": rec.get("email")}



# ============================================================================
# 6-digit code flows (in-app entry, no email link required)
# ----------------------------------------------------------------------------
# These endpoints layer on top of the existing token-based `/verify-email/*`
# and `/password-reset/*` flows. Codes are stored bcrypt-hashed in the same
# `magic_links` collection with distinct modes so both flows can coexist.
# The user experience: request → receive 6 digits by email → type them into
# the app. No link click required.
# ============================================================================

CODE_LIFETIME_MINUTES = 15
CODE_RATE_LIMIT_PER_HOUR = 5
CODE_MAX_ATTEMPTS = 5


def _generate_numeric_code(digits: int = 6) -> str:
    """Cryptographically-secure numeric OTP. Leading zeros preserved."""
    upper = 10 ** digits
    return f"{secrets.randbelow(upper):0{digits}d}"


def _hash_code(code: str) -> str:
    return pwd_ctx.hash(code)


def _verify_code(plain: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(plain, hashed)
    except Exception:  # pragma: no cover — defensive
        return False


async def _issue_email_code(
    db: AsyncIOMotorDatabase,
    *,
    mode: str,
    email: str,
    user_id: str,
    ip: str,
) -> str:
    """Mint a fresh 6-digit code, invalidate any prior unused codes of the
    same mode for this user, and persist the hashed record. Returns the
    plaintext code so the caller can email it."""
    # Burn all previously-unused codes of this mode for this user so a
    # replay from an older email cannot be used after a new request.
    await db.magic_links.update_many(
        {"user_id": user_id, "mode": mode, "used": False},
        {"$set": {"used": True, "invalidated_at": datetime.now(timezone.utc).isoformat()}},
    )
    code = _generate_numeric_code(6)
    record = {
        "token": secrets.token_urlsafe(16),  # opaque id — never emailed
        "mode": mode,
        "email": email,
        "user_id": user_id,
        "code_hash": _hash_code(code),
        "attempts": 0,
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=CODE_LIFETIME_MINUTES)
        ).isoformat(),
        "used": False,
    }
    await db.magic_links.insert_one(record)
    return code


async def _lookup_active_code(
    db: AsyncIOMotorDatabase,
    *,
    mode: str,
    email: str,
) -> Optional[dict]:
    """Return the most-recent unused-and-unexpired code record for
    (email, mode), or None."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return await db.magic_links.find_one(
        {
            "mode": mode,
            "email": email,
            "used": False,
            "expires_at": {"$gt": now_iso},
        },
        {"_id": 0},
        sort=[("created_at", -1)],
    )


@router.post("/verify-email/send-code")
async def send_verify_email_code(
    body: EmailCodeSend,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send a 6-digit email-verification code to the account matching
    `body.email`. Always returns 200 (privacy: don't leak account existence).
    """
    email = body.email.lower().strip()
    ip = _client_ip(request)

    # Rate limit on IP AND on target email, so two parents behind the same
    # NAT (shared home Wi-Fi) don't lock each other out when each requests
    # their own verification code. We only 429 when BOTH signals are hot:
    # a single IP hammering many accounts still hits the IP cap, but the
    # common "co-parents sharing an egress" case survives.
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent_by_ip = await db.magic_links.count_documents(
        {"ip": ip, "mode": "verify_code", "created_at": {"$gte": one_hour_ago}}
    )
    recent_by_email = await db.magic_links.count_documents(
        {"email": email, "mode": "verify_code", "created_at": {"$gte": one_hour_ago}}
    )
    if recent_by_ip >= CODE_RATE_LIMIT_PER_HOUR and recent_by_email >= CODE_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many verification requests. Please try again later.",
        )

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or user.get("is_guest") or user.get("suspended"):
        return {
            "ok": True,
            "sent": False,
            "message": "If an account exists for that email, we sent a 6-digit code. It expires in 15 minutes.",
        }
    if user.get("email_verified"):
        return {
            "ok": True,
            "sent": False,
            "already_verified": True,
            "message": "This email is already verified.",
        }

    code = await _issue_email_code(
        db, mode="verify_code", email=email, user_id=user["user_id"], ip=ip
    )
    try:
        send_verification_code(to_email=email, code=code, user_name=user.get("name"))
        return {
            "ok": True,
            "sent": True,
            "message": "We sent a 6-digit code. It expires in 15 minutes.",
        }
    except EmailNotConfigured:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Verify code generated but SMTP not configured for user_id=%s "
            "(code stored in magic_links)", user.get("user_id"),
        )
        return {
            "ok": True,
            "sent": False,
            "message": "Code generated but email is not configured in this environment.",
        }
    except EmailSendError as e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Verify code email send failed for user_id=%s (error_type=%s)",
            user.get("user_id"), type(e).__name__,
        )
        return {
            "ok": True,
            "sent": False,
            "message": "Could not send code right now. Please try again in a moment.",
        }


@router.post("/verify-email/confirm-code")
async def confirm_verify_email_code(
    body: EmailCodeConfirm,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Consume a 6-digit code and mark the user email_verified."""
    email = body.email.lower().strip()
    code = body.code.strip()

    rec = await _lookup_active_code(db, mode="verify_code", email=email)
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    if rec.get("attempts", 0) >= CODE_MAX_ATTEMPTS:
        await db.magic_links.update_one(
            {"token": rec["token"]}, {"$set": {"used": True}}
        )
        raise HTTPException(
            status_code=400,
            detail="Too many attempts on this code. Request a new one.",
        )

    if not _verify_code(code, rec.get("code_hash", "")):
        await db.magic_links.update_one(
            {"token": rec["token"]}, {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    await db.users.update_one(
        {"user_id": rec["user_id"]},
        {
            "$set": {
                "email_verified": True,
                "email_verified_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    await db.magic_links.update_one({"token": rec["token"]}, {"$set": {"used": True}})
    return {"ok": True, "email": email}


@router.post("/password-reset/request-code")
async def request_password_reset_code(
    body: EmailCodeSend,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send a 6-digit password-reset code. Always returns 200 (privacy)."""
    email = body.email.lower().strip()
    ip = _client_ip(request)

    # See `send_verify_email_code` — same shared-NAT rationale.
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent_by_ip = await db.magic_links.count_documents(
        {"ip": ip, "mode": "reset_code", "created_at": {"$gte": one_hour_ago}}
    )
    recent_by_email = await db.magic_links.count_documents(
        {"email": email, "mode": "reset_code", "created_at": {"$gte": one_hour_ago}}
    )
    if recent_by_ip >= CODE_RATE_LIMIT_PER_HOUR and recent_by_email >= CODE_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many reset requests. Please try again later.",
        )

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or user.get("is_guest") or user.get("suspended"):
        return {
            "ok": True,
            "sent": False,
            "message": "If an account exists for that email, we sent a 6-digit code. It expires in 15 minutes.",
        }

    code = await _issue_email_code(
        db, mode="reset_code", email=email, user_id=user["user_id"], ip=ip
    )
    try:
        send_password_reset_code(to_email=email, code=code, user_name=user.get("name"))
        import logging as _logging
        _logging.getLogger(__name__).info(
            "Password reset code sent for user_id=%s", user.get("user_id"),
        )
    except EmailNotConfigured:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Reset code generated but SMTP not configured for user_id=%s "
            "(code stored in magic_links)", user.get("user_id"),
        )
    except EmailSendError as e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Reset code email send failed for user_id=%s (error_type=%s)",
            user.get("user_id"), type(e).__name__,
        )

    return {
        "ok": True,
        "sent": True,
        "message": "If an account exists for that email, we sent a 6-digit code. It expires in 15 minutes.",
    }


@router.post("/password-reset/confirm-code", response_model=TokenResponse)
async def confirm_password_reset_code(
    body: PasswordResetCodeConfirm,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Verify the 6-digit code, set a new password, sign the user in."""
    email = body.email.lower().strip()
    code = body.code.strip()

    rec = await _lookup_active_code(db, mode="reset_code", email=email)
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    if rec.get("attempts", 0) >= CODE_MAX_ATTEMPTS:
        await db.magic_links.update_one(
            {"token": rec["token"]}, {"$set": {"used": True}}
        )
        raise HTTPException(
            status_code=400,
            detail="Too many attempts on this code. Request a new one.",
        )

    if not _verify_code(code, rec.get("code_hash", "")):
        await db.magic_links.update_one(
            {"token": rec["token"]}, {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    user = await db.users.find_one({"user_id": rec["user_id"]}, {"_id": 0})
    if not user or user.get("suspended"):
        raise HTTPException(status_code=400, detail="Account not available.")

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "hashed_password": hash_password(body.password),
                "auth_method": user.get("auth_method") or "jwt",
                "password_changed_at": datetime.now(timezone.utc).isoformat(),
                "email_verified": True,
            }
        },
    )
    # Burn this code + any other outstanding auth codes/links for this user
    # so an intercepted older code can't be replayed after the reset.
    await db.magic_links.update_one({"token": rec["token"]}, {"$set": {"used": True}})
    await db.magic_links.update_many(
        {"user_id": user["user_id"], "used": False, "token": {"$ne": rec["token"]}},
        {"$set": {"used": True}},
    )

    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    token = create_jwt(user["user_id"])
    _set_jwt_cookie(response, token)
    return TokenResponse(access_token=token, user=_serialize_user(fresh))
