"""Phase 5a: safety training acknowledgment gate + supervising-professional role. Gate applies to screening responses and the safety review."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

TRAINING_VERSION = "2026-10-16.1"
TRAINING = {
    "version": TRAINING_VERSION,
    "title": "Safety screening training acknowledgment",
    "intro": "Before opening any parent's private check-in or the safety review, confirm you have read these points. This is recorded with the date and version.",
    "modules": [
        {"heading": "Fixed rules, your decision", "body": "Red, Amber and Green come from fixed, transparent rules — not AI and not a score. They alert you; they never restrict a parent or pause a case on their own. You decide the pathway, concern level and provisions."},
        {"heading": "What parents see", "body": "Parents never see a tier, flag, score or the other parent's answers. Every parent gets the same questions. Declining the check-in is a neutral status, not a finding."},
        {"heading": "What leaves this screen", "body": "Item-level answers, free text, triggered rules and tier colours stay professional-only. Court, co-parent and report outputs carry only a neutral receipt line, and every export is scanned for screening wording before download."},
        {"heading": "Safe contact and devices", "body": "Use a parent's safe-contact details only for the purpose they gave them. Never confirm to one parent what the other disclosed. Encourage private-device use."},
        {"heading": "Lowering a Red", "body": "Lowering a Red concern level to Amber, Green or none requires a second, supervising professional's sign-off. Record your reasons; the supervisor records theirs."},
        {"heading": "Mandatory reporting", "body": "Suspected child abuse or neglect must be reported (in Texas, any person must report). This training does not replace your professional, ethical or legal obligations."},
    ],
    "acknowledgment": "I have read the six points above and will handle private check-in information as described.",
}


def training_current(user: dict) -> bool:
    return (user.get("safety_training") or {}).get("version") == TRAINING_VERSION


async def require_training(db, user: dict) -> None:
    if user.get("role") not in ("professional", "admin"):
        return
    full = await db.users.find_one({"_id": user["_id"]}, {"safety_training": 1})
    if not training_current(full or {}):
        raise HTTPException(status_code=428, detail={"code": "training_required", "message": "Complete the safety screening training acknowledgment before opening private check-in information.", "version": TRAINING_VERSION})


async def is_supervisor(db, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    full = await db.users.find_one({"_id": user["_id"]}, {"is_supervisor": 1})
    return bool((full or {}).get("is_supervisor"))


class AckIn(BaseModel):
    version: str
    acknowledged: bool = False


class SupervisorIn(BaseModel):
    is_supervisor: bool


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/professional-training")
    async def get_training(user=Depends(get_current_user)):
        full = await db.users.find_one({"_id": user["_id"]}, {"safety_training": 1, "is_supervisor": 1, "role": 1}) or {}
        return {"training": TRAINING, "current": training_current(full), "acknowledged": full.get("safety_training"), "is_supervisor": await is_supervisor(db, user)}

    @r.post("/professional-training/acknowledge")
    async def ack(body: AckIn, user=Depends(get_current_user)):
        if user.get("role") not in ("professional", "admin"):
            raise HTTPException(status_code=403, detail="Professionals only")
        if not body.acknowledged:
            raise HTTPException(status_code=400, detail="Please confirm the acknowledgment to continue")
        if body.version != TRAINING_VERSION:
            raise HTTPException(status_code=409, detail="The training has been updated. Please review the current version.")
        rec = {"version": TRAINING_VERSION, "acknowledged_at": datetime.now(timezone.utc).isoformat()}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"safety_training": rec}, "$push": {"safety_training_history": rec}})
        return {"ok": True, **rec}

    @r.patch("/admin/professionals/{uid}/supervisor")
    async def set_supervisor(uid: str, body: SupervisorIn, user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        res = await db.users.update_one({"_id": uid, "role": "professional"}, {"$set": {"is_supervisor": body.is_supervisor, "supervisor_set_at": datetime.now(timezone.utc).isoformat(), "supervisor_set_by": user["_id"]}})
        if not res.matched_count:
            raise HTTPException(status_code=404, detail="Professional not found")
        return {"ok": True, "is_supervisor": body.is_supervisor}

    @r.get("/admin/safety-audit")
    async def safety_audit(user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        rows = await db.access_events.find({"kind": {"$in": list(AUDIT_KINDS)}}, {"_id": 0}).sort("at", -1).to_list(500)
        return {"kinds": sorted(AUDIT_KINDS), "rows": rows, "total": len(rows)}

    @r.get("/admin/safety-audit.csv")
    async def safety_audit_csv(user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        import csv
        import io

        from fastapi import Response
        rows = await db.access_events.find({"kind": {"$in": list(AUDIT_KINDS)}}, {"_id": 0}).sort("at", -1).to_list(5000)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["at", "case_id", "kind", "action", "by_role", "by_name", "by"])
        for e in rows:
            w.writerow([e.get("at", ""), e.get("report_id", ""), e.get("kind", ""), e.get("action", ""), e.get("by_role", ""), e.get("by_name", ""), e.get("by", "")])
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="safety-audit-log.csv"'})

    return r


AUDIT_KINDS = {"safety_screening", "safety_screening_view", "safety_pathway", "safety_review", "safety_review_export", "export_scan_block", "supervisor_signoff",
               "invite_cadence", "redaction", "safe_contact_view", "bridge_safe_contact", "integration_write", "webhook_failed"}
