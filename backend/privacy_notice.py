"""Privacy Notification — shown on first sign-in and whenever PRIVACY_NOTICE_VERSION changes. Acceptance stored per user with timestamp + version."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

PRIVACY_NOTICE_VERSION = "2026-10-19.1"  # bumped: no-tier wording, Claude drafting disclosure, "professionals assigned to your case" (owner 2026-10-19)
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
        {"heading": "Your individual answers remain private.", "body": "Your co-parent does not automatically see your assessments, personal reflections, or journal entries."},
        {"heading": "You control what you share.", "body": "In the Self Journey, you choose which completed reports to share and with whom. Separate consent rules apply to joint and court-ordered participation."},
        {"heading": "Reports are different from raw answers.", "body": "Sharing a selected report does not automatically provide access to your entire account or private journal."},
        {"heading": "Safety comes first.", "body": "Family violence and communication safety concerns may require separate participation and additional safeguards."},
        {"heading": "Professionals and courts receive the information you authorize, or what the law or a court order requires.", "body": "Assigned professionals may see individual screening answers."},
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
