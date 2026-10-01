"""Iter234 · Co-Parenting Assessment history + progress analytics.

The main `/report/generate` endpoint upserts one report per user in
`cp_reports`. That gives the parent "the latest" but no sense of
trajectory. This module keeps an append-only history collection so
we can:

  * Draw a sparkline of overall numeric rating over time.
  * Diff the most-recent run against a run from ~60 days ago to
    surface per-section movers (↑ this section improved, ↓ this
    one slipped).
  * Drive the 60-day retake nudge banner.

No PII beyond the user_id that's already stored elsewhere. Each
history row is a lightweight snapshot — just the overall rating,
per-section averages, and the submitted_at ISO timestamp — so even
after a hundred retakes a user's history document is a few KB.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


HISTORY_COLLECTION = "cp_report_history"

# Days between retakes we encourage. Anything over this triggers
# the "see how you've changed" banner on Alignment & Tools.
RETAKE_INTERVAL_DAYS = 60

# Numeric values we assign to each overall-rating band so the
# sparkline can render as a line chart. These are only used for
# visual trending — the rating text itself is still the source of
# truth for anything a parent sees worded.
_RATING_VALUES: Dict[str, float] = {
    "Needs Improvement": 1.0,
    "Fair": 2.0,
    "Good": 3.0,
    "Excellent": 4.0,
    "Building Progress": 2.0,   # alias emitted by the scoring engine
    "Not enough data": 0.0,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rating_value(rating: Optional[str]) -> float:
    return _RATING_VALUES.get((rating or "").strip(), 0.0)


def _section_avgs_from_scores(scores: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull a compact per-section snapshot out of the scoring dict.

    Each row: {id, number, name, rating, avg}. Keeps field names
    identical to what the live report emits so the frontend's
    section-name rendering doesn't need a parallel code path."""
    out: List[Dict[str, Any]] = []
    for sec in (scores.get("sections") or []):
        out.append({
            "id":     sec.get("id"),
            "number": sec.get("number"),
            "name":   sec.get("name"),
            "rating": sec.get("rating"),
            "avg":    sec.get("avg"),
        })
    return out


async def append_history(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    scores: Dict[str, Any],
    answered: int,
    total: int,
) -> Dict[str, Any]:
    """Append one snapshot to the user's history document.

    Called from inside `/report/generate` after the upsert — a single
    atomic $push on an {_id: user_id} doc.
    """
    snapshot = {
        "submitted_at":    _now_iso(),
        "overall_rating":  scores.get("overall_rating") or "Not enough data",
        "overall_value":   _rating_value(scores.get("overall_rating")),
        "section_avgs":    _section_avgs_from_scores(scores),
        "answered":        int(answered),
        "total":           int(total),
    }
    await db[HISTORY_COLLECTION].update_one(
        {"_id": user_id},
        {"$push": {"snapshots": snapshot}, "$setOnInsert": {"user_id": user_id}},
        upsert=True,
    )
    return snapshot


