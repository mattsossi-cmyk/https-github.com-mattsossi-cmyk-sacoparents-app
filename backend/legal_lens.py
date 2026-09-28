"""Legal Lens Review and Report to Court — professional report builder (collection: professional_reports)."""
import uuid
from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from coparenting_tiers import joint_findings, suggested_score
from joint_data import SAFETY_SUBJECT_KEYS

from lens_data import (  # noqa: F401  (re-exported for callers importing from legal_lens)
    TAGLINE, STATUSES, SAFETY_NOTE, RATING_NOTE, JOINT_OPTIONS, RECEIPT, INDIVIDUAL_BANDS, JOINT_BANDS, INDIVIDUAL_BASE, JOINT_BASE, INDIVIDUAL_RESOURCES, JOINT_RESOURCES, SCALE_TABLE, RISK_CATEGORIES, RISK_LEVELS, SAFETY_ALERT, PATHWAYS, RESOURCE_CATEGORIES, REASSESS_INTERVALS, REASSESS_UP_DEFAULT, REASSESS_DOWN_DEFAULT, INTRO_TEXT, recommended_pathway, resource_lists, CONFLICT_OPTIONS, TEXT_FIELDS, LIST_FIELDS, DICT_FIELDS, INT_FIELDS, ROWS_FIELDS, RISK_FIELDS, GROWTH_FIELDS, CHILD_FIELDS, CONFLICT_GUIDANCE, CHILD_FOCUS_CATEGORIES, REPORT_PRINCIPLE, REPORT_PURPOSE, SAFETY_PATHWAY, REPORT_DISCLAIMER, growth_lines, AI_MODELS, classify_individual, classify_joint)


def _lines(text) -> list[str]:
    return [g.strip() for g in (text or "").split("\n") if g.strip()]


def _summary_ratings(rep: dict, a: dict | None, b: dict | None, j: dict | None) -> dict:
    return {"parent_a": {"score": rep.get("parent_a_rating"), "label": (a or {}).get("label")}, "parent_b": {"score": rep.get("parent_b_rating"), "label": (b or {}).get("label")},
            "joint": {"score": rep.get("joint_rating"), "label": (j or {}).get("label"), "mode": (j or {}).get("mode")}}


def _summary_safety(rep: dict) -> dict:
    risk = rep.get("risk_screening") or {}
    return {"risk_screening": [{"label": lbl, "level": risk.get(k, {}).get("level", "Not assessed"), "note": risk.get(k, {}).get("note", "")} for k, lbl, _ in RISK_CATEGORIES],
            "fv_received": {"a": rep.get("fv_a_received"), "b": rep.get("fv_b_received")}, "joint_process_appropriate": rep.get("joint_process_appropriate"), "safety_takeaway": rep.get("safety_takeaway")}


def _summary_scale(rep: dict, a: dict | None, b: dict | None, j: dict | None) -> dict:
    return {"growth": {"a": growth_lines(rep, "a"), "b": growth_lines(rep, "b")}, "parent_names": {"a": rep.get("parent_a_name"), "b": rep.get("parent_b_name")},
            "scale_table": SCALE_TABLE, "placement": {"a": (a or {}).get("row"), "b": (b or {}).get("row"), "joint": (j or {}).get("row")}}


def _summary_roadmap(rep: dict, j: dict | None) -> dict:
    chosen = rep.get("conflict_pathways") or [k for k in [rep.get("conflict_pathway") or ((j or {}).get("pathway") or {}).get("key")] if k]
    names = [p["name"] for p in PATHWAYS if p["key"] in chosen]
    return {"pathway": " · ".join(names) or None, "pathways": names, "pathway_rationale": rep.get("pathway_rationale") or rep.get("conflict_management_rationale"),
            "child_focus": [{"label": lbl, "note": (rep.get("child_focus") or {}).get(k, {}).get("note", "")} for k, lbl in CHILD_FOCUS_CATEGORIES if (rep.get("child_focus") or {}).get(k, {}).get("checked")],
            "shared_concerns": rep.get("shared_concerns"), "professional_summary": rep.get("professional_summary"), "court_summary": rep.get("court_summary_text"),
            "short_term_goals": _lines(rep.get("short_term_goals")), "long_term_goals": _lines(rep.get("long_term_goals")),
            "resources": rep.get("resource_rows") or [], "reassess_interval": rep.get("reassess_interval"), "next_review_date": rep.get("next_review_date"), "finalized_at": rep.get("finalized_at")}


