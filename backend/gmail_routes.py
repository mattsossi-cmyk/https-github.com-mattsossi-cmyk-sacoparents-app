"""Gmail integration routes: OAuth 2.0 connect + inbox/search/send.

Users grant this app permission via Google OAuth to access their own Gmail
inbox and send email on their behalf. Refresh tokens are stored encrypted
(Fernet) in Mongo so we never keep raw credentials at rest.

Endpoints (all under /api):
  GET  /oauth/gmail/login       — start OAuth flow (JSON with auth_url)
  GET  /oauth/gmail/callback    — Google redirects here with ?code&state
  GET  /gmail/status            — is the current user connected?
  POST /gmail/disconnect        — revoke + wipe tokens
  GET  /gmail/messages          — list inbox (optional q=... for search)
  GET  /gmail/messages/{msg_id} — full message (subject, from, body)
  POST /gmail/send              — compose & send a new email
"""
import base64
import logging
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gmail"])

# ---- Config ----------------------------------------------------------------

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GMAIL_TOKEN_ENC_KEY = os.environ.get("GMAIL_TOKEN_ENC_KEY", "")

# Scopes: read + send + label management + profile email.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Publicly reachable callback URL. Set PUBLIC_API_URL to override in prod.
def _api_base_url(request: Request) -> str:
    override = os.environ.get("PUBLIC_API_URL")
    if override:
        return override.rstrip("/")
    # Fallback: construct from request. Kubernetes ingress terminates TLS so we
    # force https.
    host = request.headers.get("host", "")
    if not host:
        return ""
    return f"https://{host}"


def _redirect_uri(request: Request) -> str:
    return f"{_api_base_url(request)}/api/oauth/gmail/callback"


def _frontend_origin(request: Request) -> str:
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        from urllib.parse import urlparse
        p = urlparse(origin)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return os.environ.get("PUBLIC_APP_URL", "").rstrip("/") or "https://sacoparentsapp.online"


def _fernet() -> Fernet:
    if not GMAIL_TOKEN_ENC_KEY:
        raise HTTPException(status_code=503, detail="Gmail token encryption key not configured")
    try:
        return Fernet(GMAIL_TOKEN_ENC_KEY.encode())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Invalid GMAIL_TOKEN_ENC_KEY: {e}") from e


def _require_google_creds():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on this server.",
        )


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


# ---- Token storage ---------------------------------------------------------

def _encrypt(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return _fernet().encrypt(text.encode()).decode()


def _decrypt(cipher: Optional[str]) -> Optional[str]:
    if not cipher:
        return None
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except InvalidToken:
        return None


async def _save_tokens(db: AsyncIOMotorDatabase, user_id: str, creds: Credentials, google_email: Optional[str]) -> None:
    expires = creds.expiry
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    await db.gmail_tokens.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "access_token_enc": _encrypt(creds.token),
                "refresh_token_enc": _encrypt(creds.refresh_token),
                "expires_at": (expires or datetime.now(timezone.utc)).isoformat(),
                "google_email": google_email,
                "scopes": list(creds.scopes or GMAIL_SCOPES),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )


async def _load_credentials(db: AsyncIOMotorDatabase, user_id: str) -> Credentials:
    doc = await db.gmail_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Gmail not connected. Please connect your account first.")

    access_token = _decrypt(doc.get("access_token_enc"))
    refresh_token = _decrypt(doc.get("refresh_token_enc"))

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=doc.get("scopes") or GMAIL_SCOPES,
    )

    # Refresh if expired.
    expires_iso = doc.get("expires_at")
    try:
        expires = datetime.fromisoformat(expires_iso) if expires_iso else datetime.now(timezone.utc)
    except (ValueError, TypeError):
        expires = datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expires - timedelta(seconds=60):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Gmail session expired. Please reconnect.")
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:  # noqa: BLE001
            logger.warning("Gmail token refresh failed for %s: %s", user_id, e)
            raise HTTPException(status_code=401, detail="Gmail session expired. Please reconnect.") from e
        await _save_tokens(db, user_id, creds, doc.get("google_email"))

    return creds


# ---- OAuth: start & callback ----------------------------------------------

@router.get("/oauth/gmail/login")
async def gmail_login(
    request: Request,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the Google consent URL. Frontend does window.location = auth_url.

    We persist a short-lived state token mapped to the user_id so the callback
    can identify who's connecting (the callback has no auth headers)."""
    _require_google_creds()
    _fernet()  # ensure enc key is valid before starting flow

    flow = Flow.from_client_config(_client_config(), scopes=GMAIL_SCOPES, redirect_uri=_redirect_uri(request))

    state = secrets.token_urlsafe(32)
    await db.gmail_oauth_states.insert_one({
        "state": state,
        "user_id": current.user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "origin": _frontend_origin(request),
    })

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",  # ensure we get refresh_token
        include_granted_scopes="true",
        state=state,
    )
    return {"auth_url": auth_url}


