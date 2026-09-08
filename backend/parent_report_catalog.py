"""Parent-facing report catalog.

Enumerates the SIGNED-IN PARENT'S completed reports across every
lane so the "Invite a Professional" wizard can present a
selectable list. Data-minimisation guardrail: this module returns
ONLY metadata (title, type, completion date, short blurb) — never
report body content. Report bodies are fetched lane-by-lane by the
sibling portal after the professional accepts an invite.

Report catalog entries carry:
  * report_id     — stable identifier, format `{lane}:{owner_ref}`
  * lane          — canonical taxonomy tag ("foundation", "coparenting",
                    "med-deep", "edu-deep", "psych-deep", "snc",
                    "safety", "communication-reflection")
  * title         — human-facing card title
  * blurb         — one-line description
  * completed_at  — ISO timestamp
  * version       — integer, defaults 1 (lanes without versioning
                    increment on regeneration)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


def _iso(v: Any) -> Optional[str]:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat()
    if isinstance(v, str):
        return v
    return None


def _foundation_completed(reflection: Optional[Dict[str, Any]]) -> bool:
    """A reflection counts as "complete" once at least one canonical
    prompt has non-empty content — matches the send-eligibility
    guardrail in foundation_statement_pdf."""
    if not reflection:
        return False
    for key in ("child_lens", "own_part", "best_outcome", "coparent_feedback"):
        v = reflection.get(key)
        if isinstance(v, str) and v.strip():
            return True
    return False


async def list_completed_reports(
    db: AsyncIOMotorDatabase, *, user_id: str,
) -> List[Dict[str, Any]]:
    """Return metadata for every completed report the caller owns.
    Never surfaces report body content."""
    out: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Foundation Statement — lives on prep_data.reflection.
    # ------------------------------------------------------------------
    prep = await db.prep_data.find_one(
        {"user_id": user_id}, {"_id": 0, "reflection": 1, "updated_at": 1},
    )
    if prep and _foundation_completed(prep.get("reflection")):
        out.append({
            "report_id": f"foundation:{user_id}",
            "lane": "foundation",
            "title": "Foundation Statement",
            "blurb": (
                "Four-prompt reflection I wrote for my mediator or "
                "attorney to read before our first session."
            ),
            "completed_at": _iso(prep.get("updated_at")),
            "version": 1,
        })

    # ------------------------------------------------------------------
    # Co-Parenting Assessment Report — cp_reports collection.
    # ------------------------------------------------------------------
    cp_report = await db.cp_reports.find_one(
        {"user_id": user_id},
        {"_id": 1, "generated_at": 1, "updated_at": 1, "version": 1},
    )
    if cp_report:
        out.append({
            "report_id": f"coparenting:{cp_report['_id']}",
            "lane": "coparenting",
            "title": "Co-Parenting Assessment Report",
            "blurb": (
                "My private co-parenting reflection — priorities, "
                "areas I want to work on, and how I want us to "
                "communicate."
            ),
            "completed_at": _iso(
                cp_report.get("generated_at") or cp_report.get("updated_at"),
            ),
            "version": int(cp_report.get("version") or 1),
        })

    # ------------------------------------------------------------------
    # Deep-Dive reports — three lanes, same shape.
    # ------------------------------------------------------------------
    for coll, lane, title, blurb in (
        (
            "med_deep_reports", "med-deep", "Medical Needs Report",
            "Deep-dive on my child's medical picture — appointments, "
            "medications, care coordination.",
        ),
        (
            "edu_deep_reports", "edu-deep", "Educational Needs Report",
            "Deep-dive on my child's education — supports, IEP/504, "
            "school communication.",
        ),
        (
            "psych_deep_reports", "psych-deep", "Psychological Needs Report",
            "Deep-dive on my child's emotional and psychological "
            "supports — providers, coping tools, patterns.",
        ),
    ):
        dd = await db[coll].find_one(
            {"user_id": user_id},
            {"_id": 1, "generated_at": 1, "updated_at": 1, "version": 1},
            sort=[("generated_at", -1)],
        )
        if dd:
            out.append({
                "report_id": f"{lane}:{dd['_id']}",
                "lane": lane,
                "title": title,
                "blurb": blurb,
                "completed_at": _iso(
                    dd.get("generated_at") or dd.get("updated_at"),
                ),
                "version": int(dd.get("version") or 1),
            })

    # ------------------------------------------------------------------
    # Special Needs Report (SNC v2) — snc2_reports collection.
    # ------------------------------------------------------------------
    snc = await db.snc2_reports.find_one(
        {"user_id": user_id},
        {"_id": 1, "generated_at": 1, "updated_at": 1, "version": 1},
        sort=[("generated_at", -1)],
    )
    if snc:
        out.append({
            "report_id": f"snc:{snc['_id']}",
            "lane": "snc",
            "title": "Special Needs Report",
            "blurb": (
                "Broad-scope special-needs summary spanning medical, "
                "educational, and psychological considerations."
            ),
            "completed_at": _iso(
                snc.get("generated_at") or snc.get("updated_at"),
            ),
            "version": int(snc.get("version") or 1),
        })

    # Sort newest-first so the parent sees their most-recent work
    # at the top of the picker.
    out.sort(key=lambda r: r.get("completed_at") or "", reverse=True)
    return out