def court_summary(rep: dict) -> dict:
    """Court-safe snapshot of the Professional Evaluation Report frozen with a submission (no parent-reported notes)."""
    a, b, j = classify_individual(rep.get("parent_a_rating")), classify_individual(rep.get("parent_b_rating")), classify_joint(rep.get("joint_rating"))
    return {"ratings": _summary_ratings(rep, a, b, j), **_summary_safety(rep), **_summary_scale(rep, a, b, j), **_summary_roadmap(rep, j)}


def default_resource_rows(providers: list[dict]) -> list[dict]:
    rows = [{"category": "Individual (Parent A)", "resource": "Individual Therapy / Counseling", "focus": "Processes separation stress, emotional regulation, and separating partner conflict from co-parenting goals."},
            {"category": "Individual (Parent B)", "resource": "Individual Coaching / Behavioral Therapy", "focus": "Focuses on time management, healthy communication boundaries, and administrative independence."},
            {"category": "Individual (Child)", "resource": "Child Therapy", "focus": "Provides a safe, neutral space to express feelings without getting caught in the middle."}]
    cat = {"Education": "Educational Assessment", "Children in the Middle": "Parent Education", "Options": "Clinical & Forensics"}
    for p in providers:
        c = next((v for k, v in cat.items() if k.lower() in p["specialty"].lower()), "Joint / Co-Parenting")
        rows.append({"category": c, "resource": p["label"], "focus": p["contact"]})
    return rows


def _answers(doc: dict, role: str) -> dict:
    return ((doc.get("responses") or {}).get(role) or {}).get("answers") or {}


def _pick(ans: dict, key: str) -> str:
    return " ".join(str(v).strip() for k, v in ans.items() if (k == key or k.endswith(f":{key}")) and str(v).strip())[:1500]


def readiness(doc: dict) -> list[dict]:
    a, b = bool(_answers(doc, "a")), bool(_answers(doc, "b"))
    safety = any(s in SAFETY_SUBJECT_KEYS for s in (doc.get("subjects") or [doc.get("subject")]))
    return [{"key": "assessment_a", "label": "Parent A Assessment Received", "done": a}, {"key": "assessment_b", "label": "Parent B Assessment Received", "done": b},
            {"key": "joint", "label": "Joint Report Received", "done": a and b},
            {"key": "fv_a", "label": "Parent A Family Violence Assessment Received", "done": safety and a, "na": not safety},
            {"key": "fv_b", "label": "Parent B Family Violence Assessment Received", "done": safety and b, "na": not safety}]


def _prefill_header(doc: dict, pro: dict, rd: dict) -> dict:
    parts, court, sug = doc.get("participants") or {}, doc.get("court") or {}, suggested_score(doc)
    fv = lambda k: "Not Applicable" if rd[k]["na"] else ("Received" if rd[k]["done"] else "Not Received")  # noqa: E731
    return {"matter_name": f"{doc.get('subject_label') or 'Co-parenting'} — {doc.get('child_name') or ''}".strip(" —"), "court_county": court.get("court_name", ""),
            "cause_number": court.get("cause_number", ""), "professional_role": pro.get("pro_role", ""), "report_date": datetime.now(timezone.utc).date().isoformat(),
            "parent_a_name": parts.get("a", {}).get("name") or "Parent A", "parent_b_name": parts.get("b", {}).get("name") or "Parent B", "fv_a_received": fv("fv_a"), "fv_b_received": fv("fv_b"),
            "joint_rating": sug["score"] if sug else None, "parent_a_rating": None, "parent_b_rating": None,
            "risk_screening": {k: {"level": "Not assessed", "note": ""} for k, _, _ in RISK_CATEGORIES}, "reassess_interval": "Every 90 to 180 days",
            "reassess_up": REASSESS_UP_DEFAULT, "reassess_down": REASSESS_DOWN_DEFAULT, "resource_rows": []}


