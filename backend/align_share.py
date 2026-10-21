"""Communication Style answers for SACOparentsAlign (seen by assigned professionals and, when needed, SA CoParents administrators), sent only after the parent says yes.

No choice yet (skipped) or "no" -> the communication_readiness field is left out of the Align export entirely.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from case_safety import case_ids_for
from self_assessment_reminders import is_safety_flagged

log = logging.getLogger(__name__)
router = APIRouter(tags=["integrations"])
_COLL = "align_share_choices"
_PATH = "/integrations/align-share/communication-readiness"
NO_STORE = {"Cache-Control": "no-store"}
# Bump when the parent-facing sharing wording changes: an earlier "yes" is then asked again.
WORDING_VERSION = "2026-10-21"

# Same wording as frontend/src/pages/CommStyle.jsx.
QUESTIONS = [
    ("q1", "When my co-parent texts me about a conflict, my first instinct is to…", {
        "avoider": "Wait days to reply — or not reply.",
        "escalator": "Match the intensity and reply quickly.",
        "defensive": "Explain why they're wrong before anything else.",
        "over_explainer": "Write a long message covering every angle.",
        "passive": "Say 'fine' to keep the peace, even if it's not fine.",
        "balanced": "Pause, then reply briefly and factually.",
    }),
    ("q2", "When disagreements arise about our child, I most often…", {
        "avoider": "Disengage and hope it passes.",
        "escalator": "Make my point loudly so it lands.",
        "defensive": "Justify my parenting decisions.",
        "over_explainer": "Send articles, screenshots, and context.",
        "passive": "Agree even when I disagree.",
        "balanced": "Name the issue and propose options.",
    }),
    ("q3", "If I had to be honest, the pattern I'd most like to change is…", {
        "avoider": "Avoiding hard conversations.",
        "escalator": "Reacting before thinking.",
        "defensive": "Defending instead of listening.",
        "over_explainer": "Over-explaining instead of being clear.",
        "passive": "Going passive when I'm hurt.",
        "balanced": "I feel steady; I want to stay that way.",
    }),
]
SAMPLE_QUESTION = "A recent message I sent"
# Align keeps only these names. Closest match to q1, q2, q3 and the sample message, pending Align's confirmation.
CR_FIELDS = ("cr_conflict", "cr_child", "cr_direct", "cr_channel")
IMPORT_KEYS = ("cr_conflict", "cr_direct", "cr_channel", "cr_child", "completed_at")


class ShareBody(BaseModel):
    share: bool


class ShareStatus(BaseModel):
    choice: Optional[Literal["yes", "no"]] = None
    decided_at: Optional[str] = None
    reask: bool = False


async def _status(db, user_id: str) -> ShareStatus:
    doc = await db[_COLL].find_one({"user_id": user_id}, {"_id": 0}) or {}
    choice = doc.get("communication_readiness")
    if choice == "yes" and doc.get("wording_version") != WORDING_VERSION:
        return ShareStatus(reask=True)
    return ShareStatus(choice=choice, decided_at=doc.get("decided_at"))


def _reply(status: ShareStatus) -> JSONResponse:
    return JSONResponse(status.model_dump(), headers=NO_STORE)


@router.get(_PATH, response_model=ShareStatus)
async def get_share_choice(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    return _reply(await _status(db, current.user_id))


@router.put(_PATH, response_model=ShareStatus)
async def set_share_choice(body: ShareBody, background: BackgroundTasks,
                           current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    # Only parents linked to Align are asked (stale tabs included).
    if not await db.align_links.find_one({"user_id": current.user_id, "unlinked_at": None}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Link your account to SACOparentsAlign first.")
    await db[_COLL].update_one(
        {"user_id": current.user_id},
        {"$set": {"communication_readiness": "yes" if body.share else "no",
                  "wording_version": WORDING_VERSION,
                  "decided_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    if body.share:
        background.add_task(push_to_align, db, current.user_id)
    return _reply(await _status(db, current.user_id))


@router.delete(_PATH, response_model=ShareStatus)
async def clear_share_choice(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    """'Skip for now' on the ask-again prompt: back to not chosen, so nothing is shared."""
    await reset_share_choice(db, current.user_id)
    return _reply(await _status(db, current.user_id))


async def reset_share_choice(db, user_id: str) -> None:
    """Unlinking clears the choice, so linking again never silently restarts sharing."""
    await db[_COLL].delete_one({"user_id": user_id})


async def communication_readiness(db, user_id: str, prep: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The 4 Communication Style answers in plain words, or None unless the parent said yes and answered something."""
    if (await _status(db, user_id)).choice != "yes":
        return None
    cs = prep.get("comm_style") or {}
    picked = cs.get("answers") or {}
    answers = [{"question": text, "answer": options.get(picked.get(qid))} for qid, text, options in QUESTIONS]
    answers.append({"question": SAMPLE_QUESTION, "answer": (cs.get("free_text_sample") or "").strip() or None})
    if not any(a["answer"] for a in answers):
        return None
    saved_at = cs.get("saved_at")
    return {"answers": answers, "answered_at": saved_at,
            **{f: a["answer"] for f, a in zip(CR_FIELDS, answers)}, "completed_at": saved_at}


async def import_payload(db, user_id: str) -> Optional[Dict[str, Any]]:
    """What goes to Align's import address: the case code, email and Align's five fields. None = send nothing."""
    if not await db.align_links.find_one({"user_id": user_id, "unlinked_at": None}, {"_id": 1}):
        return None
    if await is_safety_flagged(db, user_id):
        return None
    prep = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0, "comm_style": 1}) or {}
    cr = await communication_readiness(db, user_id, prep)
    if not cr:
        return None
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1}) or {}
    ids = await case_ids_for(db, user_id)
    return {"case_id": ids[0] if ids else None, "email": user.get("email"), **{k: cr[k] for k in IMPORT_KEYS}}


async def push_to_align(db, user_id: str) -> None:
    """Off until ALIGN_IMPORT_URL and ALIGN_IMPORT_KEY are both set. Never logs answer content."""
    url, key = os.environ.get("ALIGN_IMPORT_URL"), os.environ.get("ALIGN_IMPORT_KEY")
    if not url or not key:
        return
    payload = await import_payload(db, user_id)
    if not payload:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload, headers={"X-Integration-Key": key})
        if r.status_code >= 300:
            log.warning("Align import answered %s", r.status_code)
    except httpx.HTTPError as e:
        log.warning("Align import failed: %s", type(e).__name__)
