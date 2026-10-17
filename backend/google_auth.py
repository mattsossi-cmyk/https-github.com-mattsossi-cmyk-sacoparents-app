"""Emergent-managed Google sign-in. Existing professional/admin accounts only (matched by email); never creates accounts; password login unchanged."""
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from core import db, logger

SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
GOOGLE_ROLES = ("professional", "admin")


class GoogleSessionIn(BaseModel):
    session_id: str


async def resolve_google_user(email: str, ip: str = "") -> dict:
    """Existing professional/admin by email only. Never creates an account."""
    user = await db.users.find_one({"email": email})
    if not user or user.get("role") not in GOOGLE_ROLES:
        await db.login_attempts.insert_one({"email": email, "method": "google", "ok": False, "at": datetime.now(timezone.utc).isoformat(), "ip": ip})
        raise HTTPException(status_code=403, detail="Google sign-in is available for existing professional and admin accounts only. Parents sign in with their invitation code and password.")
    if user.get("role") == "professional" and not user.get("approved"):
        raise HTTPException(status_code=403, detail="Your professional account is awaiting approval.")
    return user


def build_router(set_auth_cookies, public_user) -> APIRouter:
    r = APIRouter()

    @r.post("/auth/google/session")
    async def google_session(body: GoogleSessionIn, request: Request, response: Response):
        if not body.session_id.strip():
            raise HTTPException(status_code=400, detail="Missing session id")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(SESSION_DATA_URL, headers={"X-Session-ID": body.session_id.strip()})
        except Exception:
            logger.warning("google session-data unreachable")
            raise HTTPException(status_code=502, detail="Google sign-in is temporarily unavailable. Please use your password.")
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
        data = resp.json()
        email = (data.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=401, detail="Google did not return an email address.")
        user = await resolve_google_user(email, request.client.host if request.client else "")
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"google_linked_at": datetime.now(timezone.utc).isoformat(), "google_picture": data.get("picture", "")}})
        set_auth_cookies(response, user["_id"], user["email"])
        return public_user(user)

    @r.get("/auth/google/config")
    async def google_config():
        return {"enabled": os.environ.get("GOOGLE_SIGNIN", "true").lower() == "true", "roles": list(GOOGLE_ROLES)}

    return r
