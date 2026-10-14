"""Monday digest for professionals: counts only across active (non-archived) codes and cases. No names, no references.

Runs inside the daily 9am Central cron on Mondays. Once per ISO week; skipped when the counts haven't changed since the
last digest that was sent, when the professional switched it off, or when there's nothing to report.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import jwt
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import JWT_ALGO, JWT_SECRET, get_current_user, get_db
from court_checklist import REQUESTABLE, case_requested_keys, progress_rows
from models import UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/professional", tags=["professional-digest"])

UNSUB_KIND = "pro_digest_unsub"


def make_unsubscribe_token(user_id: str) -> str:
    return jwt.encode({"kind": UNSUB_KIND, "sub": user_id}, JWT_SECRET, algorithm=JWT_ALGO)


def read_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require": ["kind", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload["sub"] if payload.get("kind") == UNSUB_KIND else None


def _bucket(rows: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if rows is None:
        return "not_started"  # invited to a joint case but hasn't joined yet
    if not rows:
        return None
    if all(r["status"] == "done" for r in rows):
        return "finished"
    return "in_progress" if any(r["status"] != "todo" for r in rows) else "not_started"


async def digest_counts(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, int]:
    from court_codes_routes import linked_parents
    from joint_alignment_routes import _derived_status

    counts = {"finished": 0, "in_progress": 0, "not_started": 0}
    buckets: List[Optional[str]] = []
    async for d in db.portal_court_keys.find({"created_by": uid, "archived_at": None}, {"_id": 0, "case_id": 1, "requested": 1}):
        keys = [k for k in REQUESTABLE if k in (d.get("requested") or [])]
        buckets += [_bucket(p["assessments"]) for p in await linked_parents(db, d["case_id"], keys)]
    async for case in db.joint_alignment_cases.find({"professional_created_by": uid, "professional_archived_at": None}, {"_id": 0}):
        if _derived_status(case) in ("cancelled", "expired"):
            continue
        keys = case_requested_keys(case)
        for p in case.get("parents") or []:
            buckets.append(_bucket(await progress_rows(db, p["user_id"], keys) if p.get("user_id") else None))
    for b in buckets:
        if b:
            counts[b] += 1
    return counts


def _links(user_id: str) -> Dict[str, str]:
    app = (os.environ.get("PUBLIC_APP_URL") or "https://sacoparentsapp.online").rstrip("/")
    api = (os.environ.get("PUBLIC_BACKEND_URL") or app).rstrip("/")
    return {
        "cta": f"{app}/professional/joint-alignment/mine",
        "unsubscribe": f"{api}/api/professional/digest/unsubscribe?token={make_unsubscribe_token(user_id)}",
    }


async def send_professional_digests(db: AsyncIOMotorDatabase, *, now: Optional[datetime] = None) -> Dict[str, int]:
    from email_service import EmailNotConfigured, EmailSendError, send_professional_digest

    now = now or datetime.now(timezone.utc)
    year, wk, _ = now.isocalendar()
    week = f"{year}-W{wk:02d}"
    stats = {"sent": 0, "already_sent": 0, "skipped_off": 0, "skipped_empty": 0, "skipped_unchanged": 0, "skipped_no_email": 0, "failed": 0}
    pros = set(await db.portal_court_keys.distinct("created_by", {"archived_at": None, "created_by": {"$nin": [None, ""]}}))
    pros |= set(await db.joint_alignment_cases.distinct("professional_created_by",
                                                        {"professional_archived_at": None, "professional_created_by": {"$nin": [None, ""]}}))
    for uid in pros:
        if await db.professional_prefs.find_one({"user_id": uid, "digest_off": True}, {"_id": 1}):
            stats["skipped_off"] += 1
            continue
        if await db.professional_digest_sends.find_one({"user_id": uid, "week": week}, {"_id": 1}):
            stats["already_sent"] += 1
            continue
        counts = await digest_counts(db, uid)
        if not sum(counts.values()):
            stats["skipped_empty"] += 1
            continue
        last = await db.professional_digest_sends.find_one({"user_id": uid}, {"_id": 0, "counts": 1}, sort=[("sent_at", -1)])
        if last and last.get("counts") == counts:
            stats["skipped_unchanged"] += 1
            continue
        user = await db.users.find_one({"user_id": uid}, {"_id": 0, "email": 1, "name": 1, "email_bounced": 1, "email_complained": 1}) or {}
        if not user.get("email") or user.get("email_bounced") or user.get("email_complained"):
            stats["skipped_no_email"] += 1
            continue
        links = _links(uid)
        try:
            await asyncio.to_thread(send_professional_digest, to_email=user["email"], counts=counts, cta_url=links["cta"],
                                    unsubscribe_url=links["unsubscribe"], first_name=(user.get("name") or "").split(" ")[0] or None)
        except (EmailNotConfigured, EmailSendError) as exc:
            stats["failed"] += 1
            logger.warning("professional digest failed: %s", exc)
            continue
        await db.professional_digest_sends.insert_one({"user_id": uid, "week": week, "counts": counts, "sent_at": now.isoformat()})
        stats["sent"] += 1
    return stats


@router.get("/digest/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_digest(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> HTMLResponse:
    from self_assessment_routes import _UNSUB_PAGE

    uid = read_unsubscribe_token(token)
    if not uid:
        return HTMLResponse(_UNSUB_PAGE.format(title="Link not valid", body="This unsubscribe link isn't valid."), status_code=400)
    await db.professional_prefs.update_one({"user_id": uid}, {"$set": {"digest_off": True}}, upsert=True)
    return HTMLResponse(_UNSUB_PAGE.format(
        title="You're unsubscribed",
        body="You won't get the Monday case digest anymore. You can turn it back on from your Account page.",
    ))


class DigestPref(BaseModel):
    enabled: bool


@router.get("/digest")
async def get_digest_pref(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    from professional_nudges import _is_creator

    pref = await db.professional_prefs.find_one({"user_id": user.user_id}, {"_id": 0, "digest_off": 1}) or {}
    return {"eligible": await _is_creator(db, user.user_id), "enabled": not pref.get("digest_off")}


@router.put("/digest")
async def put_digest_pref(body: DigestPref, user: UserPublic = Depends(get_current_user),
                          db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    from professional_nudges import _is_creator

    await db.professional_prefs.update_one({"user_id": user.user_id}, {"$set": {"digest_off": not body.enabled}}, upsert=True)
    return {"eligible": await _is_creator(db, user.user_id), "enabled": body.enabled}
