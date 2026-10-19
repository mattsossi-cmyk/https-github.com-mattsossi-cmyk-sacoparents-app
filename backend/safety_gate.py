"""safety_gate.py — IPV / family-violence guardrail for parent-to-co-parent invitations.

Rule (founder directive, 2026-03-04):
    A parent may only send an invitation to their co-parent AFTER completing
    the family-violence / IPV safety screen AND scoring at Level 3 or 4.
    Level 1 (highest concern) and Level 2 (coercive-control indicators) MUST NOT
    be able to send a co-parent invitation from within the app.

This module is intentionally tiny and single-purpose so any parent-to-coparent
invitation route can import `require_ipv_clearance(...)` and get the same
gate + the same 403 payload shape.

Invitations to *professionals* are NOT gated by this module — a professional
is not the safety concern; blocking those would harm the parent's ability to
seek help.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


# Any level ≤ this is BLOCKED. Level 1 = highest concern, Level 2 = coercive
# control. Level 3 = manageable with structure. Level 4 = generally safe.
BLOCKED_LEVEL_CEILING = 2

DV_HOTLINE = "1-800-799-7233"


class IPVGateError(HTTPException):
    """403 raised when the calling parent has not cleared the IPV gate.

    `code` gives the frontend a stable string it can key UX off of, and the
    `detail` is a compassionate one-liner the parent can read directly.
    """

    def __init__(self, code: str, message: str, *, level: Optional[int] = None):
        super().__init__(status_code=403, detail={
            "code": code,
            "message": message,
            "level": level,
            "hotline": DV_HOTLINE,
            "safety_screen_url": "/safety",
        })
        self.gate_code = code


async def _latest_safety_level(db: AsyncIOMotorDatabase, user_id: str) -> Optional[int]:
    """Return the numeric `level` from this parent's most recent safety
    assessment (1..4), or None if they have not completed one."""
    doc = await db.safety_assessments.find_one(
        {"user_id": user_id},
        {"_id": 0, "result.level": 1},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    result = doc.get("result") or {}
    level = result.get("level")
    return int(level) if isinstance(level, (int, float)) else None


async def require_ipv_clearance(
    db: AsyncIOMotorDatabase,
    user_id: str,
) -> int:
    """Raise `IPVGateError` when the parent should NOT be able to invite
    the co-parent. Returns the passing level (3 or 4) otherwise.

    - No safety screen on file    → 403 `safety_screen_required`
    - Latest screen level ≤ 2     → 403 `safety_screen_blocked`
    - Latest screen level ≥ 3     → returns the level
    """
    level = await _latest_safety_level(db, user_id)
    if level is None:
        raise IPVGateError(
            "safety_screen_required",
            (
                "Please complete the family-violence safety screen before sending "
                "a co-parent invitation. It takes about 5 minutes and stays private."
            ),
        )
    if level <= BLOCKED_LEVEL_CEILING:
        raise IPVGateError(
            "safety_screen_blocked",
            (
                "Based on your safety screen, direct outreach to your co-parent "
                f"through this app isn't recommended. If you're in danger, call {DV_HOTLINE}. "
                "A mediator or attorney can safely handle communication on your behalf."
            ),
            level=level,
        )
    return level


async def ipv_gate_status(
    db: AsyncIOMotorDatabase,
    user_id: str,
) -> dict:
    """Non-raising variant used by GET endpoints so the frontend can decide
    whether to render the "Invite co-parent" surface at all.

    Returns:
      { "clear": bool, "level": int|None, "code": "ok"|"safety_screen_required"|"safety_screen_blocked" }
    """
    level = await _latest_safety_level(db, user_id)
    if level is None:
        return {"clear": False, "level": None, "code": "safety_screen_required"}
    if level <= BLOCKED_LEVEL_CEILING:
        return {"clear": False, "level": level, "code": "safety_screen_blocked"}
    return {"clear": True, "level": level, "code": "ok"}
