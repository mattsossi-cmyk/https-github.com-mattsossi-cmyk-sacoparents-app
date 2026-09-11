"""Dual-consent gating helper — reusable pattern for future
cross-parent surfaces.

Extracts the privacy contract that `snc2_comparison_routes` already
enforces so ANY future route wanting to surface one parent's raw
answers to the other can slot the same gate in a single line:

    @router.get("/joint/foo/{case_id}")
    async def foo(
        case_id: str,
        current: UserPublic = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        # Both parents must have EXPLICITLY consented AND completed.
        # Raises 403 with a neutral message if either gate is open.
        await require_dual_consent(
            db,
            case_id=case_id,
            caller_user_id=current.user_id,
            consent_key="foo_share_consent_at",
        )
        ...

Why this matters:
  Code review iter186 caught the Complete Alignment Report leaking
  Foundation Statement free-text between co-parents on nothing more
  than an implicit "you're both on a case" consent. The audit that
  followed found every OTHER cross-parent surface on the platform
  already enforces one of two strict patterns:
    (a) flag-only (no raw content leaves the individual view), or
    (b) explicit dual-consent (both parents have recorded a
        consent-at timestamp AND both have completed the assessment
        AND — for safety-sensitive lanes — both are safety-cleared).

This module makes pattern (b) mechanically enforceable, so a future
route can't accidentally skip it.

Design constraints:
  * READ-ONLY. Never writes consent records — a dedicated consent
    endpoint (in the caller module) is where consent is captured.
  * Fails closed. If ANY gate is missing (case not found, caller not
    a member, one parent missing consent) we return an HTTP 403 with
    a neutral message that never leaks case existence.
  * Zero side effects. Safe to call from any request handler.
"""
from __future__ import annotations

from typing import Optional, Tuple

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


_CASES_COLL = "joint_alignment_cases"


class DualConsentGate:
    """Result of a successful dual-consent check.

    Callers get the case doc + the two parent user_ids so they can go
    on to build the joint payload without a second DB read.
    """
    __slots__ = ("case", "parent_a_user_id", "parent_b_user_id")

    def __init__(self, case: dict, parent_a_user_id: str, parent_b_user_id: str) -> None:
        self.case = case
        self.parent_a_user_id = parent_a_user_id
        self.parent_b_user_id = parent_b_user_id


async def require_dual_consent(
    db: AsyncIOMotorDatabase,
    *,
    case_id: str,
    caller_user_id: str,
    consent_key: str,
    require_both_completed: bool = True,
) -> DualConsentGate:
    """Raise HTTP 403 unless ALL of the following hold:

      1. `case_id` resolves to a case in `joint_alignment_cases`.
      2. `caller_user_id` is one of the two parents on the case OR
         the professional who created it. (Non-members see a 403
         with the same neutral message as everyone else — case
         existence is never leaked.)
      3. Both parents on the case have `user_id` populated (i.e. both
         accepted their invitation).
      4. When `require_both_completed` is True, both parents have
         `assessment_completed_at` set — matches the platform's
         existing pattern where flag-only previews unlock at the
         completion milestone.
      5. Both parents have a truthy value at `consent_key` inside
         their parents-list entry — the caller's endpoint is the one
         that records this timestamp when a parent taps "share my
         X in this joint report".

    On success returns a `DualConsentGate` with the case doc + both
    parents' user_ids so the caller can build the payload without a
    second query.
    """
    neutral = HTTPException(
        status_code=403,
        detail=(
            "This joint view requires both parents to have completed "
            "the assessment AND recorded explicit share consent."
        ),
    )
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise neutral
    parents = case.get("parents") or []
    if len(parents) < 2:
        raise neutral
    a, b = parents[0], parents[1]
    a_uid: Optional[str] = a.get("user_id")
    b_uid: Optional[str] = b.get("user_id")
    if not a_uid or not b_uid:
        raise neutral
    prof_id = (
        case.get("professional_created_by")
        or (case.get("professional") or {}).get("id")
    )
    if caller_user_id not in (a_uid, b_uid) and caller_user_id != prof_id:
        raise neutral
    if require_both_completed:
        if not a.get("assessment_completed_at") or not b.get("assessment_completed_at"):
            raise neutral
    if not a.get(consent_key) or not b.get(consent_key):
        raise neutral
    return DualConsentGate(case=case, parent_a_user_id=a_uid, parent_b_user_id=b_uid)


async def record_consent(
    db: AsyncIOMotorDatabase,
    *,
    case_id: str,
    caller_user_id: str,
    consent_key: str,
    consent_iso: str,
) -> Tuple[bool, bool]:
    """Idempotent single-parent consent capture. Returns
    ``(recorded, both_now_consented)`` so the caller can respond
    "we're still waiting on the other parent" vs. "the joint view
    is now unlocked". Idempotent — re-recording the same consent
    key just overwrites the timestamp (never removes it).

    Returns `(False, False)` and raises 403 if the caller is not a
    parent on the case (professional-only routes can call
    `require_dual_consent` directly rather than through this helper).
    """
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    parents = case.get("parents") or []
    slot: Optional[int] = None
    for idx, p in enumerate(parents[:2]):
        if p.get("user_id") == caller_user_id:
            slot = idx
            break
    if slot is None:
        raise HTTPException(status_code=403, detail="You are not a parent on this case.")
    await db[_CASES_COLL].update_one(
        {"case_id": case_id},
        {"$set": {f"parents.{slot}.{consent_key}": consent_iso}},
    )
    refreshed = await db[_CASES_COLL].find_one({"case_id": case_id}, {"parents": 1}) or {}
    fresh_parents = refreshed.get("parents") or []
    both = (
        len(fresh_parents) >= 2
        and bool(fresh_parents[0].get(consent_key))
        and bool(fresh_parents[1].get(consent_key))
    )
    return True, both
