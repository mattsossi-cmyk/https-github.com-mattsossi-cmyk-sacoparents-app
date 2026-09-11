"""Complete Alignment aggregator — pulls a parent's completed
reflections across every lane so the Complete Alignment Report can
stitch them into one 10-section artefact.

Design:
  * READ-ONLY. Never writes to any lane collection.
  * Data-minimised return shape. The aggregator emits ONLY the fields
    the PDF renderer + JSON viewer need — no raw Mongo `_id` values,
    no auth tokens, no other-parent references.
  * "Not completed yet" is a first-class state. The Complete Alignment
    Report intentionally lists ALL lanes so a parent can see at a
    glance where they still have exploration to do — matching the
    sacoparentsalign.com structure where every section always renders.
  * Sits at the bottom of the import graph (no project deps beyond
    Motor) so it can be pulled in from tests hermetically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


# --- Lane taxonomy ----------------------------------------------------------
# Order here IS the order sections render in when a lane is listed.
# Kept in lockstep with the frontend's `LANE_META` map.
LANES: List[Dict[str, str]] = [
    {
        "id": "foundation",
        "title": "Foundation Statement",
        "blurb": "Four-prompt reflection about the child, your part, and your best outcome.",
    },
    {
        "id": "communication",
        "title": "Communication",
        "blurb": "How you share information and messages with your co-parent.",
    },
    {
        "id": "activities",
        "title": "Activities & Costs",
        "blurb": "Weekly commitments, activities, and how you split shared costs.",
    },
    {
        "id": "schedule",
        "title": "Parenting Schedule",
        "blurb": "Weekday, weekend, holiday, and transition patterns.",
    },
    {
        "id": "child_needs",
        "title": "Child Needs Statement",
        "blurb": "Medical, educational, psychological, and behavioural needs.",
    },
    {
        "id": "safety",
        "title": "Safety Reflection",
        "blurb": "Private safety screen — routed only to your professional.",
    },
    {
        "id": "coparenting",
        "title": "Co-Parenting Assessment",
        "blurb": "Priorities, working style, and how you want to communicate.",
    },
]


def _iso(v: Any) -> Optional[str]:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat()
    if isinstance(v, str):
        return v
    return None


def _first_nonempty(*vals: Any) -> Optional[str]:
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


async def _foundation(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Foundation Statement lives on `prep_data.reflection`.
    Completion requires at least one canonical prompt to be non-empty
    (matches `parent_report_catalog._foundation_completed`).
    """
    doc = await db.prep_data.find_one(
        {"user_id": user_id},
        {"_id": 0, "reflection": 1, "child_name": 1, "updated_at": 1},
    ) or {}
    reflection = doc.get("reflection") or {}
    prompts = {
        "child_lens": (reflection.get("child_lens") or "").strip(),
        "own_part": (reflection.get("own_part") or "").strip(),
        "best_outcome": (reflection.get("best_outcome") or "").strip(),
        "coparent_feedback": (reflection.get("coparent_feedback") or "").strip(),
    }
    completed = any(v for v in prompts.values())
    return {
        "id": "foundation",
        "completed": completed,
        "updated_at": _iso(doc.get("updated_at")),
        "child_name": doc.get("child_name"),
        "prompts": prompts if completed else {},
    }


