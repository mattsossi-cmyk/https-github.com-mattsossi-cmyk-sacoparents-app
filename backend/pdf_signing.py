"""Small helper to build the `signed_by` / `signed_at` / `signed_note` kwargs
when the `?sign=true` query parameter is set on a PDF download endpoint.

Every PDF builder accepts `signed_by` + `signed_at` (+ optional
`signed_note`) — this consolidates the "should we sign?" logic in one
place so routes stay tiny.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


_NOTE_MAX_CHARS = 120


def sign_kwargs(sign: bool, name: str | None,
                note: Optional[str] = None) -> Dict[str, Any]:
    """Return `{signed_by, signed_at, signed_note?}` when the user opted
    in — else `{}`.

    Timestamp is always UTC ISO-8601 at the moment of the download so
    the stamp reflects when the PDF was generated (not when the report
    was first authored).

    `note` (if provided) is silently trimmed + clamped to
    `_NOTE_MAX_CHARS` so a stray paste never breaks PDF layout.
    """
    if not sign or not name:
        return {}
    kwargs: Dict[str, Any] = {
        "signed_by": name,
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }
    if note:
        clean = str(note).strip()
        if len(clean) > _NOTE_MAX_CHARS:
            clean = clean[:_NOTE_MAX_CHARS].rstrip()
        if clean:
            kwargs["signed_note"] = clean
    return kwargs
