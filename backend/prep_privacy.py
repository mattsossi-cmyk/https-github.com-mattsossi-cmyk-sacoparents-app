"""Mediation Prep privacy rules.

* The Issues safety text stays in the parent's saved record only: never shown, sent to AI, or shared.
* Reflection answers only reach the parent's own AI coach (never the Summary / Agreement prompts).
* Shared Summary / Agreement copies never carry the readiness score.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional

SAFETY_ISSUE = "safety_concerns"
SHARE_OWN_ONLY = {"summary": ["readiness", "changes_since_last"], "agreement": ["changes_since_last"]}
READINESS_KEYS = ("readiness", "readiness_score", "readiness_label", "readiness_narrative", "dimension_narratives",
                  "changes_since_last")
_READINESS_RE = re.compile(r"readiness|needs support|moderately ready|prepared for mediation|\b\d{1,3}\s*/\s*100\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def clean_issues(issues: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(issues, dict):
        return issues
    out = copy.deepcopy(issues)
    out.pop("safety", None)
    if isinstance(out.get("items"), dict):
        out["items"].pop(SAFETY_ISSUE, None)
    return out


def saved_safety_text(issues: Optional[Dict[str, Any]]) -> str:
    return (((issues or {}).get("items") or {}).get(SAFETY_ISSUE) or "") if isinstance(issues, dict) else ""


def without_safety_text(prep: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(prep or {})
    if "issues" in out:
        out["issues"] = clean_issues(out["issues"])
    return out


def for_document_ai(prep: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Prompt input for AI documents that can be shared: no safety text, no reflection answers."""
    out = without_safety_text(prep)
    out.pop("reflection", None)
    return out


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(s for s in _SENTENCE.split(value) if not _READINESS_RE.search(s)).strip()
    if isinstance(value, list):
        kept: List[Any] = []
        for v in value:
            if isinstance(v, str) and _READINESS_RE.search(v):
                continue
            if isinstance(v, dict) and any(isinstance(x, str) and _READINESS_RE.search(x) for x in v.values()):
                continue
            kept.append(_scrub(v))
        return kept
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    return value


def scrub_readiness(doc: Dict[str, Any]) -> Dict[str, Any]:
    """A shared copy: readiness score, label, narrative and any sentence that mentions them removed."""
    out = {k: v for k, v in doc.items() if k not in READINESS_KEYS}
    return {k: (v if k.endswith("_id") or k in ("user_id", "generated_at") else _scrub(v)) for k, v in out.items()}
