"""Professional-only live views over the parent-app bridge (never stored, never exported). Hidden unless PARENT_APP_LINK_CONTRACT is on."""
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from core import db
from joint_helpers import get_joint_report_doc
from parent_app_contract import PARENT_APP_LINK_CONTRACT, case_context, fetch_aggregate, fetch_safe_contact

NO_ACCESS = "The SA CoParents service did not release information for this link. Ask the parent to confirm the link for this case, then try again."


async def _pro_case(rid: str, user: dict) -> dict:
    doc = await get_joint_report_doc(rid, user)
    if not (user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))):
        raise HTTPException(status_code=403, detail="Assigned professional only")
    if not PARENT_APP_LINK_CONTRACT:
        raise HTTPException(status_code=404, detail="Not available")
    return doc


def build_router(log_access) -> APIRouter:
    router = APIRouter()

    @router.get("/joint/reports/{rid}/bridge/safe-contact/{role}")
    async def bridge_safe_contact(rid: str, role: str, user=Depends(get_current_user)):
        doc = await _pro_case(rid, user)
        if role not in ("a", "b"):
            raise HTTPException(status_code=400, detail="Invalid role")
        parent_uid = ((doc.get("participants") or {}).get(role) or {}).get("user_id")
        link = await db.account_links.find_one({"user_id": parent_uid}) if parent_uid else None
        if not link:
            raise HTTPException(status_code=404, detail=NO_ACCESS)
        await log_access(doc, user, f"Viewed Parent {role.upper()} SA CoParents App contact preference (professional-only)", "safe_contact_bridge")
        return {"safe_contact": await fetch_safe_contact(link["external_email"], *case_context(doc))}

    @router.get("/joint/reports/{rid}/bridge/aggregate")
    async def bridge_aggregate(rid: str, user=Depends(get_current_user)):
        doc = await _pro_case(rid, user)
        return await fetch_aggregate(*case_context(doc))

    return router
