"""Small helper to build the `signed_by` / `signed_at` kwargs when the
`?sign=true` query parameter is set on a PDF download endpoint.

Every PDF builder accepts `signed_by` + `signed_at` — this consolidates
the "should we sign?" logic in one place so routes stay tiny.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def sign_kwargs(sign: bool, name: str | None) -> Dict[str, Any]:
    """Return `{signed_by, signed_at}` when the user opted in — else `{}`.

    Timestamp is always UTC ISO-8601 at the moment of the download so the
    stamp reflects when the PDF was generated (not when the report was
    first authored).
    """
    if not sign or not name:
        return {}
    return {
        "signed_by": name,
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }
