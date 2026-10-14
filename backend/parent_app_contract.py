"""Parent-app link contract (sacoparentsapp.online ↔ Align), 2026-10-14 version from the parent-app builder.
Behind PARENT_APP_LINK_CONTRACT (default false = current behaviour). Secret is read from env and never logged or echoed."""
import os

import httpx
from fastapi import HTTPException

from core import EXTERNAL_APP_URL, INTEGRATION_SECRET, logger

PARENT_APP_LINK_CONTRACT = os.environ.get("PARENT_APP_LINK_CONTRACT", "false").lower() == "true"

# Neutral, user-facing wording — no safety / screening / flag words.
MSG_NO_ACCESS = "The SA CoParents service did not release information for this link. Ask the parent to confirm the link for this case, then try again."
MSG_NO_ASSESSMENTS = "No completed assessments were found for the linked SA CoParents account."
MSG_BAD_CODE = "Invalid or expired link code"
MSG_NOT_CONFIGURED = "The SA CoParents connection is not available right now. Please try again later."
MSG_CONFIG_ERROR = "The SA CoParents connection is not set up correctly. Please contact support."
MSG_UNREACHABLE = "Could not reach the SA CoParents service. Try again later."


def contract_headers(professional_id: str | None, case_id: str | None, professional_email: str | None = None) -> dict:
    h = {"X-Integration-Key": INTEGRATION_SECRET}
    if PARENT_APP_LINK_CONTRACT:
        if professional_id:
            h["X-Professional-Id"] = str(professional_id)
        if case_id:
            h["X-Case-Id"] = str(case_id)
        if professional_email:
            h["X-Professional-Email"] = professional_email
    return h


def case_context(doc: dict | None) -> tuple[str | None, str | None]:
    if not doc:
        return None, None
    return (doc.get("professional_id") or doc.get("created_by")), doc.get("id")


def map_refusal(resp: httpx.Response, not_found_default: str = MSG_NO_ACCESS) -> HTTPException:
    """Parent-app refusals → neutral Align errors. 404s are deliberately indistinguishable upstream; we only vary on its own detail text."""
    detail = ""
    try:
        detail = str((resp.json() or {}).get("detail") or "")
    except Exception:  # noqa: BLE001
        detail = ""
    if resp.status_code == 401:
        logger.error("parent-app: integration key rejected")
        return HTTPException(status_code=502, detail=MSG_CONFIG_ERROR)
    if resp.status_code == 503:
        return HTTPException(status_code=503, detail=MSG_NOT_CONFIGURED)
    if resp.status_code == 400:
        logger.error("parent-app: request rejected (%s)", detail[:80])
        return HTTPException(status_code=502, detail=MSG_CONFIG_ERROR)
    if resp.status_code == 403:
        return HTTPException(status_code=404, detail=MSG_NO_ACCESS)
    if resp.status_code == 404:
        if detail.lower().startswith("no completed assessments"):
            return HTTPException(status_code=404, detail=MSG_NO_ASSESSMENTS)
        if detail.lower().startswith("invalid or expired link code"):
            return HTTPException(status_code=400, detail=MSG_BAD_CODE)
        return HTTPException(status_code=404, detail=not_found_default)
    return HTTPException(status_code=502, detail=MSG_UNREACHABLE)


async def _call(method: str, path: str, **kw) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            return await c.request(method, f"{EXTERNAL_APP_URL}{path}", **kw)
    except Exception as e:  # noqa: BLE001
        logger.error("parent-app %s %s unreachable: %s", method, path, type(e).__name__)
        raise HTTPException(status_code=502, detail=MSG_UNREACHABLE)


async def verify_link_code(code: str, professional_id: str | None, case_id: str | None) -> str:
    body = {"code": code}
    if PARENT_APP_LINK_CONTRACT:
        if not (professional_id and case_id):
            raise HTTPException(status_code=400, detail="Link your SA CoParents account from inside the case your professional invited you to.")
        body.update({"professional_id": str(professional_id), "case_id": str(case_id)})
    resp = await _call("POST", "/api/integrations/verify-link-code", headers=contract_headers(professional_id, case_id), json=body)
    if resp.status_code != 200:
        if not PARENT_APP_LINK_CONTRACT:
            raise HTTPException(status_code=400, detail=MSG_BAD_CODE)
        raise map_refusal(resp)
    email = ((resp.json() or {}).get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=502, detail="Unexpected response from the SA CoParents service")
    return email


async def export_assessments(email: str, professional_id: str | None, case_id: str | None) -> dict:
    resp = await _call("GET", "/api/integrations/export-assessments", headers=contract_headers(professional_id, case_id), params={"email": email})
    if resp.status_code != 200:
        raise map_refusal(resp, not_found_default=MSG_NO_ASSESSMENTS if not PARENT_APP_LINK_CONTRACT else MSG_NO_ACCESS)
    data = resp.json() or {}
    scope = data.get("access_scope") or ("case" if not PARENT_APP_LINK_CONTRACT else "legacy_unscoped")
    if scope != "case":
        # Summary only: never trust item-level data or safety fields outside a case-scoped release.
        data = {k: v for k, v in data.items() if k not in ("responses",)}
        data["safety_flags"] = None
        for a in data.get("assessments") or []:
            if isinstance(a, dict):
                a.pop("responses", None)
    data["access_scope"] = scope
    return data


async def fetch_safe_contact(email: str, professional_id: str, case_id: str) -> dict | None:
    """Professional-only, access-logged use. Never stored, never in reports/PDFs/emails/exports."""
    resp = await _call("GET", "/api/integrations/safe-contact", headers=contract_headers(professional_id, case_id), params={"email": email})
    if resp.status_code != 200:
        raise map_refusal(resp)
    return (resp.json() or {}).get("safe_contact")


async def assign_screening_version(email: str, version: str, professional_id: str, case_id: str) -> bool:
    resp = await _call("POST", "/api/integrations/screening/assign", headers=contract_headers(professional_id, case_id), json={"email": email, "version": version})
    if resp.status_code != 200:
        raise map_refusal(resp)
    return True


async def fetch_aggregate(professional_id: str, case_id: str) -> dict:
    resp = await _call("GET", "/api/integrations/aggregate", headers=contract_headers(professional_id, None), params={"case_id": case_id})
    if resp.status_code != 200:
        raise map_refusal(resp)
    return resp.json() or {}