def _prefill_joint(f: dict, doc: dict) -> dict:
    return {"joint_strengths": " ".join(f["alignment"]), "joint_gaps": " ".join(f["differences"]), "alignment_agreements": "\n".join(f["alignment"]), "alignment_disagreements": "\n".join(f["differences"]),
            "partial_alignment": "\n".join(f"{r['area']}: some common ground; may benefit from structured discussion." for r in f["alignment_map"] if r.get("status") == "Moderate alignment"),
            "child_focus": _child_focus_prefill(f.get("child_focused") or [], doc.get("subject") or "")}


def prefill(doc: dict, pro: dict) -> dict:
    """Pull everything already in the case so the professional never re-enters it."""
    out = _prefill_header(doc, pro, {r["key"]: r for r in readiness(doc)})
    for role in ("a", "b"):
        ans = _answers(doc, role)
        out[f"parent_{role}_strengths"], out[f"parent_{role}_gaps"] = _pick(ans, "working_well"), _pick(ans, "concerns")
    f = joint_findings(doc)
    return {**out, **_prefill_joint(f, doc)} if f else out


def _child_focus_prefill(child_items: list, subject: str) -> dict:
    """Tick child-focused categories suggested by the Joint Report's child-needs items and the case subject."""
    text = " ".join(str(x.get("text") if isinstance(x, dict) else x) for x in child_items).lower() + " " + subject.lower()
    hints = {"educational": ("school", "educat", "homework"), "medical": ("medical", "doctor", "health"), "psychological": ("emotion", "anxiety", "counsel", "psycholog"),
             "developmental": ("development", "milestone"), "routines": ("routine", "bedtime", "schedule"), "relationships": ("relationship", "bond", "time with"),
             "communication": ("communicat", "message", "text"), "transitions": ("transition", "handoff", "exchange", "pickup"), "special_needs": ("iep", "accommodat", "special need")}
    return {k: {"checked": any(h in text for h in hs), "note": ""} for k, hs in hints.items()}


class ReportIn(BaseModel):
    fields: dict
    status: str | None = None


class AiDraftIn(BaseModel):
    fields: dict = {}
    model: str = "gemini"


def _clean_text(v) -> str:
    return str(v or "")[:8000]


def _clean_list(v):
    return [str(x)[:200] for x in v][:30] if isinstance(v, list) else None


def _clean_dict(v):
    return {f: str(v.get(f, ""))[:300] for f in ("name", "specialty", "contact")} if isinstance(v, dict) else None


def _clean_int(v):
    return max(1, min(10, int(v))) if v not in (None, "", 0) else None


def _clean_rows(v):
    if not isinstance(v, list):
        return None
    return [{"category": str(r.get("category", ""))[:80], "resource": str(r.get("resource", ""))[:300], "focus": str(r.get("focus", ""))[:600]} for r in v if isinstance(r, dict)][:30]


def _clean_risk(v):
    if not isinstance(v, dict):
        return None
    keys = {k for k, _, _ in RISK_CATEGORIES}
    return {k: {"level": (d.get("level") if d.get("level") in RISK_LEVELS else "Not assessed"), "note": str(d.get("note", ""))[:600]} for k, d in v.items() if k in keys and isinstance(d, dict)}


def _clean_growth(v):
    if not isinstance(v, dict):
        return None
    return {role: {str(t)[:300]: bool(m) for t, m in d.items()} for role, d in v.items() if role in ("a", "b") and isinstance(d, dict)}


def _clean_child(v):
    if not isinstance(v, dict):
        return None
    keys = {k for k, _ in CHILD_FOCUS_CATEGORIES}
    return {k: {"checked": bool((d or {}).get("checked")), "note": str((d or {}).get("note") or "")[:1000]} for k, d in v.items() if k in keys and isinstance(d, dict)}


