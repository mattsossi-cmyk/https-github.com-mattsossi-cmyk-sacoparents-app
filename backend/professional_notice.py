"""Professional Notice, Confidentiality & Safety Warning — shown to professionals on first sign-in and whenever the version changes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

PROFESSIONAL_NOTICE_VERSION = "2026-10-19.1"  # bumped: parents can see who viewed their information (owner 2026-10-19)
PROFESSIONAL_NOTICE_ROLES = ("professional",)
# Owner-approved text (2026-10-13). Edit strings here only.
NOTICE = {
    "version": PROFESSIONAL_NOTICE_VERSION,
    "brand": "SA CoParents Align",
    "title": "Professional Notice, Confidentiality & Safety Warning",
    "tagline": "Start With Safety. Alignment Before Agreement.",
    "intro": "SA CoParents Align is a structured, child-focused assessment and professional review platform designed to help identify areas of parental alignment, differences in perspectives, and potential options for meeting children's needs.",
    "section_heading": "Important Professional Notice",
    "points": [
        {"heading": "Confidentiality", "body": "Parent assessments may contain sensitive personal, family, medical, educational, psychological, or safety-related information. Professionals must protect this information and follow applicable confidentiality, privacy, and disclosure requirements."},
        {"heading": "Family Violence and Safety", "body": "When intimate partner violence, coercive control, intimidation, or other safety concerns are identified, professionals must independently evaluate whether further participation, communication, or joint processes are appropriate. Parent-to-parent communication must never be required when unsafe."},
        {"heading": "Separate Parent Perspectives", "body": "SA CoParents Align is designed to review individual parent perspectives without automatically disclosing one parent's private responses to the other parent. Any disclosure must follow applicable law, informed consent, court orders, and established safety protocols."},
        {"heading": "Access Is Visible to Parents", "body": "Parents can see when you view their information, including your name and role. Every opening of a parent's safety answers, assessment answers, Foundation Statement or communications log is recorded and listed for that parent."},
        {"heading": "Artificial Intelligence", "body": "AI may assist in organizing information, identifying reported similarities and differences, and presenting potential child-focused options. AI-generated findings are not independent verification of facts, clinical diagnoses, legal conclusions, or professional recommendations."},
        {"heading": "Professional Responsibility", "body": "Attorneys, mediators, mental health professionals, and other authorized users remain responsible for independently reviewing information, evaluating safety, identifying limitations, and determining whether a report is appropriate for its intended purpose."},
        {"heading": "Court Reports", "body": "Reports should clearly distinguish parent-reported information, AI-assisted summaries, professional observations, and professional conclusions. The court retains authority over judicial decisions."},
    ],
    "principle_heading": "SA CoParents Principle",
    "principle": "AI Structures Data. Professionals Evaluate. Courts Decide.",
    "ack_heading": "Acknowledgment",
    "checkbox": "By continuing, I acknowledge that SA CoParents Align is a professional support tool and does not replace independent legal, clinical, safety, or judicial judgment.",
    "continue": "Continue to SA CoParents Align",
}


def needs_acceptance(user: dict) -> bool:
    if user.get("role") not in PROFESSIONAL_NOTICE_ROLES:
        return False
    return (user.get("professional_notice") or {}).get("version") != PROFESSIONAL_NOTICE_VERSION


class AcceptIn(BaseModel):
    version: str
    acknowledged: bool


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/professional-notice")
    async def get_notice(user=Depends(get_current_user)):
        full = await db.users.find_one({"_id": user["_id"]}, {"role": 1, "professional_notice": 1})
        return {"notice": NOTICE, "needs_acceptance": needs_acceptance(full or {}), "accepted": (full or {}).get("professional_notice")}

    @r.post("/professional-notice/accept")
    async def accept(body: AcceptIn, user=Depends(get_current_user)):
        if not body.acknowledged:
            raise HTTPException(status_code=400, detail="Please confirm the acknowledgment to continue")
        if body.version != PROFESSIONAL_NOTICE_VERSION:
            raise HTTPException(status_code=409, detail="The professional notice has been updated. Please review the current version.")
        rec = {"version": PROFESSIONAL_NOTICE_VERSION, "accepted_at": datetime.now(timezone.utc).isoformat()}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"professional_notice": rec}, "$push": {"professional_notice_history": rec}})
        return {"ok": True, **rec}

    @r.get("/admin/professional-notice/acceptances")
    async def acceptance_log(user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        rows = []
        async for u in db.users.find({"role": {"$in": list(PROFESSIONAL_NOTICE_ROLES)}}, {"name": 1, "email": 1, "role": 1, "professional_notice": 1, "professional_notice_history": 1}):
            acc = u.get("professional_notice") or {}
            rows.append({"id": str(u["_id"]), "name": u.get("name") or "", "email": u.get("email") or "", "role": u.get("role") or "",
                         "accepted_version": acc.get("version"), "accepted_at": acc.get("accepted_at"), "current": acc.get("version") == PROFESSIONAL_NOTICE_VERSION,
                         "history": [{"version": h.get("version"), "accepted_at": h.get("accepted_at")} for h in (u.get("professional_notice_history") or [])]})
        rows.sort(key=lambda x: (x["current"], x["accepted_at"] or ""), reverse=True)
        return {"current_version": PROFESSIONAL_NOTICE_VERSION, "total": len(rows), "accepted_current": sum(1 for x in rows if x["current"]), "rows": rows}

    @r.get("/admin/professional-notice/acceptances.csv")
    async def acceptance_log_csv(user=Depends(get_current_user)):
        import csv
        import io
        from fastapi import Response
        data = await acceptance_log(user)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["name", "email", "role", "accepted_version", "accepted_at", "current_version", "history"])
        for x in data["rows"]:
            w.writerow([x["name"], x["email"], x["role"], x["accepted_version"] or "", x["accepted_at"] or "", "yes" if x["current"] else "no",
                        "; ".join(f"{h['version']}@{h['accepted_at']}" for h in x["history"])])
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=professional-notice-acceptances.csv"})

    return r
