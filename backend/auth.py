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


async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> UserPublic:
    """Resolve user from session_token cookie or Bearer token (JWT or session)."""
    db = request.app.state.db

    # Prefer cookie (Emergent session token)
    cookie_token = request.cookies.get("session_token")
    bearer_token = creds.credentials if creds else None

    # Try cookie -> session lookup
    if cookie_token:
        session = await db.user_sessions.find_one(
            {"session_token": cookie_token}, {"_id": 0}
        )
        if session:
            exp = session["expires_at"]
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > datetime.now(timezone.utc):
                user_doc = await db.users.find_one(
                    {"user_id": session["user_id"]}, {"_id": 0}
                )
                if user_doc:
                    return _serialize_user(user_doc)

    # Try bearer JWT
    if bearer_token:
        user_id = decode_jwt(bearer_token)
        if user_id:
            user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
            if user_doc:
                return _serialize_user(user_doc)
        # Or treat as session token
        session = await db.user_sessions.find_one(
            {"session_token": bearer_token}, {"_id": 0}
        )
        if session:
            user_doc = await db.users.find_one(
                {"user_id": session["user_id"]}, {"_id": 0}
            )
            if user_doc:
                return _serialize_user(user_doc)

    raise HTTPException(status_code=401, detail="Not authenticated")


# ============ Routes ============
@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister, db: AsyncIOMotorDatabase = Depends(get_db)):
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
    return TokenResponse(access_token=token, user=_serialize_user(doc))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_jwt(user["user_id"])
    return TokenResponse(access_token=token, user=_serialize_user(user))


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

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id}
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = (data.get("email") or "").lower()
    name = data.get("name") or email
    picture = data.get("picture")
    session_token = data["session_token"]

    # Upsert user
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
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
        user = user_doc
    else:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"name": name, "picture": picture}},
        )
        user["name"] = name
        user["picture"] = picture

    # Persist session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one(
        {
            "user_id": user["user_id"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Set cookie (cross-site safe)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
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
