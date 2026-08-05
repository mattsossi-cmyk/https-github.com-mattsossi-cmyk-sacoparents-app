"""Small helper to build the `signed_by` / `signed_at` / `signed_note` kwargs
when the `?sign=true` query parameter is set on a PDF download endpoint.

Every PDF builder accepts `signed_by` + `signed_at` (+ optional
`signed_note`) — this consolidates the "should we sign?" logic in one
place so routes stay tiny.

Iteration 72 also emits `signed_verify_id` + `signed_verify_url`. The
QR code stamped alongside the signature encodes the verify URL; the
public verify page reconstructs the tuple `(signed_by, signed_at,
signed_note, verify_id)` from the URL and confirms the hash matches
`sha256(SIGNATURE_VERIFY_SECRET + name + timestamp + note)`. This gives
us a tamper-evident signature without any DB write on the hot path.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote


_NOTE_MAX_CHARS = 120
_SIG_SECRET_ENV = "SIGNATURE_VERIFY_SECRET"
_SIG_ID_LEN = 16  # short prefix of the sha256, plenty for uniqueness + URL brevity


def _sig_secret() -> str:
    """Fetch the HMAC secret. Falls back to a deterministic dev salt so
    verify keeps working in local/preview even if the env var is unset."""
    return os.environ.get(_SIG_SECRET_ENV) or "sacop-signature-verify-secret-dev-only"


def compute_signature_id(signed_by: str, signed_at: str,
                         signed_note: Optional[str] = None) -> str:
    """Deterministic short id derived from the signature tuple + secret."""
    payload = f"{_sig_secret()}|{signed_by}|{signed_at}|{signed_note or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_SIG_ID_LEN]


def verify_signature_id(signature_id: str, signed_by: str, signed_at: str,
                        signed_note: Optional[str] = None) -> bool:
    """True iff `signature_id` matches the tuple. Any tampered field
    (name, timestamp, note) breaks the hash."""
    if not signature_id or len(signature_id) != _SIG_ID_LEN:
        return False
    return compute_signature_id(signed_by, signed_at, signed_note) == signature_id


def _public_base_url() -> str:
    """External base URL used inside QR codes. Reads REACT_APP_BACKEND_URL
    from env — that's the public preview/prod host. Falls back to a
    relative URL if unset so verify links stay clickable on-domain."""
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def _build_verify_url(sig_id: str, name: str, ts: str, note: Optional[str]) -> str:
    """Assemble the public verify URL. The tuple is passed as query
    params so verify page can reconstruct + hash-check without a DB."""
    q = f"n={quote(name)}&t={quote(ts)}"
    if note:
        q += f"&note={quote(note)}"
    base = _public_base_url()
    return f"{base}/verify/{sig_id}?{q}" if base else f"/verify/{sig_id}?{q}"


def sign_kwargs(sign: bool, name: str | None,
                note: Optional[str] = None) -> Dict[str, Any]:
    """Return `{signed_by, signed_at, signed_note?}` when the user opted
    in — else `{}`.

    Timestamp is always UTC ISO-8601 at the moment of the download so
    the stamp reflects when the PDF was generated (not when the report
    was first authored).

    `note` (if provided) is silently trimmed + clamped to
    `_NOTE_MAX_CHARS` so a stray paste never breaks PDF layout.

    Note: the tamper-evident QR + verify URL are derived on-the-fly
    from `signed_by`/`signed_at`/`signed_note` inside
    `pdf_watermark.stamp_signature_line`, so this helper does NOT need
    to plumb `signed_verify_id`/`signed_verify_url` through to the
    various PDF builders.
    """
    if not sign or not name:
        return {}
    signed_at = datetime.now(timezone.utc).isoformat()
    kwargs: Dict[str, Any] = {
        "signed_by": name,
        "signed_at": signed_at,
    }
    if note:
        clean = str(note).strip()
        if len(clean) > _NOTE_MAX_CHARS:
            clean = clean[:_NOTE_MAX_CHARS].rstrip()
        if clean:
            kwargs["signed_note"] = clean
    return kwargs
