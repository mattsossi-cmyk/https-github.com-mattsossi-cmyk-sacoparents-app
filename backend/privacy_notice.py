"""Privacy Notification — shown on first sign-in and whenever PRIVACY_NOTICE_VERSION changes. Acceptance stored per user with timestamp + version."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

PRIVACY_NOTICE_VERSION = "2026-10-19.2"  # bumped: points rewritten for Align (Foundation Statement, joint comparison, stop sharing, who looked); no readiness sentence (owner 2026-10-20)
SUBHEAD = "Private by default. Shared with your consent, or as the law requires."
# Reusable legal-notice sentences (also for the future privacy policy). Edit here only.
LEGAL_NOTICE_SENTENCES = [
    "Using SA CoParents does not automatically create an attorney-client, therapist-patient, or other legally privileged relationship.",
    "Information may be subject to lawful disclosure requirements.",
    "SA CoParents is a separate tool from the law practice of Matt Sossi.",
    "Access to or use of this app does not create an attorney-client relationship.",
]
LEGAL_NOTICE = " ".join(LEGAL_NOTICE_SENTENCES)
NOTICE = {
    "version": PRIVACY_NOTICE_VERSION,
    "banner_heading": "Privacy & Confidentiality",
    "tagline": "Start with Safety. Build with Trust.",
    "title": "Your Privacy Matters",
    "subhead": SUBHEAD,
    "intro": "Your preparation is private and under your control.",
    "points": [
        {"heading": "Your individual answers remain private.", "body": "Your co-parent never sees your assessment answers or your safety check-in. Your Foundation Statement stays private unless you choose to share it; once shared, it appears in the joint report that both parents and the professional can read."},
        {"heading": "You control what you share.", "body": "Once both parents have submitted their answers, the joint report shows the generated comparison to both parents and to the professional on the case, never anyone's raw answers. Beyond that, you choose which professionals to share a report with, and you can stop sharing with a professional you added yourself. Separate rules apply to court-ordered participation."},
        {"heading": "Reports are different from raw answers.", "body": "Sharing a report gives that professional access to the report only, not to your whole account or your individual answers."},
        {"heading": "Safety comes first.", "body": "Your Family check-in answers are seen only by the professionals assigned to your case and, when needed, SA CoParents administrators, on a protected screen. Every view is recorded, and you can see who looked and when. Court documents and reports show only whether the check-in was received, not started, or declined."},
        {"heading": "Professionals and courts receive the information you authorize, or what the law or a court order requires.", "body": "Reports are built from what you authorize. A report a professional submits to a court is frozen and cannot be changed afterward."},
    ],
    "legal_heading": "Important Legal Notice",
    "legal": LEGAL_NOTICE,
    "checkbox": "I have read and understand this privacy notification.",
    "continue": "Continue to SA CoParents",
    # PLACEHOLDER: footer links to /privacy, /confidentiality, /sharing-consent stay OFF until the owner confirms those draft pages are final.
    "footer_links": [],
}


def needs_acceptance(user: dict) -> bool:
    acc = user.get("privacy_notice") or {}
    return acc.get("version") != PRIVACY_NOTICE_VERSION


class AcceptIn(BaseModel):
    version: str
    acknowledged: bool


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/privacy-notice")
    async def get_notice(user=Depends(get_current_user)):
        full = await db.users.find_one({"_id": user["_id"]}, {"privacy_notice": 1, "role": 1})
        return {"notice": {**NOTICE, "access_notice": __import__("safety_screening").PROFESSIONAL_ACCESS_NOTICE if (full or {}).get("role") == "parent" else None}, "needs_acceptance": needs_acceptance(full or {}), "accepted": (full or {}).get("privacy_notice")}

    @r.post("/privacy-notice/accept")
    async def accept(body: AcceptIn, user=Depends(get_current_user)):
        if not body.acknowledged:
            raise HTTPException(status_code=400, detail="Please confirm you have read the privacy notification")
        if body.version != PRIVACY_NOTICE_VERSION:
            raise HTTPException(status_code=409, detail="The privacy notification has been updated. Please review the current version.")
        rec = {"version": PRIVACY_NOTICE_VERSION, "accepted_at": datetime.now(timezone.utc).isoformat()}
        upd = {"$set": {"privacy_notice": rec}, "$push": {"privacy_notice_history": rec}}
        if user.get("role") == "parent":  # combined consent (owner 2026-10-19): the "Who can see your information" notice is shown on this page and accepted together
            from safety_screening import STEP_NOTICE_VERSION
            upd["$set"]["safety_step_notice"] = {"version": STEP_NOTICE_VERSION, "seen_at": rec["accepted_at"]}
        await db.users.update_one({"_id": user["_id"]}, upd)
        return {"ok": True, **rec}

    def _admin(user):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")

    async def _log_rows():
        cur = db.users.find({}, {"name": 1, "email": 1, "role": 1, "privacy_notice": 1, "privacy_notice_history": 1})
        rows = []
        async for u in cur:
            acc = u.get("privacy_notice") or {}
            rows.append({
                "id": str(u["_id"]), "name": u.get("name") or "", "email": u.get("email") or "", "role": u.get("role") or "",
                "accepted_version": acc.get("version"), "accepted_at": acc.get("accepted_at"),
                "current": acc.get("version") == PRIVACY_NOTICE_VERSION,
                "history": [{"version": h.get("version"), "accepted_at": h.get("accepted_at")} for h in (u.get("privacy_notice_history") or [])],
            })
        rows.sort(key=lambda x: (x["current"], x["accepted_at"] or ""), reverse=True)
        return rows

    @r.get("/admin/privacy-notice/acceptances")
    async def acceptance_log(user=Depends(get_current_user)):
        _admin(user)
        rows = await _log_rows()
        return {"current_version": PRIVACY_NOTICE_VERSION, "total": len(rows), "accepted_current": sum(1 for x in rows if x["current"]), "rows": rows}

    @r.get("/admin/privacy-notice/acceptances.csv")
    async def acceptance_log_csv(user=Depends(get_current_user)):
        _admin(user)
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["name", "email", "role", "accepted_version", "accepted_at", "current_version", "history"])
        for x in await _log_rows():
            w.writerow([x["name"], x["email"], x["role"], x["accepted_version"] or "", x["accepted_at"] or "", "yes" if x["current"] else "no",
                        "; ".join(f"{h['version']}@{h['accepted_at']}" for h in x["history"])])
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=privacy-notice-acceptances.csv"})

    # Retention admin preview route intentionally removed — Retention Engine is switched OFF (RETENTION_ENGINE_ENABLED=false).
    return r
