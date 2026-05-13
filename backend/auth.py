"""Authentication: JWT (email/password) + Emergent Google session exchange."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import UserRegister, UserLogin, UserPublic, TokenResponse

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
    )


async def _user_by_id(db, user_id: Optional[str]) -> Optional[UserPublic]:
    if not user_id:
        return None
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return _serialize_user(doc) if doc else None


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

    # Try each credential source in order of preference.
    resolvers = (
        _user_from_session_token(db, request.cookies.get("session_token")),
        _user_from_jwt_token(db, request.cookies.get(JWT_COOKIE_NAME)),
        _user_from_jwt_token(db, bearer_token),
        _user_from_session_token(db, bearer_token),
    )
    for awaitable in resolvers:
        user = await awaitable
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")


JWT_COOKIE_NAME = "auth_token"
JWT_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


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