@router.get("/oauth/gmail/callback")
async def gmail_callback(
    request: Request,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Google redirects here after user consents. Exchange code -> tokens,
    encrypt & store, then bounce user back to the frontend Gmail page."""
    if error:
        return RedirectResponse(
            f"{_frontend_origin(request)}/gmail?connected=false&error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state")

    state_doc = await db.gmail_oauth_states.find_one({"state": state}, {"_id": 0})
    if not state_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    exp = state_doc.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="OAuth state expired. Please try again.")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid OAuth state") from None
    await db.gmail_oauth_states.delete_one({"state": state})

    user_id = state_doc["user_id"]
    frontend = state_doc.get("origin") or _frontend_origin(request)

    _require_google_creds()
    flow = Flow.from_client_config(_client_config(), scopes=GMAIL_SCOPES, redirect_uri=_redirect_uri(request))

    try:
        with warnings.catch_warnings():
            # Google reorders scopes; suppress the noisy warning.
            warnings.simplefilter("ignore")
            flow.fetch_token(code=code)
    except Exception as e:  # noqa: BLE001
        logger.exception("Gmail token exchange failed for user=%s", user_id)
        return RedirectResponse(
            f"{frontend}/gmail?connected=false&error=token_exchange_failed",
            status_code=302,
        )

    creds = flow.credentials

    # Fetch the Google-side email address for display.
    google_email = None
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        google_email = profile.get("emailAddress")
    except HttpError as e:
        logger.warning("Could not fetch Gmail profile for user=%s: %s", user_id, e)

    await _save_tokens(db, user_id, creds, google_email)

    return RedirectResponse(f"{frontend}/gmail?connected=true", status_code=302)


# ---- Status / disconnect ---------------------------------------------------

@router.get("/gmail/status")
async def gmail_status(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.gmail_tokens.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc:
        return {"connected": False}
    return {
        "connected": True,
        "google_email": doc.get("google_email"),
        "scopes": doc.get("scopes", []),
        "updated_at": doc.get("updated_at"),
    }


@router.post("/gmail/disconnect")
async def gmail_disconnect(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.gmail_tokens.delete_many({"user_id": current.user_id})
    return {"ok": True}


# ---- Inbox / search / read -------------------------------------------------

def _header(headers: list, name: str) -> str:
    for h in headers or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_body(payload: dict) -> str:
    """Walk the payload MIME tree and return the best plain-text body."""
    if not payload:
        return ""

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data and mime in ("text/plain", "text/html"):
            try:
                text = base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
                return (mime, text)
            except Exception:  # noqa: BLE001
                return None
        for sub in part.get("parts") or []:
            result = walk(sub)
            if result:
                return result
        return None

    result = walk(payload)
    if not result:
        return ""
    mime, text = result
    if mime == "text/html":
        # Very light HTML strip. Full parsing not needed for preview.
        import re
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@router.get("/gmail/messages")
async def list_messages(
    q: Optional[str] = Query(default=None, description="Gmail search query, e.g. 'from:alice@example.com'"),
    max_results: int = Query(default=25, ge=1, le=100),
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    creds = await _load_credentials(db, current.user_id)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    try:
        list_result = service.users().messages().list(
            userId="me",
            q=q or None,
            maxResults=max_results,
        ).execute()
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status if e.resp else 500, detail=f"Gmail error: {e}") from e

    ids = [m["id"] for m in list_result.get("messages", [])]
    messages = []
    for mid in ids:
        try:
            meta = service.users().messages().get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
        except HttpError as e:
            logger.warning("Skipping message %s: %s", mid, e)
            continue
        headers = meta.get("payload", {}).get("headers", [])
        messages.append({
            "id": meta["id"],
            "thread_id": meta.get("threadId"),
            "snippet": meta.get("snippet", ""),
            "from": _header(headers, "From"),
            "to": _header(headers, "To"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "unread": "UNREAD" in (meta.get("labelIds") or []),
        })

    return {"messages": messages, "query": q or ""}


@router.get("/gmail/messages/{msg_id}")
async def get_message(
    msg_id: str,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    creds = await _load_credentials(db, current.user_id)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status if e.resp else 500, detail=f"Gmail error: {e}") from e

    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "snippet": msg.get("snippet", ""),
        "from": _header(headers, "From"),
        "to": _header(headers, "To"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "body": _extract_body(msg.get("payload", {})),
        "labels": msg.get("labelIds", []),
    }


# ---- Send ------------------------------------------------------------------

class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=50000)
    cc: Optional[str] = None
    thread_id: Optional[str] = None


@router.post("/gmail/send")
async def send_email(
    body: SendEmailRequest,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    creds = await _load_credentials(db, current.user_id)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEMultipart("alternative")
    msg["To"] = body.to
    if body.cc:
        msg["Cc"] = body.cc
    msg["Subject"] = body.subject
    msg.attach(MIMEText(body.body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if body.thread_id:
        payload["threadId"] = body.thread_id

    try:
        sent = service.users().messages().send(userId="me", body=payload).execute()
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status if e.resp else 500, detail=f"Gmail error: {e}") from e

    return {"ok": True, "id": sent.get("id"), "thread_id": sent.get("threadId")}
