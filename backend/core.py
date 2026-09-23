"""Shared runtime: env, database, logger, URL helpers and cross-module constants."""
from dotenv import load_dotenv, dotenv_values
from pathlib import Path

load_dotenv()  # platform/Kubernetes env vars take precedence

# The preview supervisor injects a stale APP_URL; the .env file carries the correct
# value in preview and the platform-managed value in production.
_APP_URL_FILE = dotenv_values(Path(__file__).resolve().parent / ".env").get("APP_URL")

import os
import uuid
import logging
from datetime import datetime, timezone
from html import escape

from motor.motor_asyncio import AsyncIOMotorClient

from email_utils import set_comm_logger, EMAIL_FROM_NAME

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
logger = logging.getLogger(__name__)
BUILD_ID = "2026-09-23.1"
logging.basicConfig(level=logging.INFO)

async def _log_communication(rec: dict) -> None:
    await db.communications.insert_one({"id": str(uuid.uuid4()), "at": datetime.now(timezone.utc).isoformat(), **rec})


set_comm_logger(_log_communication)

WEBHOOK_CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]

EXTERNAL_APP_URL = os.environ["SACOPARENTS_APP_URL"].rstrip("/")
INTEGRATION_SECRET = os.environ["INTEGRATION_SHARED_SECRET"]
APP_ASSESSMENT_URL = (os.environ.get("SACOPARENTS_APP_ASSESSMENT_URL") or EXTERNAL_APP_URL).rstrip("/")

def invite_link(token: str) -> str:
    return f"{APP_ASSESSMENT_URL}/?invite={token}"

PRO_ROLES = ("professional", "admin")

def app_url():
    return (_APP_URL_FILE or os.environ["APP_URL"]).rstrip("/")

INVITE_EXPIRY_DAYS = 14
INVITE_EXPIRING_SOON_DAYS = 4
PRO_INVITE_TTL_HOURS = 72

def _pro_email_wrap(inner: str) -> str:
    return ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            + inner + f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>')

def _parse_iso(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except Exception:
        return None


async def _log_lifecycle(rid: str, action: str, user: dict) -> None:
    await db.access_events.insert_one({"report_id": rid, "kind": "lifecycle", "action": action, "at": datetime.now(timezone.utc).isoformat(),
                                       "by": user["_id"], "by_name": user.get("name", ""), "by_role": "Assigned professional"})
