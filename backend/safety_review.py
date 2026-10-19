"""Phase 4: professional-only safety review — two-column status, pattern panel, concern level with reasons, provisions library, provisions PDF with export scan + footer."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from core import db
from fv_screening import ITEMS, LEGACY_ITEMS, RULE_LABEL, TF
from pdf_common import _new_pdf, _s
from pro_training import is_supervisor, require_training

LEVELS = ("none", "green", "amber", "red")
LEVEL_LABEL = {"none": "Not yet decided", "green": "No concerns reported", "amber": "Amber — structured review", "red": "Red — protected review"}
REASONS = [
    "Pattern of concern across more than one domain", "Recent events within the last 12 months", "Children exposed or involved",
    "Parent reported not feeling safe at home", "Monitoring or control of communication reported", "Weapons or threats mentioned",
    "Protective order or criminal matter in place", "Professional judgment — context from session", "No concerns reported by either parent",
]
PROVISIONS = [
    {"id": "ex1", "group": "Exchange", "text": "Exchanges of the children shall occur at a neutral public location agreed in writing, or at a supervised exchange center if available."},
    {"id": "ex2", "group": "Exchange", "text": "Exchanges shall be curbside only; the receiving parent remains in the vehicle and the delivering parent brings the children to the vehicle."},
    {"id": "ex3", "group": "Exchange", "text": "A third party designated in writing may conduct exchanges on behalf of either parent."},
    {"id": "cm1", "group": "Communication", "text": "All parent-to-parent communication shall occur through a court-approved co-parenting application and shall be limited to the children's needs."},
    {"id": "cm2", "group": "Communication", "text": "Neither parent shall use the children to relay messages to the other parent."},
    {"id": "cm3", "group": "Communication", "text": "Emergency contact by telephone is permitted only for a medical or safety emergency involving a child."},
    {"id": "ct1", "group": "Contact", "text": "Neither parent shall come within 100 yards of the other parent's residence or workplace except as required for scheduled exchanges."},
    {"id": "ct2", "group": "Contact", "text": "Each parent shall provide the other with a working emergency contact that does not disclose their residential address."},
    {"id": "sv1", "group": "Supervision", "text": "Parenting time shall be supervised by a provider agreed in writing or appointed by the court until further order."},
    {"id": "sv2", "group": "Supervision", "text": "Supervised parenting time may step down to unsupervised time only on review by the court or by written agreement filed with the court."},
    {"id": "fa1", "group": "Firearms", "text": "Firearms shall be stored unloaded and locked, with ammunition stored separately, at any residence where the children spend time."},
    {"id": "fa2", "group": "Firearms", "text": "Where a protective order so requires, the restrained party shall comply with all firearm surrender terms of that order."},
    {"id": "nc1", "group": "No-contact", "text": "This parenting plan does not modify any protective order. Where terms conflict, the protective order controls."},
    {"id": "nc2", "group": "No-contact", "text": "Neither parent shall track, monitor or access the other parent's devices, accounts or location."},
]
PROVISIONS_FOOTER = "These provisions are the professional's recommendations prepared for the parties and their counsel. They are not an order; only the court decides. This document contains no screening answers."
_PART_OF = {it["id"]: it["part"] for it in ITEMS + LEGACY_ITEMS}
RULE_DOMAIN = {"danger_now": "danger", "not_safe_home": "safe_home", "pv_worse": "pv", "pv_medical": "pv", "strangulation": "strangle", "threat_kill": "threat_kill",
               "weapon_used": "weapon_used", "stalking": "stalk", "sexual": "sexual", "kids_hurt": "kids_hurt", "amber_cluster": "separated", "amber_recent": "pv",
               "weapon_access": "weapon_access", "afraid": "afraid", "red_skipped": "danger", "kids_worry": "kids_worry", "substance": "substance"}


def pattern_panel(triggered: list[str]) -> list[dict]:
    """Group triggered rules by questionnaire domain — rule labels only, never the answers."""
    out: dict[str, list[str]] = {}
    for rid in triggered or []:
        key = rid if rid in RULE_LABEL else next((k for k, v in RULE_LABEL.items() if v == rid), rid)
        dom = _PART_OF.get(RULE_DOMAIN.get(key, ""), "Other")
        out.setdefault(dom, []).append(RULE_LABEL.get(key, key))
    return [{"domain": k, "signals": v} for k, v in out.items()]


def _forbidden_terms() -> list[str]:
    terms = [it["text"] for it in ITEMS + LEGACY_ITEMS if it.get("text")]
    terms += [o for o in TF if o.lower() not in ("never", "prefer not to answer")]
    terms += ["Red — protected", "Amber — structured", "triggered_rules", "Tier 1 —", "Tier 2 —", "Tier 3 —", "Tier not available"] + [v for v in RULE_LABEL.values() if len(v) > 12]
    return terms


def scan_text(text: str) -> list[str]:
    """Returns the forbidden screening terms present in export text (export must be blocked when non-empty)."""
    norm = re.sub(r"\s+", " ", text or "").lower()
    return [t for t in _forbidden_terms() if len(t) > 6 and re.sub(r"\s+", " ", t).lower() in norm]


def assert_export_clean(pdf: bytes, label: str = "export") -> bytes:
    """Every outbound PDF passes through here: blocks the download (409) if screening wording is present."""
    leaks = scan_pdf(pdf)
    if leaks:
        raise HTTPException(status_code=409, detail=f"{label} blocked by the export scan: the document contains private check-in wording. Remove it and try again.")
    return pdf


def scan_pdf(pdf: bytes) -> list[str]:
    import pymupdf
    with pymupdf.open(stream=pdf, filetype="pdf") as d:
        return scan_text("\n".join(p.get_text() for p in d))


def build_provisions_pdf(doc: dict, review: dict, pro: dict) -> bytes:
    pdf = _new_pdf()
    pdf.add_page()
    pdf.set_font(pdf.font_family or "helvetica", "B", 16)
    pdf.cell(0, 10, _s("Recommended Parenting-Plan Safety Provisions"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.font_family, "", 10)
    pdf.cell(0, 6, _s(f"Case {doc.get('case_code') or doc['id'][:8]} · Prepared by {pro.get('name', '')} · {datetime.now(timezone.utc).date().isoformat()}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    chosen = {p["id"]: p for p in PROVISIONS}
    by_group: dict[str, list[str]] = {}
    for pid in review.get("provisions") or []:
        if pid in chosen:
            by_group.setdefault(chosen[pid]["group"], []).append(chosen[pid]["text"])
    for text in review.get("custom_provisions") or []:
        by_group.setdefault("Additional", []).append(text)
    if not by_group:
        pdf.multi_cell(0, 6, _s("No provisions selected."))
    for group, texts in by_group.items():
        pdf.set_font(pdf.font_family, "B", 12)
        pdf.cell(0, 8, _s(group), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(pdf.font_family, "", 10.5)
        for i, t in enumerate(texts, 1):
            pdf.multi_cell(0, 6, _s(f"{i}. {t}"))
            pdf.ln(1)
        pdf.ln(2)
    pdf.ln(4)
    pdf.set_font(pdf.font_family, "I", 9)
    pdf.multi_cell(0, 5, _s(PROVISIONS_FOOTER))
    return bytes(pdf.output())


class SignoffIn(BaseModel):
    approve: bool
    note: str = ""


class ReviewIn(BaseModel):
    concern_level: str = "none"
    reasons: list[str] = Field(default_factory=list)
    provisions: list[str] = Field(default_factory=list)
    custom_provisions: list[str] = Field(default_factory=list)
    notes: str = ""


def _column(doc: dict, role: str, status: dict) -> dict:
    s = status.get(role) or {}
    scr = (doc.get("safety_screenings") or {}).get(role) or {}
    return {"role": role, "label": f"Parent {role.upper()}", "entry_status": s.get("entry_status"), "entry_label": s.get("entry_label"), "received": bool(s.get("received")),
            "app_tier": s.get("app_tier"), "app_tier_label": s.get("app_tier_label"), "completed_at": s.get("completed_at"),
            "pattern": pattern_panel(scr.get("triggered_rules") or []), "pathway": (doc.get("safety_pathway") or {}).get(role)}


def build_router(get_current_user, get_joint_report_doc, log_access, is_pro, status_fn) -> APIRouter:
    r = APIRouter()

    @r.get("/safety-provisions")
    async def provisions(user=Depends(get_current_user)):
        if user.get("role") not in ("professional", "admin"):
            raise HTTPException(status_code=403, detail="Professionals only")
        return {"provisions": PROVISIONS, "footer": PROVISIONS_FOOTER, "reasons": REASONS, "levels": [{"id": k, "label": LEVEL_LABEL[k]} for k in LEVELS]}

    @r.get("/joint/reports/{rid}/safety-review")
    async def get_review(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user) and not (doc.get("safety_review_pending_lower") and await is_supervisor(db, user)):
            raise HTTPException(status_code=403, detail="Only the assigned professional can open the safety review")
        await require_training(db, user)
        status = status_fn(doc)
        await log_access(doc, user, "Opened safety review (two-column)", "safety_review")
        rev = doc.get("safety_review") or {"concern_level": "none", "reasons": [], "provisions": [], "custom_provisions": [], "notes": ""}
        pend = doc.get("safety_review_pending_lower")
        return {"columns": [_column(doc, "a", status), _column(doc, "b", status)], "review": {**rev, "level_label": LEVEL_LABEL.get(rev.get("concern_level") or "none")},
                "pending_lower": pend, "can_sign_off": bool(pend) and await is_supervisor(db, user) and pend.get("requested_by") != user["_id"],
                "reasons": REASONS, "levels": [{"id": k, "label": LEVEL_LABEL[k]} for k in LEVELS], "provisions": PROVISIONS, "footer": PROVISIONS_FOOTER,
                "notice": "Professional-only. Access is logged. Nothing here is shown to either parent or to the court; only the provisions document can be exported, and it is scanned before download."}

    @r.put("/joint/reports/{rid}/safety-review")
    async def put_review(rid: str, body: ReviewIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can record the safety review")
        if body.concern_level not in LEVELS:
            raise HTTPException(status_code=400, detail="Unknown concern level")
        if body.concern_level in ("amber", "red") and not body.reasons:
            raise HTTPException(status_code=400, detail="Give at least one reason for an Amber or Red concern level")
        await require_training(db, user)
        valid = {p["id"] for p in PROVISIONS}
        rev = {"concern_level": body.concern_level, "reasons": [x for x in body.reasons if x in REASONS][:9], "provisions": [p for p in body.provisions if p in valid],
               "custom_provisions": [c.strip()[:600] for c in body.custom_provisions if c.strip()][:10], "notes": body.notes.strip()[:4000],
               "decided_by": user["_id"], "decided_by_name": user.get("name", ""), "at": datetime.now(timezone.utc).isoformat()}
        current = (doc.get("safety_review") or {}).get("concern_level")
        if current == "red" and body.concern_level != "red":
            if not body.reasons:
                raise HTTPException(status_code=400, detail="Give at least one reason to lower a Red concern level")
            pend = {**rev, "requested_by": user["_id"], "requested_by_name": user.get("name", ""), "requested_at": rev["at"], "from_level": "red"}
            await db.joint_reports.update_one({"id": rid}, {"$set": {"safety_review_pending_lower": pend}})
            await log_access(doc, user, f"Requested lowering concern level Red → {LEVEL_LABEL[body.concern_level]} (awaiting supervising professional)", "supervisor_signoff")
            return {**(doc.get("safety_review") or {}), "level_label": LEVEL_LABEL["red"], "pending_lower": pend, "requires_supervisor": True}
        await db.joint_reports.update_one({"id": rid}, {"$set": {"safety_review": rev}, "$unset": {"safety_review_pending_lower": ""}})
        await log_access(doc, user, f"Safety review saved: concern level {LEVEL_LABEL[body.concern_level]} ({len(rev['reasons'])} reasons, {len(rev['provisions']) + len(rev['custom_provisions'])} provisions)", "safety_review")
        return {**rev, "level_label": LEVEL_LABEL[body.concern_level]}

    @r.post("/joint/reports/{rid}/safety-review/supervisor-signoff")
    async def supervisor_signoff(rid: str, body: SignoffIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        pend = doc.get("safety_review_pending_lower")
        if not pend:
            raise HTTPException(status_code=404, detail="No lowering request is awaiting sign-off")
        if not await is_supervisor(db, user):
            raise HTTPException(status_code=403, detail="Only a supervising professional can sign off lowering a Red concern level")
        if pend.get("requested_by") == user["_id"]:
            raise HTTPException(status_code=403, detail="A second professional must sign off; you made the request")
        await require_training(db, user)
        if not body.note.strip():
            raise HTTPException(status_code=400, detail="Record a short reason for your decision")
        now = datetime.now(timezone.utc).isoformat()
        sign = {"by": user["_id"], "by_name": user.get("name", ""), "at": now, "approved": body.approve, "note": body.note.strip()[:1000]}
        if body.approve:
            rev = {k: v for k, v in pend.items() if k not in ("requested_by", "requested_by_name", "requested_at", "from_level")}
            rev["supervisor_signoff"] = sign
            await db.joint_reports.update_one({"id": rid}, {"$set": {"safety_review": rev}, "$unset": {"safety_review_pending_lower": ""}})
        else:
            await db.joint_reports.update_one({"id": rid}, {"$unset": {"safety_review_pending_lower": ""}, "$set": {"safety_review.last_signoff": sign}})
        await log_access(doc, user, f"Supervising professional {'approved' if body.approve else 'declined'} lowering Red → {LEVEL_LABEL.get(pend.get('concern_level'), '?')}", "supervisor_signoff")
        return {"ok": True, "approved": body.approve, "concern_level": pend["concern_level"] if body.approve else "red"}

    @r.get("/joint/reports/{rid}/safety-review/provisions.pdf")
    async def provisions_pdf(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can export provisions")
        await require_training(db, user)
        rev = doc.get("safety_review") or {}
        pdf = build_provisions_pdf(doc, rev, user)
        leaks = scan_pdf(pdf)
        if leaks:
            await log_access(doc, user, "Provisions export BLOCKED by export scan", "export_scan_block")
            raise HTTPException(status_code=409, detail="Export blocked: the document contains screening wording. Edit the custom provisions and try again.")
        await log_access(doc, user, "Exported provisions PDF (export scan passed)", "safety_review_export")
        return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="provisions-{(doc.get("case_code") or rid[:8])}.pdf"'})

    return r
