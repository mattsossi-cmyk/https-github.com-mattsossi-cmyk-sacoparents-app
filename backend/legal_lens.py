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


def resource_lists(providers: list[dict]) -> tuple[list[str], list[str]]:
    ind = [p["label"] for p in providers if "individual" in p["lists"]]
    joint = [p["label"] for p in providers if "joint" in p["lists"]]
    return [*INDIVIDUAL_BASE, *ind, "Additional Counselor / Provider"], [*joint, *JOINT_BASE, "Additional Expert / Provider"]
CONFLICT_OPTIONS = ["Further Court Hearing", "Parent Facilitation", "Traditional Mediation", "Child-Centered Mediation"]
TEXT_FIELDS = ("matter_name", "court_county", "cause_number", "professional_role", "report_date", "parent_a_name", "parent_b_name", "joint_process_appropriate", "safety_notes",
               "parent_a_strengths", "parent_a_gaps", "parent_a_notes", "parent_b_strengths", "parent_b_gaps", "parent_b_notes", "joint_strengths", "joint_gaps", "joint_notes",
               "alignment_agreements", "alignment_disagreements", "partial_alignment", "alignment_summary", "conflict_management_rationale", "short_term_goals", "long_term_goals",
               "professional_summary", "next_review_date", "signature_name", "professional_title", "fv_a_received", "fv_b_received")
LIST_FIELDS = ("parent_a_resources", "parent_b_resources", "joint_resources", "conflict_management_options")
DICT_FIELDS = ("parent_a_provider", "parent_b_provider", "joint_provider")
INT_FIELDS = ("parent_a_rating", "parent_b_rating", "joint_rating")
AI_MODELS = [{"key": "gemini", "label": "Gemini 3.1 Pro"}, {"key": "openai", "label": "GPT-5.4 Mini"}]


def classify_individual(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, strengths, gaps = next(b for b in INDIVIDUAL_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "strengths": strengths, "gaps": gaps}


def classify_joint(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, mode, strengths, gaps, guidance = next(b for b in JOINT_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "mode": mode, "strengths": strengths, "gaps": gaps, "guidance": guidance}


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
           "joint_rating": sug["score"] if sug else None, "parent_a_rating": None, "parent_b_rating": None}
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
        return {"report": rep, "readiness": readiness(doc), "classification": {"parent_a": classify_individual(rep.get("parent_a_rating")), "parent_b": classify_individual(rep.get("parent_b_rating")),
                "joint": classify_joint(rep.get("joint_rating"))}, "library": {"individual_resources": ind, "joint_resources": joint, "providers": provs, "conflict_options": CONFLICT_OPTIONS,
                "joint_process_options": JOINT_OPTIONS, "receipt_options": RECEIPT, "statuses": STATUSES, "ai_models": AI_MODELS}, "notes": {"safety": SAFETY_NOTE, "rating": RATING_NOTE, "tagline": TAGLINE},
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
        if rep["status"] == "submitted_to_court" and body.status != "submitted_to_court":
            pass
        upd = {}
        for k, v in body.fields.items():
            if k in TEXT_FIELDS:
                upd[k] = str(v or "")[:8000]
            elif k in LIST_FIELDS and isinstance(v, list):
                upd[k] = [str(x)[:200] for x in v][:30]
            elif k in DICT_FIELDS and isinstance(v, dict):
                upd[k] = {f: str(v.get(f, ""))[:300] for f in ("name", "specialty", "contact")}
            elif k in INT_FIELDS:
                upd[k] = max(1, min(10, int(v))) if v not in (None, "", 0) else None
        if body.status:
            if body.status not in STATUSES:
                raise HTTPException(status_code=400, detail="Invalid status")
            if body.status in ("final", "submitted_to_court") and not (upd.get("signature_name") or rep.get("signature_name")):
                raise HTTPException(status_code=400, detail="Professional Signature Name is required to finalize")
            upd["status"] = body.status
            if body.status == "final" and not rep.get("finalized_at"):
                upd["finalized_at"] = datetime.now(timezone.utc).isoformat()
                merged = {**rep, **upd}
                upd["ai_review"] = {k: {"model": d["model"], "drafted_at": d["at"], "edited": (merged.get(k) or "").strip() != d["text"].strip()} for k, d in (rep.get("ai_drafts") or {}).items()}
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.professional_reports.update_one({"case_id": rid}, {"$set": upd})
        await log_event(rid, "LEGAL_LENS_REPORT_FINALIZED" if body.status == "final" else "LEGAL_LENS_REPORT_SAVED", user)
        if upd.get("ai_review"):
            n_ed = sum(1 for x in upd["ai_review"].values() if x["edited"])
            await log_event(rid, f"LEGAL_LENS_AI_DISCLOSURE: {len(upd['ai_review'])} AI-assisted section(s), {n_ed} edited by professional before certification", user)
        return await view({**rep, **upd}, doc)

    @r.post("/cases/{rid}/professional-report/ai-draft")
    async def ai_draft(rid: str, body: AiDraftIn, user=Depends(get_current_user)):
        from legal_ai import draft_lens_report
        doc = await own_case(rid, user)
        rep = {**(await get_or_create(doc, user)), **{k: v for k, v in body.fields.items() if k in TEXT_FIELDS or k in LIST_FIELDS or k in INT_FIELDS}}
        cls = (await view(rep, doc))["classification"]
        fields, source, label = await draft_lens_report(rep, cls, rid, body.model)
        now = datetime.now(timezone.utc).isoformat()
        drafts = {**(rep.get("ai_drafts") or {}), **{k: {"text": v, "model": label if source == "ai" else f"{label} (rule-based fallback)", "at": now} for k, v in fields.items()}}
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
        return [{"id": d["id"], "case_code": d.get("case_code"), "child_name": d.get("child_name"), "subject_label": d.get("subject_label"), "status": reps.get(d["id"], "not_started"),
                 "parent_a": (d.get("participants") or {}).get("a", {}).get("name"), "parent_b": (d.get("participants") or {}).get("b", {}).get("name"), "readiness": readiness(d)} for d in docs]

    return r
