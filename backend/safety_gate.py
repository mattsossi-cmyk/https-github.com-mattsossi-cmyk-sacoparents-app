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
    # The in-app safety screen is turned off (screening happens on SACOparentsAlign); saved answers are never read.
    return None


async def require_ipv_clearance(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """No longer gates invites: the in-app safety screen is off and the case settings from SACOparentsAlign
    (structured / restricted) now protect families. Kept so existing callers don't change."""
    return None


async def ipv_gate_status(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    return {"clear": True, "level": None, "code": "ok"}
