"""Right-away email to the professional when a parent finishes everything that professional asked for.

Names only the case reference and the professional's own private label: never the parent, an assessment or answers.
In-app court codes and joint cases only (Align-made codes have no professional email here). Once per parent per case.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from motor.motor_asyncio import AsyncIOMotorDatabase

from court_checklist import REQUESTABLE, assessment_statuses, case_requested_keys

logger = logging.getLogger(__name__)

_TASKS: Set[asyncio.Task] = set()


async def _sources(db: AsyncIOMotorDatabase, uid: str) -> List[Dict[str, Any]]:
    out = []
    ps = await db.portal_state.find_one({"user_id": uid}, {"_id": 0, "court_key": 1}) or {}
    ck = (ps.get("court_key") or "").strip()
    if ck:
        kd = await db.portal_court_keys.find_one({"case_id": ck, "created_by": {"$nin": [None, ""]}},
                                                 {"_id": 0, "requested": 1, "label": 1, "created_by": 1})
        if kd:
            out.append({"ref": ck, "label": kd.get("label") or "", "pro": kd["created_by"],
                        "keys": [k for k in REQUESTABLE if k in (kd.get("requested") or [])]})
    async for case in db.joint_alignment_cases.find(
        {"parents.user_id": uid, "status": {"$ne": "cancelled"}, "professional_created_by": {"$nin": [None, ""]}},
        {"_id": 0, "case_id": 1, "assigned_steps": 1, "assessment_type": 1, "align_case_reference": 1, "professional_created_by": 1},
    ):
        out.append({"ref": case["case_id"], "label": case.get("align_case_reference") or "",
                    "pro": case["professional_created_by"], "keys": case_requested_keys(case)})
    return out


async def check_and_alert(db: AsyncIOMotorDatabase, uid: str) -> int:
    """Send any due alerts for this parent. Returns how many were sent."""
    from email_service import EmailNotConfigured, EmailSendError, send_completion_alert

    sources = [s for s in await _sources(db, uid) if s["keys"]]
    if not sources:
        return 0
    st = await assessment_statuses(db, uid)
    app = (os.environ.get("PUBLIC_APP_URL") or "https://sacoparentsapp.online").rstrip("/")
    sent = 0
    for s in sources:
        if any(st[k]["status"] != "done" for k in s["keys"]):
            continue
        now = datetime.now(timezone.utc).isoformat()
        claim = await db.completion_alerts.update_one(
            {"user_id": uid, "ref": s["ref"]},
            {"$setOnInsert": {"user_id": uid, "ref": s["ref"], "pro_user_id": s["pro"], "status": "pending", "created_at": now}},
            upsert=True,
        )
        if not claim.upserted_id:
            continue  # already alerted for this parent + case
        pro = await db.users.find_one({"user_id": s["pro"]}, {"_id": 0, "email": 1, "email_bounced": 1, "email_complained": 1}) or {}
        status = "skipped_no_email"
        if pro.get("email") and not pro.get("email_bounced") and not pro.get("email_complained"):
            try:
                await asyncio.to_thread(send_completion_alert, to_email=pro["email"], case_ref=s["ref"], label=s["label"],
                                        cta_url=f"{app}/professional/joint-alignment/mine")
                status, sent = "sent", sent + 1
            except (EmailNotConfigured, EmailSendError) as exc:
                logger.warning("completion alert failed for %s: %s", s["ref"], exc)
                await db.completion_alerts.delete_one({"user_id": uid, "ref": s["ref"]})  # retry on the next save
                continue
        await db.completion_alerts.update_one({"user_id": uid, "ref": s["ref"]}, {"$set": {"status": status, "sent_at": now}})
    return sent


async def _run(db: AsyncIOMotorDatabase, uid: str) -> None:
    try:
        await check_and_alert(db, uid)
    except Exception:  # noqa: BLE001 — never break the parent's save
        logger.exception("completion alert check failed")


def schedule_completion_check(db: AsyncIOMotorDatabase, uid: str) -> None:
    """Fire-and-forget after a parent finishes an assessment."""
    task = asyncio.create_task(_run(db, uid))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
