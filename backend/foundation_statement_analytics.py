"""Foundation Statement — recipient open analytics.

Tracks each time someone hits `GET /foundation-statement/shared/{token}`
so the sender can see a soft "3 opens · last opened 2h ago" line in
their Share modal history. Closes the loop between "I sent it" and
"they read it" — a real anxiety-reducer for parents.

Design choices:
  * Bot user-agents are filtered BEFORE the write so a Slack /
    Discord / WhatsApp / Twitter / Facebook link-preview crawler
    doesn't inflate the count when the recipient first pastes the
    URL in a chat.
  * IPs are HASHED (sha256, no reversible mapping) before storage —
    we care about "how many opens", not "who the recipient is",
    and PHI-adjacent data (foundation statements) shouldn't hoard
    raw IPs.
  * Log writes are async and best-effort: a failure to log NEVER
    surfaces to the recipient (they get their statement anyway).
  * The sender-side read helper aggregates by `jti` in a single
    query so the History tab payload stays fast even at 100+ shares.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


_OPENS_COLL = "foundation_statement_preview_opens"

# Known link-preview / crawler user agents. Substring match — we
# intentionally keep this narrow so real recipient browsers (Chrome,
# Safari, Edge, Firefox on any OS) always count. Add entries as
# real-world traffic surfaces new bots.
_LINK_PREVIEW_BOT_PATTERNS = (
    "slackbot",           # Slack link unfurl
    "discordbot",         # Discord unfurl
    "whatsapp",           # WhatsApp / Meta preview
    "facebookexternalhit",
    "twitterbot",         # X / Twitter card
    "linkedinbot",
    "telegrambot",
    "skypeuripreview",
    "bot ",               # trailing space to avoid matching "robot" as noun
    "bot/",
    "crawler",
    "spider",
    "preview",
    "curl/",              # scripts, not human recipients
    "wget/",
    "httpie/",
    "python-requests",
    "go-http-client",
    "okhttp",
    "postman",
    "insomnia",
)


def is_link_preview_bot(user_agent: Optional[str]) -> bool:
    """Return True when the caller's UA looks like a link-preview
    crawler or automated script. Case-insensitive substring match."""
    if not user_agent:
        # A missing UA is suspicious enough on a public share
        # endpoint that we treat it as a bot. Real browsers always
        # send one.
        return True
    ua = user_agent.lower()
    return any(pat in ua for pat in _LINK_PREVIEW_BOT_PATTERNS)


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    """Return a short-hash of the client IP for de-duping opens
    within a session without storing the raw IP."""
    if not ip or not isinstance(ip, str):
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def client_ip_from_request(request) -> Optional[str]:
    """Extract the client IP behind the Emergent K8s ingress. Prefer
    the leftmost `X-Forwarded-For` hop (real client) over the
    request-socket IP (edge proxy)."""
    xff = request.headers.get("x-forwarded-for") or ""
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]
    if request.client and request.client.host:
        return request.client.host
    return None


async def record_preview_open(
    db: AsyncIOMotorDatabase,
    *,
    jti: Optional[str],
    doc_owner_user_id: Optional[str],
    user_agent: Optional[str],
    ip: Optional[str],
    referer: Optional[str] = None,
) -> bool:
    """Persist one open row. Silent no-op when the caller is a bot
    or when the token has no jti (legacy links). Returns True when
    a row was written."""
    if not jti or not doc_owner_user_id:
        return False
    if is_link_preview_bot(user_agent):
        return False
    try:
        await db[_OPENS_COLL].insert_one({
            "jti": jti,
            "doc_owner_user_id": doc_owner_user_id,
            "opened_at": datetime.now(timezone.utc),
            "ip_hash": _hash_ip(ip),
            "user_agent": (user_agent or "")[:240],
            "referer": (referer or "")[:240] or None,
        })
        return True
    except Exception:  # noqa: BLE001 — analytics MUST never break the recipient view
        return False


async def opens_by_jti(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    jtis: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Aggregate open counts + last-opened + unique-viewer count per
    jti, scoped to the caller (sender). Returns
    `{jti: {open_count, last_opened_at, unique_ip_count}}`.

    Uses a single `$group` pipeline so the History tab stays fast
    even when a heavy user has 25 share rows.
    """
    if not jtis:
        return {}
    pipeline = [
        {
            "$match": {
                "doc_owner_user_id": user_id,
                "jti": {"$in": jtis},
            },
        },
        {
            "$group": {
                "_id": "$jti",
                "open_count": {"$sum": 1},
                "last_opened_at": {"$max": "$opened_at"},
                "unique_ips": {"$addToSet": "$ip_hash"},
            },
        },
    ]
    out: Dict[str, Dict[str, Any]] = {}
    async for row in db[_OPENS_COLL].aggregate(pipeline):
        opened = row.get("last_opened_at")
        out[row["_id"]] = {
            "open_count": int(row.get("open_count") or 0),
            "last_opened_at": (
                opened.isoformat() if isinstance(opened, datetime) else None
            ),
            # Best-effort unique viewer count via hashed IP. Same
            # recipient re-opening on the same network only counts
            # once; a co-parent + mediator on different networks
            # count as two.
            "unique_ip_count": len([ip for ip in row.get("unique_ips") or [] if ip]),
        }
    return out