_CLEANERS = [(TEXT_FIELDS, _clean_text), (CHILD_FIELDS, _clean_child), (LIST_FIELDS, _clean_list), (DICT_FIELDS, _clean_dict), (INT_FIELDS, _clean_int), (ROWS_FIELDS, _clean_rows), (RISK_FIELDS, _clean_risk), (GROWTH_FIELDS, _clean_growth)]


def sanitize_fields(fields: dict) -> dict:
    upd = {}
    for k, v in fields.items():
        cleaner = next((fn for keys, fn in _CLEANERS if k in keys), None)
        if cleaner is None:
            continue
        cleaned = cleaner(v)
        if cleaned is not None or cleaner is _clean_int:
            upd[k] = cleaned
    return upd


def _assert_finalizable(rep: dict, upd: dict) -> None:
    if not (upd.get("signature_name") or rep.get("signature_name")):
        raise HTTPException(status_code=400, detail="Professional Signature Name is required to finalize")
    rationale = next((v for k in ("pathway_rationale", "conflict_management_rationale") for v in (upd.get(k), rep.get(k)) if v), "")
    if (upd.get("conflict_pathways") or rep.get("conflict_pathways")) and not rationale.strip():
        raise HTTPException(status_code=400, detail="Explain why the selected conflict-resolution pathways are relevant before finalizing")


def _ai_review(rep: dict, upd: dict) -> dict:
    merged = {**rep, **upd}
    return {k: {"model": d["model"], "drafted_at": d["at"], "edited": (merged.get(k) or "").strip() != d["text"].strip()} for k, d in (rep.get("ai_drafts") or {}).items()}


def apply_status(rep: dict, upd: dict, status: str) -> None:
    if status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if status in ("final", "submitted_to_court"):
        _assert_finalizable(rep, upd)
    upd["status"] = status
    if status == "final" and not rep.get("finalized_at"):
        upd["finalized_at"] = datetime.now(timezone.utc).isoformat()
        upd["ai_review"] = _ai_review(rep, upd)


def ai_disclosure_line(ai_review: dict) -> str:
    n_ed = sum(1 for x in ai_review.values() if x["edited"])
    return f"LEGAL_LENS_AI_DISCLOSURE: {len(ai_review)} AI-assisted section(s), {n_ed} edited by professional before certification"


def merge_drafts(rep: dict, fields: dict, label: str, source: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    model = label if source == "ai" else f"{label} (rule-based fallback)"
    return {**(rep.get("ai_drafts") or {}), **{k: {"text": v, "model": model, "at": now} for k, v in fields.items()}}


def case_summary(d: dict, status: str) -> dict:
    parts = d.get("participants") or {}
    return {"id": d["id"], "case_code": d.get("case_code"), "child_name": d.get("child_name"), "subject_label": d.get("subject_label"), "status": status,
            "parent_a": parts.get("a", {}).get("name"), "parent_b": parts.get("b", {}).get("name"), "readiness": readiness(d)}


def _reminder_html(rep: dict, case: dict, pro: dict, app_url, email_from_name: str) -> str:
    open_goals = sum(1 for r in ("a", "b") for g in growth_lines(rep, r) if not g["met"])
    return ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f"<p>Hi {escape(pro.get('name', ''))},</p><p>The next review date (<strong>{rep['next_review_date']}</strong>) for the Professional Evaluation Report in case "
            f"<strong>{escape(case.get('case_code') or '')}</strong> has arrived. {open_goals} Key Growth Area{'s are' if open_goals != 1 else ' is'} not yet marked as met.</p>"
            "<p>Re-check each parent's growth areas, update the 1–10 ratings, set the next review date, and submit a new version if the court should see the progress.</p>"
            f'<p><a href="{app_url()}/cases/{rep["case_id"]}/professional-report" style="background:#5B2A86;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block">Open the report</a></p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>')