def _days_between(iso_a: Optional[str], iso_b: Optional[str]) -> Optional[int]:
    if not iso_a or not iso_b:
        return None
    try:
        a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
        b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    except Exception:
        return None
    return abs(int((a - b).total_seconds() // 86400))


def _pick_baseline(snapshots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the snapshot closest to RETAKE_INTERVAL_DAYS before the
    most recent one. Falls back to the oldest snapshot if nothing
    older than 7 days exists. Returns None when only one submission
    is on file."""
    if len(snapshots) < 2:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: s.get("submitted_at") or "")
    most_recent = sorted_snaps[-1]
    older = sorted_snaps[:-1]
    best = None
    best_score = None
    for snap in older:
        delta = _days_between(most_recent.get("submitted_at"), snap.get("submitted_at"))
        if delta is None:
            continue
        # Score = how close delta is to the target interval; closer is better.
        score = abs(delta - RETAKE_INTERVAL_DAYS)
        if best_score is None or score < best_score:
            best = snap
            best_score = score
    return best or sorted_snaps[0]


def _section_movers(
    recent: Optional[Dict[str, Any]],
    baseline: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build an ordered list of per-section movers for the UI change
    bars. Positive `delta` = that section improved."""
    if not recent or not baseline:
        return []
    base_map = {s["id"]: s for s in baseline.get("section_avgs") or []}
    out: List[Dict[str, Any]] = []
    for cur in recent.get("section_avgs") or []:
        prev = base_map.get(cur.get("id"))
        if prev is None:
            continue
        cur_avg = cur.get("avg")
        prev_avg = prev.get("avg")
        if cur_avg is None or prev_avg is None:
            continue
        delta = round(float(cur_avg) - float(prev_avg), 2)
        out.append({
            "id":           cur.get("id"),
            "number":       cur.get("number"),
            "name":         cur.get("name"),
            "prev_rating":  prev.get("rating"),
            "cur_rating":   cur.get("rating"),
            "prev_avg":     prev_avg,
            "cur_avg":      cur_avg,
            "delta":        delta,
            "direction":    "up" if delta > 0.1 else "down" if delta < -0.1 else "flat",
        })
    # Sort by biggest-move-first so the UI can show the strongest
    # changers at the top.
    out.sort(key=lambda m: abs(m["delta"]), reverse=True)
    return out


async def build_progress_payload(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
) -> Dict[str, Any]:
    """Shape the response the frontend progress tile consumes.

    Keys:
      snapshots       — full ordered list of lightweight snapshots
      overall_series  — [{submitted_at, value, rating}] for the sparkline
      recent          — most-recent snapshot (or null)
      baseline        — closest snapshot to RETAKE_INTERVAL_DAYS ago (or null)
      section_movers  — ordered list for the change bars
      radar           — {labels, recent, baseline} ready for a radar chart
      days_since_last — int or null
      retake_due      — bool (days_since_last >= RETAKE_INTERVAL_DAYS)
      retake_interval_days — the configured interval (60)
      sample_pdf_url  — public sample link for the "See a sample" CTA
    """
    doc = await db[HISTORY_COLLECTION].find_one({"_id": user_id}, {"_id": 0})
    snapshots: List[Dict[str, Any]] = sorted(
        (doc or {}).get("snapshots") or [],
        key=lambda s: s.get("submitted_at") or "",
    )
    overall_series = [
        {
            "submitted_at": s.get("submitted_at"),
            "value":        s.get("overall_value") or _rating_value(s.get("overall_rating")),
            "rating":       s.get("overall_rating"),
        }
        for s in snapshots
    ]

    recent = snapshots[-1] if snapshots else None
    baseline = _pick_baseline(snapshots)

    # Radar needs matching ordered labels; the baseline + recent
    # snapshots share the same section schema so we just use recent's.
    radar_labels: List[str] = []
    radar_recent: List[float] = []
    radar_baseline: List[float] = []
    if recent:
        base_map = {}
        if baseline:
            base_map = {s["id"]: s for s in baseline.get("section_avgs") or []}
        for cur in recent.get("section_avgs") or []:
            if cur.get("avg") is None:
                continue
            radar_labels.append(cur.get("name") or cur.get("id") or "")
            radar_recent.append(float(cur.get("avg") or 0.0))
            prev = base_map.get(cur.get("id"))
            radar_baseline.append(
                float((prev or {}).get("avg") or 0.0) if prev else 0.0
            )

    days_since_last = _days_between(_now_iso(), (recent or {}).get("submitted_at"))

    return {
        "snapshots":             snapshots,
        "overall_series":        overall_series,
        "recent":                recent,
        "baseline":              baseline,
        "section_movers":        _section_movers(recent, baseline),
        "radar": {
            "labels":   radar_labels,
            "recent":   radar_recent,
            "baseline": radar_baseline if baseline else [],
        },
        "days_since_last":       days_since_last,
        "retake_due":            (days_since_last is not None and days_since_last >= RETAKE_INTERVAL_DAYS),
        "retake_interval_days":  RETAKE_INTERVAL_DAYS,
        "sample_pdf_url":        "/api/insights/samples/coparenting-self-assessment.pdf",
    }
