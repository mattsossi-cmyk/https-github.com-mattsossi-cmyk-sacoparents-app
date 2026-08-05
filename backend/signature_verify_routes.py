"""Public signature verification endpoint.

When a signed PDF is downloaded from SA CoParents, a small QR code is
stamped next to the signature line. The QR resolves to a frontend URL
`/verify/{sig_id}?n=...&t=...&note=...` which itself hits
`GET /api/verify/{sig_id}` to confirm whether the signature tuple
matches.

No DB lookup is required — the sig_id is a deterministic SHA of
`(SIGNATURE_VERIFY_SECRET, name, timestamp, note)`, so any tampering
with the query params breaks the hash and the route reports untampered
= False. This keeps the verify surface a static, cache-friendly read.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from pdf_signing import verify_signature_id


router = APIRouter(prefix="/verify", tags=["signature-verify"])


@router.get("/{sig_id}")
async def verify_signature(
    sig_id: str,
    n: Optional[str] = Query(None, description="signed_by name"),
    t: Optional[str] = Query(None, description="signed_at ISO-8601"),
    note: Optional[str] = Query(None, description="optional signed_note"),
):
    """Return whether `sig_id` matches the tuple `(n, t, note)` under
    the current SIGNATURE_VERIFY_SECRET. All fields required except
    `note` (which is optional to preserve backward-compat with QR codes
    generated for signatures without a note)."""
    if not n or not t:
        return {
            "signature_id":  sig_id,
            "untampered":    False,
            "reason":        "missing_signature_fields",
        }
    clean_note = (note or "").strip() or None
    untampered = verify_signature_id(sig_id, n, t, clean_note)
    return {
        "signature_id":  sig_id,
        "untampered":    untampered,
        "signed_by":     n if untampered else None,
        "signed_at":     t if untampered else None,
        "signed_note":   clean_note if untampered else None,
        "reason":        None if untampered else "hash_mismatch",
    }