async def _send_reminder(db, rep: dict, send_email, app_url, email_from_name, logger) -> bool:
    case = await db.joint_reports.find_one({"id": rep["case_id"]}, {"_id": 0, "case_code": 1, "child_name": 1, "professional_id": 1}) or {}
    pro = await db.users.find_one({"_id": rep.get("professional_id") or case.get("professional_id")}, {"name": 1, "email": 1}) or {}
    if not pro.get("email"):
        return False
    try:
        await send_email(to=pro["email"], case_id=rep["case_id"], kind="reassessment_reminder", to_role="Professional",
                         subject=f"Reassessment due - Case {case.get('case_code') or ''}", html=_reminder_html(rep, case, pro, app_url, email_from_name))
    except Exception as exc:
        logger.warning("reassessment reminder failed for %s: %s", rep["case_id"], exc)
        return False
    await db.professional_reports.update_one({"case_id": rep["case_id"]}, {"$set": {"reassess_reminder_for": rep["next_review_date"], "reassess_reminder_sent_at": datetime.now(timezone.utc).isoformat()}})
    return True


async def run_reassessment_reminders(db, send_email, app_url, email_from_name, logger, today=None) -> int:
    """Email the professional on a report's next_review_date so Key Growth Areas are re-checked; once per date."""
    today_s = (today or datetime.now(timezone.utc).date()).isoformat()
    reps = await db.professional_reports.find({"next_review_date": {"$gt": "", "$lte": today_s}, "status": {"$in": ["final", "submitted_to_court"]}}, {"_id": 0}).to_list(500)
    due = [rep for rep in reps if rep.get("reassess_reminder_for") != rep["next_review_date"]]
    return sum([await _send_reminder(db, rep, send_email, app_url, email_from_name, logger) for rep in due])


def _lens_case_query(rid: str, user: dict) -> dict:
    if user.get("role") not in ("professional", "admin") or (user.get("role") == "professional" and not user.get("approved")):
        raise HTTPException(status_code=403, detail="Approved professional access required.")
    return {"id": rid} if user.get("role") == "admin" else {"id": rid, "professional_id": user["_id"]}


async def professional_contact(db, uid: str | None, rep: dict | None = None) -> dict:
    """Cover-page contact block: profile values, overridden per report by cover_* fields; images are storage refs."""
    u = await db.users.find_one({"_id": uid}, {"name": 1, "email": 1, "profile": 1}) if uid else None
    rep = rep or {}
    p = (u or {}).get("profile") or {}
    line2 = ", ".join(x for x in (p.get("city"), p.get("state")) if x) + (f" {p['zip']}" if p.get("zip") else "")
    address = "\n".join(x for x in (p.get("organization"), p.get("address"), line2.strip()) if x)
    return {"name": rep.get("cover_name") or (u or {}).get("name", ""), "email": rep.get("cover_email") or (u or {}).get("email", ""), "phone": rep.get("cover_phone") or p.get("phone", ""),
            "address": rep.get("cover_address") or address, "images": {k: v.get("path") for k, v in (p.get("images") or {}).items() if v}}


async def _lens_view(db, rep: dict, doc: dict) -> dict:
    from providers import active_providers
    provs = await active_providers(db)
    ind, joint = resource_lists(provs)
    if not rep.get("resource_rows"):
        rep = {**rep, "resource_rows": default_resource_rows(provs)}
    rep = {**rep, "reassess_up": rep.get("reassess_up") or REASSESS_UP_DEFAULT, "reassess_down": rep.get("reassess_down") or REASSESS_DOWN_DEFAULT,
           "reassess_interval": rep.get("reassess_interval") or "Every 90 to 180 days"}
    return {"report": rep, "professional": await professional_contact(db, rep.get("professional_id"), rep), "readiness": readiness(doc), "classification": {"parent_a": classify_individual(rep.get("parent_a_rating")), "parent_b": classify_individual(rep.get("parent_b_rating")),
            "joint": classify_joint(rep.get("joint_rating"))}, "library": {"individual_resources": ind, "joint_resources": joint, "providers": provs, "conflict_options": CONFLICT_OPTIONS,
            "joint_process_options": JOINT_OPTIONS, "receipt_options": RECEIPT, "statuses": STATUSES, "ai_models": AI_MODELS, "scale_table": SCALE_TABLE, "risk_categories": RISK_CATEGORIES,
            "risk_levels": RISK_LEVELS, "pathways": PATHWAYS, "conflict_guidance": CONFLICT_GUIDANCE, "child_focus_categories": CHILD_FOCUS_CATEGORIES, "resource_categories": RESOURCE_CATEGORIES, "reassess_intervals": REASSESS_INTERVALS}, "notes": {"safety": SAFETY_NOTE, "rating": RATING_NOTE, "tagline": TAGLINE, "alert": SAFETY_ALERT, "intro": INTRO_TEXT, "principle": REPORT_PRINCIPLE, "purpose": REPORT_PURPOSE, "safety_pathway": SAFETY_PATHWAY, "disclaimer": REPORT_DISCLAIMER},
            "case": {"id": doc["id"], "case_code": doc.get("case_code"), "child_name": doc.get("child_name"), "subject_label": doc.get("subject_label")}}


