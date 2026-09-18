"""Bundle Download — one ZIP of every PDF the signed-in parent has ready.

Iter204. The dashboard's "Your Reports" surface links to ~10 separate
PDF endpoints. Parents kept complaining that gathering everything they
had completed meant clicking through each one and remembering which
they'd already downloaded. This endpoint wraps whichever are ready in
a single ZIP with a plain-text MANIFEST at the root explaining what's
inside and (when transparent) what was skipped because it hasn't been
completed yet.

Design choices:
  * In-process ASGI calls via httpx (`ASGITransport`) so we reuse every
    builder's authentication, guardrails, PHI-access logging, and 404/409
    empty-state contracts EXACTLY as the parent would experience them.
    No duplication of the "what does 'ready' mean?" logic.
  * Cookies from the incoming request are forwarded verbatim, so the
    caller's auth state is preserved. `Authorization` header (Bearer)
    is forwarded as a fallback for API clients.
  * 200 → include PDF in the ZIP under a friendly filename.
  * 404 / 409 / 4xx → silently skip; note in the manifest.
  * 500 / network error → note as an error in the manifest, keep going.
  * Empty ZIP (nothing to include) returns HTTP 409 with a friendly
    detail so the frontend `downloadPdf` helper deep-links back to the
    dashboard.

Route:
  GET /api/bundle/my-completed.zip   (auth required)
"""
from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from auth import get_current_user
from models import UserPublic


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bundle", tags=["bundle"])


# --------------------------------------------------------------------- #
# Endpoint catalog.
#
# Each entry describes ONE per-parent PDF the bundle should try to
# include. `path` is the absolute API path (prefixed with `/api`).
# `filename` is the name that lands inside the ZIP. `label` is the
# human-readable name printed in the manifest.
#
# `id_from` is optional — when set, the bundler first hits that JSON
# endpoint to pull the parent's owned artefact IDs (from `id_field`),
# then substitutes {id} into `path` for each ID discovered. This
# powers the Safety Assessment (`/me` returns the latest assessment
# object) without hard-coding IDs on the client.
# --------------------------------------------------------------------- #
_STATIC_ENDPOINTS: List[Dict[str, str]] = [
    {
        "path": "/api/mediation/foundation-statement.pdf",
        "filename": "01-foundation-statement.pdf",
        "label": "Foundation Statement",
    },
    {
        "path": "/api/coparenting/report/pdf",
        "filename": "02-coparenting-assessment.pdf",
        "label": "Co-Parenting Assessment",
    },
    {
        "path": "/api/snc2/report/pdf",
        "filename": "03-child-needs-statement.pdf",
        "label": "Child Needs Statement",
    },
    {
        "path": "/api/edu-deep/report/pdf",
        "filename": "04-educational-deep-dive.pdf",
        "label": "Educational Deep-Dive",
    },
    {
        "path": "/api/med-deep/report/pdf",
        "filename": "05-medical-deep-dive.pdf",
        "label": "Medical Deep-Dive",
    },
    {
        "path": "/api/psych-deep/report/pdf",
        "filename": "06-psychological-deep-dive.pdf",
        "label": "Psychological Deep-Dive",
    },
    {
        "path": "/api/pathway-report/preview/pdf",
        "filename": "07-pathway-report-preview.pdf",
        "label": "Dispute Resolution Pathway Report (preview)",
    },
    {
        "path": "/api/complete-report/mine.pdf",
        "filename": "08-complete-alignment-report.pdf",
        "label": "Complete Alignment Report (individual)",
    },
]


# Endpoints that need a list-first lookup. The lookup endpoint returns
# the caller's owned artefact id(s); the bundler then hits the PDF
# route with that id substituted in.
_LOOKUP_ENDPOINTS: List[Dict[str, Any]] = [
    {
        "lookup_path": "/api/safety-assessment/me",
        "id_field": "id",  # top-level `id` on the /me response
        "pdf_path_template": "/api/safety-assessment/{id}/pdf",
        "filename": "09-safety-assessment.pdf",
        "label": "Safety Assessment",
    },
]


_REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_PER_REQUEST_TIMEOUT_S = 20.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def _fetch_pdf(
    client: httpx.AsyncClient,
    path: str,
    forwarded_headers: Dict[str, str],
    forwarded_cookies: Dict[str, str],
) -> Tuple[Optional[bytes], int, str]:
    """Fetch `path` in-process. Returns (bytes|None, status_code, detail).

    Only returns bytes on 200 with `application/pdf`-shaped content.
    A 404/409 is a "not ready yet" signal; anything else logs & is
    reported in the manifest without blocking the rest of the bundle.
    """
    try:
        resp = await asyncio.wait_for(
            client.get(path, headers=forwarded_headers, cookies=forwarded_cookies),
            timeout=_PER_REQUEST_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        return None, 0, "timeout"
    except httpx.HTTPError as exc:
        return None, 0, f"transport error: {exc.__class__.__name__}"

    if resp.status_code == 200 and resp.content:
        # Cheap PDF-signature sanity check — never zip garbage bytes.
        if resp.content[:4] == b"%PDF":
            return resp.content, 200, "ok"
        return None, 200, "invalid PDF signature"

    detail = ""
    try:
        payload = resp.json()
        detail = payload.get("detail") or ""
    except Exception:  # noqa: BLE001
        detail = ""
    return None, resp.status_code, detail


async def _resolve_lookup_id(
    client: httpx.AsyncClient,
    lookup_path: str,
    id_field: str,
    forwarded_headers: Dict[str, str],
    forwarded_cookies: Dict[str, str],
) -> Optional[str]:
    """Fetch a JSON lookup endpoint, return the caller's artefact id or None."""
    try:
        resp = await asyncio.wait_for(
            client.get(
                lookup_path, headers=forwarded_headers, cookies=forwarded_cookies,
            ),
            timeout=_PER_REQUEST_TIMEOUT_S,
        )
    except (asyncio.TimeoutError, httpx.HTTPError):
        return None
    if resp.status_code != 200:
        return None
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(payload, dict):
        return None
    val = payload.get(id_field)
    return str(val) if val else None


def _build_forwarded_context(request: Request) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Extract the auth header + cookies to forward on in-process calls."""
    headers: Dict[str, str] = {}
    auth = request.headers.get("authorization")
    if auth:
        headers["authorization"] = auth
    cookies = dict(request.cookies)
    return headers, cookies


def _write_manifest(
    zf: zipfile.ZipFile,
    parent_name: str,
    included: List[Dict[str, str]],
    skipped: List[Dict[str, str]],
) -> None:
    """Drop a plain-text MANIFEST.txt at the ZIP root explaining what's inside."""
    lines: List[str] = []
    lines.append("SA CoParents · Report Bundle")
    lines.append("=" * 40)
    lines.append(f"Prepared for : {parent_name}")
    lines.append(f"Generated at : {_now_iso()}")
    lines.append("")
    lines.append(f"Included ({len(included)}):")
    if included:
        for item in included:
            lines.append(f"  • {item['label']}  →  {item['filename']}")
    else:
        lines.append("  (none — see 'Not yet' below)")
    lines.append("")
    if skipped:
        lines.append(f"Not yet completed ({len(skipped)}):")
        for item in skipped:
            note = item.get("note") or ""
            suffix = f"  ({note})" if note else ""
            lines.append(f"  • {item['label']}{suffix}")
        lines.append("")
    lines.append(
        "Every PDF in this ZIP was generated with the same guardrails as "
        "the individual download buttons in the app. It is a preparation "
        "resource — not a custody evaluation, diagnosis, or a "
        "recommendation to any court."
    )
    zf.writestr("MANIFEST.txt", "\n".join(lines))


@router.get("/my-completed.zip")
async def download_my_completed_bundle(
    request: Request,
    current: UserPublic = Depends(get_current_user),
) -> Response:
    """Stream a ZIP containing every per-parent PDF the caller has ready.

    Individual endpoints that reply 404/409 (empty state) are silently
    skipped and noted in the ZIP's MANIFEST.txt so the parent knows why
    a report they expected isn't inside. Returns HTTP 409 with a
    friendly detail when nothing is ready — the frontend's
    `downloadPdf` helper turns that into a "Finish an assessment first"
    toast with a dashboard action button.
    """
    forwarded_headers, forwarded_cookies = _build_forwarded_context(request)
    # In-process ASGI transport — every request goes through the full
    # FastAPI middleware stack, dependency injection, and route logic.
    transport = httpx.ASGITransport(app=request.app)
    included: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []

    buf = io.BytesIO()
    zf = zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED)

    async with httpx.AsyncClient(
        transport=transport, base_url="http://bundle.internal",
        timeout=_REQUEST_TIMEOUT,
    ) as client:
        # Static endpoints (no lookup needed).
        for entry in _STATIC_ENDPOINTS:
            pdf_bytes, status, note = await _fetch_pdf(
                client, entry["path"], forwarded_headers, forwarded_cookies,
            )
            if pdf_bytes:
                zf.writestr(entry["filename"], pdf_bytes)
                included.append(
                    {"label": entry["label"], "filename": entry["filename"]},
                )
            else:
                skipped.append(
                    {
                        "label": entry["label"],
                        "note": _skip_note(status, note),
                    },
                )

        # Lookup-first endpoints.
        for entry in _LOOKUP_ENDPOINTS:
            artefact_id = await _resolve_lookup_id(
                client,
                entry["lookup_path"],
                entry["id_field"],
                forwarded_headers,
                forwarded_cookies,
            )
            if not artefact_id:
                skipped.append(
                    {
                        "label": entry["label"],
                        "note": "not started yet",
                    },
                )
                continue
            path = entry["pdf_path_template"].format(id=artefact_id)
            pdf_bytes, status, note = await _fetch_pdf(
                client, path, forwarded_headers, forwarded_cookies,
            )
            if pdf_bytes:
                zf.writestr(entry["filename"], pdf_bytes)
                included.append(
                    {"label": entry["label"], "filename": entry["filename"]},
                )
            else:
                skipped.append(
                    {
                        "label": entry["label"],
                        "note": _skip_note(status, note),
                    },
                )

    parent_name = getattr(current, "name", None) or getattr(current, "email", "you")
    _write_manifest(zf, parent_name, included, skipped)
    zf.close()

    if not included:
        raise HTTPException(
            status_code=409,
            detail=(
                "You haven't completed any assessments yet. Once you finish "
                "one, come back here to download everything in a single ZIP."
            ),
        )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"sacoparents-my-reports-{stamp}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Bundles are user-specific and always live — never cache.
            "Cache-Control": "no-store",
            "X-SACoParents-Bundle-Included": str(len(included)),
            "X-SACoParents-Bundle-Skipped": str(len(skipped)),
        },
    )


def _skip_note(status: int, detail: str) -> str:
    """Compact human-friendly reason for the manifest 'Not yet' section."""
    if status == 200:
        return "invalid PDF"
    if status in (404, 409):
        return "not completed yet"
    if status == 401:
        return "authentication required"
    if status == 403:
        return "access blocked"
    if status == 0:
        return detail or "unreachable"
    return f"HTTP {status}"