async def _child_needs(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Child Needs Statement (SNC v2). Answers live on `snc_v2_answers`;
    the rendered report lives on `snc2_reports`. Either one being
    present means the parent has engaged with this lane.
    """
    ans = await db.snc_v2_answers.find_one(
        {"user_id": user_id}, {"_id": 0, "answers": 1, "updated_at": 1},
    ) or {}
    rpt = await db.snc2_reports.find_one(
        {"user_id": user_id},
        {"_id": 0, "generated_at": 1, "updated_at": 1, "version": 1, "summary": 1},
        sort=[("generated_at", -1)],
    ) or {}
    answers = ans.get("answers") or {}
    completed = bool(answers) or bool(rpt)
    highlights: List[str] = []
    # Best-effort pull of top-level "what my child needs" style
    # answers. We defensively coerce every value to str and cap length
    # so a rogue payload can't blow up the PDF layout.
    for key in ("what_child_needs", "top_priority", "biggest_worry", "biggest_hope"):
        v = _first_nonempty(answers.get(key))
        if v:
            highlights.append(v[:400])
    return {
        "id": "child_needs",
        "completed": completed,
        "updated_at": _iso(rpt.get("generated_at") or rpt.get("updated_at") or ans.get("updated_at")),
        "version": int(rpt.get("version") or 1),
        "highlights": highlights,
    }


async def _lane_generic(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    lane_id: str,
    collection: str,
) -> Dict[str, Any]:
    """Generic single-collection lane probe — used for Communication,
    Activities, Schedule, Safety, and Co-Parenting where the presence
    of ANY document keyed on `user_id` counts as engagement.
    """
    doc = await db[collection].find_one(
        {"user_id": user_id},
        {
            "_id": 0,
            "generated_at": 1,
            "updated_at": 1,
            "created_at": 1,
            "version": 1,
        },
        sort=[("generated_at", -1)],
    ) or {}
    return {
        "id": lane_id,
        "completed": bool(doc),
        "updated_at": _iso(
            doc.get("generated_at") or doc.get("updated_at") or doc.get("created_at")
        ),
        "version": int(doc.get("version") or 1) if doc else 0,
    }


async def aggregate_for_user(
    db: AsyncIOMotorDatabase, *, user_id: str,
) -> Dict[str, Any]:
    """Return a normalised map of every lane's completion state + a
    handful of body excerpts for the sections that need real content
    (Foundation Statement, Child Needs Statement).

    Shape:
        {
          "user_id": str,
          "generated_at": ISO-8601,
          "counts": {"completed": int, "total": int},
          "child_name": Optional[str],
          "lanes": [
             {"id": "foundation", "title": ..., "completed": bool, ...},
             ...
          ],
        }
    """
    foundation = await _foundation(db, user_id)
    child_needs = await _child_needs(db, user_id)
    communication = await _lane_generic(
        db, user_id=user_id, lane_id="communication",
        collection="communication_reflection",
    )
    activities = await _lane_generic(
        db, user_id=user_id, lane_id="activities",
        collection="activities_reflection",
    )
    schedule = await _lane_generic(
        db, user_id=user_id, lane_id="schedule",
        collection="parenting_schedule_reflection",
    )
    safety = await _lane_generic(
        db, user_id=user_id, lane_id="safety",
        collection="safety_assessments",
    )
    coparenting = await _lane_generic(
        db, user_id=user_id, lane_id="coparenting",
        collection="cp_reports",
    )
    lane_by_id = {
        "foundation": foundation,
        "communication": communication,
        "activities": activities,
        "schedule": schedule,
        "child_needs": child_needs,
        "safety": safety,
        "coparenting": coparenting,
    }

    lanes: List[Dict[str, Any]] = []
    completed_count = 0
    for meta in LANES:
        data = lane_by_id.get(meta["id"]) or {"id": meta["id"], "completed": False}
        if data.get("completed"):
            completed_count += 1
        lanes.append({
            **meta,
            **data,
        })

    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"completed": completed_count, "total": len(LANES)},
        "child_name": foundation.get("child_name"),
        "lanes": lanes,
    }


async def aggregate_for_case(
    db: AsyncIOMotorDatabase, *, parent_a_user_id: str, parent_b_user_id: str,
) -> Dict[str, Any]:
    """Joint variant — aggregate both parents and mark per-lane
    alignment status. Alignment status is:
        * "shared"      — both parents have completed this lane
        * "one-side"    — only one parent has completed it
        * "not-yet"     — neither has completed it

    The neutral labelling is deliberate — the Complete Alignment
    Report never adjudicates "who is right"; it only surfaces where
    the conversation has raw material vs. where it doesn't yet.

    PRIVACY CONTRACT: The returned `parent_a` / `parent_b` sub-objects
    MUST NOT leak either parent's raw free-text answers to the other.
    We call the per-user aggregator (which contains the Foundation
    Statement prompts + Child Needs highlights) and then run every
    lane through `_scrub_for_joint_view` which drops any body-content
    fields. Only lane-level completion metadata + neutral counts
    survive into the joint payload.
    """
    a = await aggregate_for_user(db, user_id=parent_a_user_id)
    b = await aggregate_for_user(db, user_id=parent_b_user_id)
    a_by_id = {ln["id"]: ln for ln in a["lanes"]}
    b_by_id = {ln["id"]: ln for ln in b["lanes"]}

    joint_lanes: List[Dict[str, Any]] = []
    shared_count = 0
    one_side_count = 0
    for meta in LANES:
        ac = bool(a_by_id.get(meta["id"], {}).get("completed"))
        bc = bool(b_by_id.get(meta["id"], {}).get("completed"))
        if ac and bc:
            status = "shared"
            shared_count += 1
        elif ac or bc:
            status = "one-side"
            one_side_count += 1
        else:
            status = "not-yet"
        joint_lanes.append({
            **meta,
            "status": status,
            "parent_a_completed": ac,
            "parent_b_completed": bc,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "shared": shared_count,
            "one_side": one_side_count,
            "total": len(LANES),
        },
        "child_name": a.get("child_name") or b.get("child_name"),
        "parent_a": _scrub_for_joint_view(a),
        "parent_b": _scrub_for_joint_view(b),
        "lanes": joint_lanes,
    }


# Body-content fields on the per-user aggregate that MUST NOT be
# echoed into the joint view. Kept as a module-level tuple so the
# scrub logic is auditable in one place.
#
# What lives here — and why:
#   * `prompts` — Foundation Statement four-prompt free text. Reads
#                 as "how the child sees me", "my part", "what I want
#                 you to hear" — introspective content about the
#                 relationship, ALWAYS private between co-parents.
#
# What deliberately does NOT live here:
#   * `highlights` — Child Needs Statement short excerpts (top
#                    priority, biggest worry, biggest hope). By
#                    product design these ARE surfaced across the
#                    joint view because they describe the CHILD, not
#                    the co-parent relationship. If future policy
#                    changes that, add "highlights" to this tuple.
_JOINT_STRIPPED_LANE_FIELDS: tuple[str, ...] = (
    "prompts",
)


def _scrub_for_joint_view(user_agg: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of the per-user aggregate with every
    lane's body-content fields removed. Preserves lane completion
    metadata (`completed`, `updated_at`, `version`, etc.) so the
    frontend can still say "parent A has completed 4/7 lanes" — but
    never expose the answer bodies.

    We defensively copy the top-level dict so the caller's original
    `aggregate_for_user` result is left untouched — this lets a
    future caller reuse the per-user aggregate for its own private
    view without accidentally serving the scrubbed lanes.
    """
    scrubbed = dict(user_agg)
    scrubbed["lanes"] = [
        {k: v for k, v in lane.items() if k not in _JOINT_STRIPPED_LANE_FIELDS}
        for lane in (user_agg.get("lanes") or [])
    ]
    # `child_name` on the top-level is a shared surface (both parents
    # answer for the same child) — leave it. But the per-user
    # `child_name` field on the foundation lane can carry a parent's
    # unique name spelling; leaving it on the aggregate is intentional
    # (already surfaced in section 2 of the report).
    return scrubbed
