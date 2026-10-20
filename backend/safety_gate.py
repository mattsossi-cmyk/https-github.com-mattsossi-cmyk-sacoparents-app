"""safety_gate.py: keeps co-parent invitations off for a parent with an older saved concerning safety result.

The in-app safety screen is off (the safety step is the Family check-in on SACOparentsAlign). A parent with
no saved result is never blocked. A parent whose latest saved result is level 1 or 2 still can't invite or
nudge the co-parent; they see only the neutral NOT_AVAILABLE note, never a level or a safety reason.
A named professional's case settings sent from SACOparentsAlign lift the hold.
Invitations to professionals are never gated here.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

BLOCKED_LEVEL_CEILING = 2

NOT_AVAILABLE_CODE = "not_available"
NOT_AVAILABLE = "This isn't available right now. Your Family check-in on SACOparentsAlign is the next step."


class IPVGateError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=403, detail={"code": NOT_AVAILABLE_CODE, "message": NOT_AVAILABLE})
        self.gate_code = NOT_AVAILABLE_CODE


async def _latest_safety_level(db: AsyncIOMotorDatabase, user_id: str) -> Optional[int]:
    """Level (1..4) of this parent's most recent saved assessment, or None. Internal enforcement only."""
    doc = await db.safety_assessments.find_one(
        {"user_id": user_id},
        {"_id": 0, "result.level": 1},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    level = (doc.get("result") or {}).get("level")
    return int(level) if isinstance(level, (int, float)) else None


async def lifted_by_professional(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """A named professional's case settings (signed, from SACOparentsAlign) replace the old-result hold."""
    import case_safety
    for case_id in await case_safety.case_ids_for(db, user_id):
        rec = await case_safety.read_record(db, case_id, "system", "old_result_hold")
        if rec and rec.get("set_by") == "professional":
            return True
    return False


async def is_blocked(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    level = await _latest_safety_level(db, user_id)
    if level is None or level > BLOCKED_LEVEL_CEILING:
        return False
    return not await lifted_by_professional(db, user_id)


async def require_ipv_clearance(db: AsyncIOMotorDatabase, user_id: str) -> None:
    if await is_blocked(db, user_id):
        raise IPVGateError()


async def ipv_gate_status(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    if await is_blocked(db, user_id):
        return {"clear": False, "code": NOT_AVAILABLE_CODE, "message": NOT_AVAILABLE}
    return {"clear": True, "code": "ok"}
