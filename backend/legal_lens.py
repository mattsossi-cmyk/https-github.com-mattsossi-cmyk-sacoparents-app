"""Legal Lens Review and Report to Court — professional report builder (collection: professional_reports)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from coparenting_tiers import joint_findings, suggested_score
from joint_data import SAFETY_SUBJECT_KEYS

TAGLINE = "SA CoParents — Starting With Alignment, Ending With Agreement"
STATUSES = ("draft", "under_review", "final", "submitted_to_court")
SAFETY_NOTE = "Safety findings may alter or override ordinary co-parenting, mediation, communication, or joint-process recommendations."
RATING_NOTE = "The rating does not automatically determine the process. Safety screening, professional judgment, court orders, and the specific needs of the child remain controlling considerations."
JOINT_OPTIONS = ("Yes", "Yes, with safeguards", "No / Not recommended at this time")
RECEIPT = ("Received", "Not Received", "Not Applicable")

INDIVIDUAL_BANDS = [
    (1, 2, "Crisis / High Conflict", ["follows some formal orders", "maintains separation when required", "participates in structured exchanges"],
     ["highly reactive communication", "poor boundaries", "repeated conflict", "child exposure to conflict", "heavy court involvement"]),
    (3, 4, "Restricted / Reactive", ["follows basic parenting schedule", "provides required child information", "participates in important child activities"],
     ["defensive communication", "delayed information sharing", "difficulty separating relationship conflict from parenting issues"]),
    (5, 6, "Business-Like / Functional", ["child-focused communication", "respects separate household boundaries", "handles routine requests appropriately"],
     ["difficulty with unexpected changes", "flexibility concerns", "occasional emotionally reactive communication"]),
    (7, 8, "Cooperative / Collaborative", ["consults on major decisions", "shares information proactively", "supports reasonable flexibility"],
     ["occasional disputes over parenting styles", "differences in household expectations"]),
    (9, 10, "Child-Centered Partnership", ["constructive communication", "supports child's relationship with other parent", "resolves disputes without involving the child"],
     ["few meaningful co-parenting difficulties"]),
]
JOINT_BANDS = [
    (1, 2, "Crisis / High Conflict", "Supervised / Strict Parallel", ["compliance with formal court orders", "structured exchanges", "maintaining physical separation"],
     ["communication collapse", "hostile exchanges", "repeated litigation", "serious safety concerns"],
     ["further court involvement", "formal orders", "highly structured communication", "supervised or structured exchanges", "separate professional support"]),
    (3, 4, "Restricted / Reactive", "Restricted Parallel Parenting", ["honoring scheduled transitions", "sharing required school and medical information", "attending child-related events"],
     ["handoff conflict", "reactive messages", "lateness", "gatekeeping minor information"],
     ["parent facilitation", "parallel-parenting structure", "BIFF", "Children in the Middle", "structured app communication", "carefully structured mediation when appropriate"]),
    (5, 6, "Business-Like / Functional", "Emerging Cooperative", ["task-focused written messages", "schedule accommodation with advance notice", "respect for separate households"],
     ["difficulty with sudden changes", "financial friction", "passive-aggressive communication"], ["traditional mediation", "child-centered mediation", "co-parenting agreement", "structured problem-solving"]),
    (7, 8, "Cooperative / Collaborative", "High Co-Parenting", ["consultation on major decisions", "flexible schedule changes", "support of extracurricular activities"],
     ["occasional parenting-style differences"], ["child-centered mediation", "collaborative problem-solving", "flexible parenting-plan modifications"]),
    (9, 10, "Child-Centered Partnership", "Unified Partnership", ["fluid communication", "active support for child's relationship with both parents", "shared problem-solving"],
     ["few meaningful co-parenting difficulties"], ["direct collaboration", "shared planning", "mediation only when needed for significant disputes"]),
]
INDIVIDUAL_BASE = ["Foundation Statement", "BIFF Communication Method", "SA CoParents AI Conversation Builder", "Individual Counseling / Coaching"]
JOINT_BASE = ["Co-Parenting Agreement", "Parent Facilitation / Coordination", "Traditional Mediation", "Child-Centered Mediation"]
INDIVIDUAL_RESOURCES = [*INDIVIDUAL_BASE, "Kelly Bernstein — Child-Focused Options Provider", "Kassandra Levay — Education Specialist", "Additional Counselor / Provider"]
JOINT_RESOURCES = ["Brad Craig — Children in the Middle", "Kelly Bernstein — Child-Focused Options Provider", "Kassandra Levay — Education Specialist", *JOINT_BASE, "Additional Expert / Provider"]

# Section 3 — Comprehensive 1–10 Co-Parenting Scale (joint & individual behaviors), verbatim from the Professional Evaluation Report form.
SCALE_TABLE = [
    {"lo": 1, "hi": 2, "label": "Crisis / High Conflict", "mode": "Supervised / Strict Parallel",
     "well": {"joint": "Adhere to legal orders; use 3rd-party sites.", "a": "Follows court boundaries.", "b": "Complies with supervised visits."},
     "poor": {"joint": "Communication collapse; hostile outbursts.", "a": "Repeated legal motions under stress.", "b": "Hostility or total refusal at handoffs."}},
    {"lo": 3, "hi": 4, "label": "Restricted / Reactive", "mode": "Restricted Parallel",
     "well": {"joint": "Honor scheduled times; share portal logs.", "a": "Keeps portal updated.", "b": "Engaged in sports/school events."},
     "poor": {"joint": "Verbal friction; reactive texts; late handoffs.", "a": "Defensive messaging; holds back info.", "b": "15-20 min late; redundant texts."}},
    {"lo": 5, "hi": 6, "label": "Business-Like / Functional", "mode": "Emerging Cooperative",
     "well": {"joint": "Task-focused messages; advance swaps (48h+).", "a": "Concise portal updates.", "b": "On time; checks portals independently."},
     "poor": {"joint": "Struggle with sudden schedule shifts.", "a": "Passive resistance to last-minute shifts.", "b": "Minor administrative lapses."}},
    {"lo": 7, "hi": 8, "label": "Cooperative / Collaborative", "mode": "High Co-Parenting",
     "well": {"joint": "Consult on health/school; informal swaps.", "a": "Proactive medical consultation.", "b": "Shares transport duties."},
     "poor": {"joint": "Clash over secondary house rules.", "a": "Pushes for single-rule priority.", "b": "Clashes over discipline styles."}},
    {"lo": 9, "hi": 10, "label": "Child-Centered Partnership", "mode": "Unified Partnership",
     "well": {"joint": "Matching rules; joint events; fluid updates.", "a": "Promotes bond with Parent B.", "b": "Complete rule alignment."},
     "poor": {"joint": "Complete absence of dysfunction.", "a": "Zero gatekeeping.", "b": "Zero transition delays."}},
]
RISK_CATEGORIES = [("coercive_control", "Coercive Control", "financial isolation, stalking, schedule monopolization"),
                   ("threats", "Threats & Intimidation", "physical threats, child abduction risk"),
                   ("hostility", "Verbal & Emotional Hostility", "intense or hostile exchanges, especially at transitions"),
                   ("child_exposure", "Child Exposure", "disagreements observed by the child")]
RISK_LEVELS = ["Not assessed", "Low Risk", "Moderate Risk", "Moderate-to-High Risk", "High Risk"]
SAFETY_ALERT = ("Important Safety Note: If high-risk IPV indicators are present, joint mediation, open messaging, and unmonitored contact are counter-indicated. "
                "In these situations, court orders, supervised exchanges, or legal safety plans take priority over standard co-parenting goals.")
PATHWAYS = [
    {"key": "court", "lo": 1, "hi": 3, "name": "Litigation & Court", "levels": "Levels 1–3", "desc": "Formal orders and parallel mandates. Requires mandatory individual therapy."},
    {"key": "facilitation", "lo": 3, "hi": 5, "name": "Parent Facilitation & Coordination", "levels": "Levels 3–5", "desc": "Neutral professional resolves day-to-day bumps, supported by parent education, individual counseling, and neutral educational testing."},
    {"key": "mediation", "lo": 5, "hi": 7, "name": "Traditional Mediation", "levels": "Levels 5–7", "desc": "Guided conversations to update parenting plans or schedules without court."},
    {"key": "child_centered", "lo": 7, "hi": 10, "name": "Child-Centered Mediation", "levels": "Levels 7–10", "desc": "Collaborative sessions focusing directly on the child's evolving needs."},
    {"key": "direct", "lo": 10, "hi": 10, "name": "Direct Collaboration", "levels": "Level 10", "desc": "Managing schedule shifts directly using shared calendars on SA CoParents Align."},
]
RESOURCE_CATEGORIES = ["Individual (Parent A)", "Individual (Parent B)", "Individual (Child)", "Educational Assessment", "Parent Education", "Clinical & Forensics", "Joint / Co-Parenting", "Other"]
REASSESS_INTERVALS = ["Every 90 days", "Every 90 to 180 days", "Every 180 days"]
REASSESS_UP_DEFAULT = "Move away from formal facilitators, start traditional mediation, and introduce flexible schedule swaps."
REASSESS_DOWN_DEFAULT = "Re-check safety protocols, restrict communication strictly to app logs, and bring in court oversight or clinical therapy."
INTRO_TEXT = ("The SA CoParents Align system evaluates co-parenting dynamic stability on a 1 to 10 scale. Level 1 indicates high conflict or active safety risks, while Level 10 represents a smooth, "
              "fully collaborative partnership. This report provides a complete 1–10 behavioral breakdown—identifying specific areas where co-parents and individual parents do well (strengths) "
              "and where they struggle (gaps) at every tier. It details individual placements for Parent A and Parent B, establishes a Short-Term and Long-Term Roadmap, and matches families with "
              "targeted clinical and educational resources.")


def recommended_pathway(joint_rating) -> dict | None:
    """1–2 Court · 3–4 Facilitation · 5–6 Traditional Mediation · 7–9 Child-Centered · 10 Direct Collaboration."""
    if not joint_rating:
        return None
    r = int(joint_rating)
    key = "court" if r <= 2 else "facilitation" if r <= 4 else "mediation" if r <= 6 else "child_centered" if r <= 9 else "direct"
    return next(p for p in PATHWAYS if p["key"] == key)


def resource_lists(providers: list[dict]) -> tuple[list[str], list[str]]:
    ind = [p["label"] for p in providers if "individual" in p["lists"]]
    joint = [p["label"] for p in providers if "joint" in p["lists"]]
    return [*INDIVIDUAL_BASE, *ind, "Additional Counselor / Provider"], [*joint, *JOINT_BASE, "Additional Expert / Provider"]
CONFLICT_OPTIONS = ["Further Court Hearing", "Parent Facilitation", "Traditional Mediation", "Child-Centered Mediation"]
TEXT_FIELDS = ("matter_name", "court_county", "cause_number", "professional_role", "report_date", "parent_a_name", "parent_b_name", "joint_process_appropriate", "safety_notes",
               "safety_takeaway", "parent_a_strengths", "parent_a_gaps", "parent_a_growth", "parent_a_notes", "parent_b_strengths", "parent_b_gaps", "parent_b_growth", "parent_b_notes",
               "joint_strengths", "joint_gaps", "joint_notes", "alignment_agreements", "alignment_disagreements", "partial_alignment", "alignment_summary",
               "conflict_pathway", "conflict_management_rationale", "short_term_goals", "long_term_goals", "reassess_interval", "reassess_up", "reassess_down",
               "professional_summary", "next_review_date", "signature_name", "professional_title", "fv_a_received", "fv_b_received")
LIST_FIELDS = ("parent_a_resources", "parent_b_resources", "joint_resources", "conflict_management_options")
DICT_FIELDS = ("parent_a_provider", "parent_b_provider", "joint_provider")
INT_FIELDS = ("parent_a_rating", "parent_b_rating", "joint_rating")
ROWS_FIELDS = ("resource_rows",)
RISK_FIELDS = ("risk_screening",)
GROWTH_FIELDS = ("growth_status",)


def growth_lines(rep: dict, role: str) -> list[dict]:
    """Key Growth Areas for a parent with met-at-reassessment flags."""
    status = (rep.get("growth_status") or {}).get(role) or {}
    return [{"text": g.strip(), "met": bool(status.get(g.strip()))} for g in (rep.get(f"parent_{role}_growth") or "").split("\n") if g.strip()]


def court_summary(rep: dict) -> dict:
    """Court-safe snapshot of the Professional Evaluation Report frozen with a submission (no parent-reported notes)."""
    a, b, j = classify_individual(rep.get("parent_a_rating")), classify_individual(rep.get("parent_b_rating")), classify_joint(rep.get("joint_rating"))
    risk = rep.get("risk_screening") or {}
    chosen = rep.get("conflict_pathway") or ((j or {}).get("pathway") or {}).get("key")
    return {"ratings": {"parent_a": {"score": rep.get("parent_a_rating"), "label": (a or {}).get("label")}, "parent_b": {"score": rep.get("parent_b_rating"), "label": (b or {}).get("label")},
                        "joint": {"score": rep.get("joint_rating"), "label": (j or {}).get("label"), "mode": (j or {}).get("mode")}},
            "risk_screening": [{"label": lbl, "level": risk.get(k, {}).get("level", "Not assessed"), "note": risk.get(k, {}).get("note", "")} for k, lbl, _ in RISK_CATEGORIES],
            "fv_received": {"a": rep.get("fv_a_received"), "b": rep.get("fv_b_received")}, "joint_process_appropriate": rep.get("joint_process_appropriate"), "safety_takeaway": rep.get("safety_takeaway"),
            "growth": {"a": growth_lines(rep, "a"), "b": growth_lines(rep, "b")}, "parent_names": {"a": rep.get("parent_a_name"), "b": rep.get("parent_b_name")},
            "pathway": next((p["name"] for p in PATHWAYS if p["key"] == chosen), None), "pathway_rationale": rep.get("conflict_management_rationale"),
            "short_term_goals": [g.strip() for g in (rep.get("short_term_goals") or "").split("\n") if g.strip()], "long_term_goals": [g.strip() for g in (rep.get("long_term_goals") or "").split("\n") if g.strip()],
            "resources": rep.get("resource_rows") or [], "reassess_interval": rep.get("reassess_interval"), "next_review_date": rep.get("next_review_date"), "finalized_at": rep.get("finalized_at")}
AI_MODELS = [{"key": "gemini", "label": "Gemini 3.1 Pro"}, {"key": "openai", "label": "GPT-5.4 Mini"}]


def classify_individual(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, strengths, gaps = next(b for b in INDIVIDUAL_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "strengths": strengths, "gaps": gaps, "row": next(i for i, r in enumerate(SCALE_TABLE) if r["lo"] <= int(rating) <= r["hi"])}


def classify_joint(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, mode, strengths, gaps, guidance = next(b for b in JOINT_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "mode": mode, "strengths": strengths, "gaps": gaps, "guidance": guidance,
            "row": next(i for i, r in enumerate(SCALE_TABLE) if r["lo"] <= int(rating) <= r["hi"]), "pathway": recommended_pathway(rating)}


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


def prefill(doc: dict, pro: dict) -> dict:
    """Pull everything already in the case so the professional never re-enters it."""
    f = joint_findings(doc)
    sug = suggested_score(doc)
    rd = {r["key"]: r for r in readiness(doc)}
    parts = doc.get("participants") or {}
    fv = lambda k: "Not Applicable" if rd[k]["na"] else ("Received" if rd[k]["done"] else "Not Received")  # noqa: E731
    out = {"matter_name": f"{doc.get('subject_label') or 'Co-parenting'} — {doc.get('child_name') or ''}".strip(" —"), "court_county": (doc.get("court") or {}).get("court_name", ""),
           "cause_number": (doc.get("court") or {}).get("cause_number", ""), "professional_role": pro.get("pro_role", ""), "report_date": datetime.now(timezone.utc).date().isoformat(),
           "parent_a_name": parts.get("a", {}).get("name") or "Parent A", "parent_b_name": parts.get("b", {}).get("name") or "Parent B", "fv_a_received": fv("fv_a"), "fv_b_received": fv("fv_b"),
           "joint_rating": sug["score"] if sug else None, "parent_a_rating": None, "parent_b_rating": None,
           "risk_screening": {k: {"level": "Not assessed", "note": ""} for k, _, _ in RISK_CATEGORIES}, "reassess_interval": "Every 90 to 180 days",
           "reassess_up": REASSESS_UP_DEFAULT, "reassess_down": REASSESS_DOWN_DEFAULT, "resource_rows": []}
    for role in ("a", "b"):
        ans = _answers(doc, role)
        out[f"parent_{role}_strengths"] = _pick(ans, "working_well")
        out[f"parent_{role}_gaps"] = _pick(ans, "concerns")
    if f:
        out["joint_strengths"] = " ".join(f["alignment"])
        out["joint_gaps"] = " ".join(f["differences"])
        out["alignment_agreements"] = "\n".join(f["alignment"])
        out["alignment_disagreements"] = "\n".join(f["differences"])
        out["partial_alignment"] = "\n".join(f"{r['area']}: some common ground; may benefit from structured discussion." for r in f["alignment_map"] if r.get("status") == "Moderate alignment")
    return out


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


_CLEANERS = [(TEXT_FIELDS, _clean_text), (LIST_FIELDS, _clean_list), (DICT_FIELDS, _clean_dict), (INT_FIELDS, _clean_int), (ROWS_FIELDS, _clean_rows), (RISK_FIELDS, _clean_risk), (GROWTH_FIELDS, _clean_growth)]


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


def apply_status(rep: dict, upd: dict, status: str) -> None:
    if status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if status in ("final", "submitted_to_court") and not (upd.get("signature_name") or rep.get("signature_name")):
        raise HTTPException(status_code=400, detail="Professional Signature Name is required to finalize")
    upd["status"] = status
    if status == "final" and not rep.get("finalized_at"):
        upd["finalized_at"] = datetime.now(timezone.utc).isoformat()
        merged = {**rep, **upd}
        upd["ai_review"] = {k: {"model": d["model"], "drafted_at": d["at"], "edited": (merged.get(k) or "").strip() != d["text"].strip()} for k, d in (rep.get("ai_drafts") or {}).items()}


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


def build_router(db, get_current_user, log_event) -> APIRouter:
    r = APIRouter()

    async def own_case(rid: str, user: dict) -> dict:
        if user.get("role") not in ("professional", "admin") or (user.get("role") == "professional" and not user.get("approved")):
            raise HTTPException(status_code=403, detail="Approved professional access required.")
        q = {"id": rid} if user.get("role") == "admin" else {"id": rid, "professional_id": user["_id"]}
        doc = await db.joint_reports.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Case not found")
        return doc

    async def view(rep: dict, doc: dict) -> dict:
        from providers import active_providers
        provs = await active_providers(db)
        ind, joint = resource_lists(provs)
        if not rep.get("resource_rows"):
            rep = {**rep, "resource_rows": default_resource_rows(provs)}
        rep = {**rep, "reassess_up": rep.get("reassess_up") or REASSESS_UP_DEFAULT, "reassess_down": rep.get("reassess_down") or REASSESS_DOWN_DEFAULT,
               "reassess_interval": rep.get("reassess_interval") or "Every 90 to 180 days"}
        return {"report": rep, "readiness": readiness(doc), "classification": {"parent_a": classify_individual(rep.get("parent_a_rating")), "parent_b": classify_individual(rep.get("parent_b_rating")),
                "joint": classify_joint(rep.get("joint_rating"))}, "library": {"individual_resources": ind, "joint_resources": joint, "providers": provs, "conflict_options": CONFLICT_OPTIONS,
                "joint_process_options": JOINT_OPTIONS, "receipt_options": RECEIPT, "statuses": STATUSES, "ai_models": AI_MODELS, "scale_table": SCALE_TABLE, "risk_categories": RISK_CATEGORIES,
                "risk_levels": RISK_LEVELS, "pathways": PATHWAYS, "resource_categories": RESOURCE_CATEGORIES, "reassess_intervals": REASSESS_INTERVALS}, "notes": {"safety": SAFETY_NOTE, "rating": RATING_NOTE, "tagline": TAGLINE, "alert": SAFETY_ALERT, "intro": INTRO_TEXT},
                "case": {"id": doc["id"], "case_code": doc.get("case_code"), "child_name": doc.get("child_name"), "subject_label": doc.get("subject_label")}}

    async def get_or_create(doc: dict, user: dict) -> dict:
        rep = await db.professional_reports.find_one({"case_id": doc["id"]}, {"_id": 0})
        if rep:
            return rep
        pro = await db.users.find_one({"_id": doc["professional_id"]}, {"_id": 0, "name": 1, "profile": 1})
        now = datetime.now(timezone.utc).isoformat()
        rep = {"id": str(uuid.uuid4()), "case_id": doc["id"], "professional_id": doc["professional_id"], "professional_name": (pro or {}).get("name", ""), "joint_report_id": doc["id"],
               "parent_a_assessment_id": f"{doc['id']}:a", "parent_b_assessment_id": f"{doc['id']}:b", "status": "draft", "created_at": now, "updated_at": now, "finalized_at": None,
               **{k: "" for k in TEXT_FIELDS}, **{k: [] for k in LIST_FIELDS}, **{k: {"name": "", "specialty": "", "contact": ""} for k in DICT_FIELDS}, **{k: None for k in INT_FIELDS},
               **prefill(doc, {**((pro or {}).get("profile") or {})})}
        await db.professional_reports.insert_one({**rep})
        await log_event(doc["id"], "LEGAL_LENS_REPORT_CREATED", user)
        return rep

    @r.get("/cases/{rid}/professional-report")
    async def get_report(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        return await view(await get_or_create(doc, user), doc)

    @r.get("/cases/{rid}/professional-report/readiness")
    async def get_readiness(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        rep = await db.professional_reports.find_one({"case_id": rid}, {"_id": 0, "status": 1})
        return {"readiness": readiness(doc), "status": (rep or {}).get("status")}

    @r.put("/cases/{rid}/professional-report")
    async def save_report(rid: str, body: ReportIn, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        rep = await get_or_create(doc, user)
        upd = sanitize_fields(body.fields)
        if body.status:
            apply_status(rep, upd, body.status)
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.professional_reports.update_one({"case_id": rid}, {"$set": upd})
        await log_event(rid, "LEGAL_LENS_REPORT_FINALIZED" if body.status == "final" else "LEGAL_LENS_REPORT_SAVED", user)
        if upd.get("ai_review"):
            await log_event(rid, ai_disclosure_line(upd["ai_review"]), user)
        return await view({**rep, **upd}, doc)

    @r.post("/cases/{rid}/professional-report/ai-draft")
    async def ai_draft(rid: str, body: AiDraftIn, user=Depends(get_current_user)):
        from legal_ai import draft_lens_report
        doc = await own_case(rid, user)
        rep = {**(await get_or_create(doc, user)), **sanitize_fields({k: v for k, v in body.fields.items() if k not in DICT_FIELDS})}
        cls = (await view(rep, doc))["classification"]
        fields, source, label = await draft_lens_report(rep, cls, rid, body.model)
        drafts = merge_drafts(rep, fields, label, source)
        await db.professional_reports.update_one({"case_id": rid}, {"$set": {"ai_drafts": drafts}})
        await log_event(rid, f"LEGAL_LENS_AI_DRAFT ({label}, {len(fields)} sections)", user)
        return {"fields": fields, "source": source, "model": label, "label": "AI-Assisted Draft — Professional Review Required", "ai_drafts": drafts}

    @r.get("/cases/{rid}/professional-report/pdf")
    async def report_pdf(rid: str, user=Depends(get_current_user)):
        from pdf_report import build_legal_lens_pdf
        doc = await own_case(rid, user)
        rep = await get_or_create(doc, user)
        await log_event(rid, "LEGAL_LENS_REPORT_EXPORTED", user)
        return Response(content=build_legal_lens_pdf(await view(rep, doc)), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="legal-lens-report-{doc.get("case_code") or rid}.pdf"'})

    @r.get("/professional-report/cases")
    async def my_cases(user=Depends(get_current_user)):
        if user.get("role") != "professional" or not user.get("approved"):
            raise HTTPException(status_code=403, detail="Approved professional access required.")
        docs = await db.joint_reports.find({"professional_id": user["_id"], "kind": {"$ne": "agreement"}}, {"_id": 0, "id": 1, "case_code": 1, "child_name": 1, "subject_label": 1, "participants": 1, "responses": 1, "subjects": 1, "subject": 1, "created_at": 1}).sort("created_at", -1).to_list(200)
        reps = {x["case_id"]: x["status"] for x in await db.professional_reports.find({"professional_id": user["_id"]}, {"_id": 0, "case_id": 1, "status": 1}).to_list(500)}
        return [case_summary(d, reps.get(d["id"], "not_started")) for d in docs]

    return r