def _new_report(doc: dict, pro: dict | None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {"id": str(uuid.uuid4()), "case_id": doc["id"], "professional_id": doc["professional_id"], "professional_name": (pro or {}).get("name", ""), "joint_report_id": doc["id"],
            "parent_a_assessment_id": f"{doc['id']}:a", "parent_b_assessment_id": f"{doc['id']}:b", "status": "draft", "created_at": now, "updated_at": now, "finalized_at": None,
            **{k: "" for k in TEXT_FIELDS}, **{k: [] for k in LIST_FIELDS}, **{k: {"name": "", "specialty": "", "contact": ""} for k in DICT_FIELDS}, **{k: None for k in INT_FIELDS},
            **prefill(doc, {**((pro or {}).get("profile") or {})})}


class LensStore:
    """Case access + Professional Evaluation Report persistence for the Legal Lens routes."""

    def __init__(self, db, log_event):
        self.db, self.log_event = db, log_event

    async def own_case(self, rid: str, user: dict) -> dict:
        doc = await self.db.joint_reports.find_one(_lens_case_query(rid, user), {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Case not found")
        return doc

    async def view(self, rep: dict, doc: dict) -> dict:
        return await _lens_view(self.db, rep, doc)

    async def get_or_create(self, doc: dict, user: dict) -> dict:
        rep = await self.db.professional_reports.find_one({"case_id": doc["id"]}, {"_id": 0})
        if rep:
            return rep
        rep = _new_report(doc, await self.db.users.find_one({"_id": doc["professional_id"]}, {"_id": 0, "name": 1, "profile": 1}))
        await self.db.professional_reports.insert_one({**rep})
        await self.log_event(doc["id"], "LEGAL_LENS_REPORT_CREATED", user)
        return rep


def build_router(db, get_current_user, log_event) -> APIRouter:
    r = APIRouter()
    s = LensStore(db, log_event)
    r.include_router(_report_routes(s, get_current_user))
    r.include_router(_export_routes(s, get_current_user))
    return r


def _report_routes(s: LensStore, get_current_user) -> APIRouter:
    r, db, log_event = APIRouter(), s.db, s.log_event

    @r.get("/cases/{rid}/professional-report")
    async def get_report(rid: str, user=Depends(get_current_user)):
        doc = await s.own_case(rid, user)
        return await s.view(await s.get_or_create(doc, user), doc)

    @r.get("/cases/{rid}/professional-report/walkthrough")
    async def walkthrough(rid: str, user=Depends(get_current_user)):
        from lens_walkthrough import WALKTHROUGH
        await s.own_case(rid, user)
        return [{"n": i, "title": t, "what": w, "how": h, "guardrail": g} for i, (t, w, h, g) in enumerate(WALKTHROUGH, 1)]

    @r.get("/cases/{rid}/professional-report/readiness")
    async def get_readiness(rid: str, user=Depends(get_current_user)):
        doc = await s.own_case(rid, user)
        rep = await db.professional_reports.find_one({"case_id": rid}, {"_id": 0, "status": 1})
        return {"readiness": readiness(doc), "status": (rep or {}).get("status")}

    @r.put("/cases/{rid}/professional-report")
    async def save_report(rid: str, body: ReportIn, user=Depends(get_current_user)):
        doc = await s.own_case(rid, user)
        rep = await s.get_or_create(doc, user)
        upd = sanitize_fields(body.fields)
        if body.status:
            apply_status(rep, upd, body.status)
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.professional_reports.update_one({"case_id": rid}, {"$set": upd})
        await log_event(rid, "LEGAL_LENS_REPORT_FINALIZED" if body.status == "final" else "LEGAL_LENS_REPORT_SAVED", user)
        if upd.get("ai_review"):
            await log_event(rid, ai_disclosure_line(upd["ai_review"]), user)
        return await s.view({**rep, **upd}, doc)

    return r


def _export_routes(s: LensStore, get_current_user) -> APIRouter:
    r, db, log_event = APIRouter(), s.db, s.log_event

    @r.post("/cases/{rid}/professional-report/ai-draft")
    async def ai_draft(rid: str, body: AiDraftIn, user=Depends(get_current_user)):
        from legal_ai import draft_lens_report
        doc = await s.own_case(rid, user)
        rep = {**(await s.get_or_create(doc, user)), **sanitize_fields({k: v for k, v in body.fields.items() if k not in DICT_FIELDS})}
        cls = (await s.view(rep, doc))["classification"]
        fields, source, label = await draft_lens_report(rep, cls, rid, body.model)
        drafts = merge_drafts(rep, fields, label, source)
        upd = {"ai_drafts": drafts}
        from research import research_insight
        rb = await research_insight(rep, user)
        if rb:
            upd["research_base"] = rb
        await db.professional_reports.update_one({"case_id": rid}, {"$set": upd})
        await log_event(rid, f"LEGAL_LENS_AI_DRAFT ({label}, {len(fields)} sections{', research base refreshed' if rb else ''})", user)
        return {"fields": fields, "source": source, "model": label, "label": "AI-Assisted Draft — Professional Review Required", "ai_drafts": drafts, "research_base": rb}

    @r.post("/cases/{rid}/professional-report/research-insight")
    async def research_refresh(rid: str, user=Depends(get_current_user)):
        from research import research_insight
        doc = await s.own_case(rid, user)
        rep = await s.get_or_create(doc, user)
        rb = await research_insight(rep, user)
        if rb is None:
            raise HTTPException(status_code=503, detail="Research Base unavailable — Perplexity is not configured or unreachable. The report is unaffected.")
        await db.professional_reports.update_one({"case_id": rid}, {"$set": {"research_base": rb}})
        await log_event(rid, "LEGAL_LENS_RESEARCH_BASE_REFRESHED", user)
        return {"research_base": rb}

    @r.delete("/cases/{rid}/professional-report/research-insight")
    async def research_clear(rid: str, user=Depends(get_current_user)):
        await s.own_case(rid, user)
        await db.professional_reports.update_one({"case_id": rid}, {"$unset": {"research_base": ""}})
        return {"ok": True}

    @r.get("/cases/{rid}/professional-report/pdf")
    async def report_pdf(rid: str, user=Depends(get_current_user)):
        from pdf_lens import build_legal_lens_pdf
        doc = await s.own_case(rid, user)
        rep = await s.get_or_create(doc, user)
        await log_event(rid, "LEGAL_LENS_REPORT_EXPORTED", user)
        return Response(content=build_legal_lens_pdf(await s.view(rep, doc)), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="legal-lens-report-{doc.get("case_code") or rid}.pdf"'})

    @r.get("/professional-report/cases")
    async def my_cases(user=Depends(get_current_user)):
        if user.get("role") != "professional" or not user.get("approved"):
            raise HTTPException(status_code=403, detail="Approved professional access required.")
        docs = await db.joint_reports.find({"professional_id": user["_id"], "kind": {"$ne": "agreement"}}, {"_id": 0, "id": 1, "case_code": 1, "child_name": 1, "subject_label": 1, "participants": 1, "responses": 1, "subjects": 1, "subject": 1, "created_at": 1}).sort("created_at", -1).to_list(200)
        reps = {x["case_id"]: x["status"] for x in await db.professional_reports.find({"professional_id": user["_id"]}, {"_id": 0, "case_id": 1, "status": 1}).to_list(500)}
        return [case_summary(d, reps.get(d["id"], "not_started")) for d in docs]

    return r
