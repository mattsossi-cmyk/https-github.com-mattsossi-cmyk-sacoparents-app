"""Shared Mediation Summary / Agreement draft copies (share link, text, mediator email).

A shared copy never carries the Issues safety text, reflection answers or the readiness score.
Documents made before this rule (no `clean_inputs`) were written by an AI that could see the safety text and
reflection answers: their old links stop working, and a new share uses an AI rewrite made without them, or,
if that isn't possible, only the child goals and the priority agenda.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import ai_service
import report_visibility
from prep_privacy import SHARE_OWN_ONLY, for_document_ai, scrub_readiness

log = logging.getLogger(__name__)

CLEAN = "clean_inputs"
OLD_LINK = "This was made before a privacy update. Please ask the parent for a new link."
COLL = {"summary": ("summaries", "summary_id"), "agreement": ("agreements", "agreement_id")}
FILENAME = {"summary": "Mediation_Summary.pdf", "agreement": "Co-Parenting_Agreement_Draft.pdf"}
_FALLBACK_SHOWN = {"summary": {"child_goals", "priority_agenda"}, "agreement": {"shared_goals", "priority_items"}}
_FALLBACK_KEEP = {"summary": ("priority_agenda",), "agreement": ("shared_goals", "priority_items")}
_INTERNAL = ("prep_snapshot", "share_copy", "share_copy_at", "visibility")


def shared_excluded(kind: str, excluded: List[str] | None) -> List[str]:
    return report_visibility.clean_excluded(kind, list(excluded or []) + SHARE_OWN_ONLY[kind])


async def _rewrite(kind: str, doc: Dict[str, Any], user_name: str) -> Dict[str, Any]:
    snap = for_document_ai(doc.get("prep_snapshot") or {})
    snap.pop("readiness", None)
    if kind == "summary":
        out = await ai_service.generate_summary(snap, user_name)
    else:
        out = await ai_service.generate_agreement_draft({k: snap.get(k) for k in ("child_goals", "issues", "priority")}, user_name)
    return scrub_readiness(out)


async def prepare(db, kind: str, doc: Dict[str, Any], user) -> None:
    """On a new share of an older document: an AI rewrite without the safety text or reflection answers (kept for later opens)."""
    if doc.get(CLEAN) or doc.get("share_copy") or not getattr(user, "ai_notice_current", False):
        return
    try:
        copy = await _rewrite(kind, doc, getattr(user, "name", "") or "")
    except Exception as exc:  # noqa: BLE001 — falls back to child goals + priority agenda
        log.warning("share rewrite failed for %s: %s", kind, exc)
        return
    coll, key = COLL[kind]
    await db[coll].update_one({key: doc[key]}, {"$set": {"share_copy": copy, "share_copy_at": datetime.now(timezone.utc).isoformat()}})
    doc["share_copy"] = copy


def shared_view(kind: str, doc: Dict[str, Any], excluded: List[str] | None) -> Tuple[Dict[str, Any], List[str]]:
    """The document a recipient gets and the sections hidden from it."""
    _, key = COLL[kind]
    ex = shared_excluded(kind, excluded)
    base = {key: doc.get(key), "generated_at": doc.get("generated_at")}
    if doc.get(CLEAN):
        return {**scrub_readiness({k: v for k, v in doc.items() if k not in _INTERNAL}), **base}, ex
    if doc.get("share_copy"):
        return {**doc["share_copy"], **base}, ex
    hidden = [s["key"] for s in report_visibility.REPORT_SECTIONS[kind] if s["key"] not in _FALLBACK_SHOWN[kind]]
    return {**base, **{k: doc.get(k) for k in _FALLBACK_KEEP[kind]}}, report_visibility.clean_excluded(kind, hidden)


def shared_agreement(doc: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """An agreement draft as anyone other than its parent sees it (joint draft, Complete Coparenting Report)."""
    return shared_view("agreement", doc, None)[0] if doc else doc
