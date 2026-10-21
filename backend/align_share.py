"""Communication Style answers for the parent's assigned professional on Align, sent only after the parent says yes.

No choice yet (skipped) or "no" -> the communication_readiness field is left out of the Align export entirely.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db

router = APIRouter(tags=["integrations"])
_COLL = "align_share_choices"
_PATH = "/integrations/align-share/communication-readiness"
NO_STORE = {"Cache-Control": "no-store"}

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


class ShareBody(BaseModel):
    share: bool


class ShareStatus(BaseModel):
    choice: Optional[Literal["yes", "no"]] = None
    decided_at: Optional[str] = None


async def _status(db, user_id: str) -> ShareStatus:
    doc = await db[_COLL].find_one({"user_id": user_id}, {"_id": 0}) or {}
    return ShareStatus(choice=doc.get("communication_readiness"), decided_at=doc.get("decided_at"))


@router.get(_PATH, response_model=ShareStatus)
async def get_share_choice(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    return JSONResponse((await _status(db, current.user_id)).model_dump(), headers=NO_STORE)


@router.put(_PATH, response_model=ShareStatus)
async def set_share_choice(body: ShareBody, current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    # Only parents linked to Align are asked (stale tabs included).
    if not await db.align_links.find_one({"user_id": current.user_id, "unlinked_at": None}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Link your account to SACOparentsAlign first.")
    await db[_COLL].update_one(
        {"user_id": current.user_id},
        {"$set": {"communication_readiness": "yes" if body.share else "no",
                  "decided_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return JSONResponse((await _status(db, current.user_id)).model_dump(), headers=NO_STORE)


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
    return {"answers": answers, "answered_at": cs.get("saved_at")}
