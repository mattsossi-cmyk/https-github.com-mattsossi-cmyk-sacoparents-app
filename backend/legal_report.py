"""Professional Legal Report: draft generation from case data → professional review → certified, versioned finalization.
Same record as the Professional Report (joint_reports.professional_statement); professional-only, never parent-facing."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from coparenting_tiers import joint_findings
from joint_data import SAFETY_SUBJECT_KEYS, SUBJECTS
from joint_engine import generate_joint_report
from legal_ai import AI_LABEL, draft_lens

STATUSES = ("not_started", "draft", "professional_review", "finalized")
PURPOSE = ("This Professional Legal Report organizes information provided through SA CoParents assessments and related case materials for review by the "
           "authorized professional. Parent-reported information should not be interpreted as independently verified fact unless specifically identified as such by the professional.")
SAFETY_NOTICE = ("Communication, mediation, joint decision-making, and other dispute-resolution options should be considered in light of any disclosed safety concerns, "
                 "allegations of family violence, protective orders, coercive control concerns, or other circumstances affecting safety and informed participation.")
CERTIFICATION = ("I have reviewed this report and understand that AI-generated or system-generated language is a drafting aid. I am responsible for the professional "
                 "observations, conclusions, selections, and statements contained in the finalized report.")
OPTIONS_LIBRARY = ["SA CoParents Communication Builder", "BIFF communication principles", "Structured written communication", "OurFamilyWizard", "ToneMeter",
                   "Children in the Middle", "Co-Parenting Education", "Child-Focused Mediation", "Traditional Mediation", "Parent Facilitation", "Parent Coordination",
                   "Therapeutic Support", "Educational Professional Consultation", "Medical Professional Consultation", "Mental Health Professional Consultation",
                   "Collaborative Law", "Attorney-to-Attorney Negotiation", "Court Resolution"]
PATHS = ["Continue Direct Co-Parenting Work", "Structured Communication", "Child-Focused Mediation", "Traditional Mediation", "Parent Facilitation / Coordination",
         "Collaborative Process", "Professional Consultation", "Legal Negotiation", "Court Determination", "Other"]
PARENT_HEADINGS = [("needs_most", "Child-focused priorities"), ("working_well", "Areas the parent believes are working"), ("concerns", "Primary parenting concerns"),
                   ("improve", "Goals for resolution"), ("options", "Options the parent would consider"), ("other_parent", "The parent's view of the other parent's likely concerns")]
CHILD_TOPICS = {"schedule": "Parenting schedule", "holidays": "Parenting schedule", "education": "Education", "medical": "Medical care", "psychological": "Mental/behavioral health",
                "activities": "Extracurricular activities", "transitions": "Transitions", "communication": "Communication concerning the child", "technology": "Communication concerning the child",
                "decision_making": "Decision-making", "special_needs": "Special needs", "child_needs": "Other child-specific concerns", "routine": "Other child-specific concerns"}
EDITABLE = ("observations", "further_attention", "alignment_areas", "partial_alignment", "procedural_considerations", "professional_comments", "options_resources",
            "options_custom", "conflict_resolution_paths", "conflict_resolution_explanation", "include_parent_summaries_in_court", "role")
LENS_MAP = {"professional_observations": "observations", "issues_requiring_attention": "further_attention", "existing_agreements": "alignment_areas",
            "agreement_building_opportunities": "partial_alignment", "procedural_considerations": "procedural_considerations"}
BANNED_LABELS = ("narcissist", "abusive", "alienat", "unstable", "mentally ill", "dangerous", "deceptive")

_now = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


def _subjects(doc: dict) -> list[str]:
    return list(doc.get("subjects") or ([doc["subject"]] if doc.get("subject") else []))


def _complete(doc: dict, role: str) -> bool:
    return bool(((doc.get("responses") or {}).get(role) or {}).get("answers"))


def _status_word(done: bool, exists: bool = True) -> str:
    return "Complete" if done else ("Incomplete" if exists else "Not Created")


def availability(doc: dict, notes_count: int) -> list[dict]:
    subs = _subjects(doc)
    a, b = _complete(doc, "a"), _complete(doc, "b")
    fa = bool(((doc.get("responses") or {}).get("a") or {}).get("foundation"))
    fb = bool(((doc.get("responses") or {}).get("b") or {}).get("foundation"))
    joint_exists = doc.get("kind", "joint_report") == "joint_report"
    safety = any(s in SAFETY_SUBJECT_KEYS for s in subs)
    rows = [{"key": "assessment_a", "label": "Parent A Co-Parenting Assessment", "status": _status_word(a)}, {"key": "assessment_b", "label": "Parent B Co-Parenting Assessment", "status": _status_word(b)},
            {"key": "foundation_a", "label": "Parent A Foundation Statement", "status": "Complete" if fa else "Incomplete"}, {"key": "foundation_b", "label": "Parent B Foundation Statement", "status": "Complete" if fb else "Incomplete"},
            {"key": "joint", "label": "Joint Assessment", "status": _status_word(a and b, joint_exists)}]
    for key, label in (("education", "Educational Assessment"), ("medical", "Medical Assessment"), ("psychological", "Psychological Assessment")):
        rows.append({"key": key, "label": label, "status": (_status_word(a and b) if key in subs else "Not Applicable")})
    rows.append({"key": "safety", "label": "Family Violence / Communication Safety Assessment", "status": (_status_word(a and b) if safety else "Not Applicable")})
    rows.append({"key": "notes", "label": "Professional Notes", "status": "Available" if notes_count else "None"})
    return rows


def _parent_summary(doc: dict, role: str) -> dict:
    answers = ((doc.get("responses") or {}).get(role) or {}).get("answers") or {}
    out = {"label": "PARENT-REPORTED INFORMATION", "items": []}
    for key, heading in PARENT_HEADINGS:
        vals = [str(v).strip() for k, v in answers.items() if (k == key or k.endswith(f":{key}") or k.startswith(f"{key}:")) and str(v).strip()]
        if vals:
            out["items"].append({"heading": heading, "text": " ".join(vals)[:1500]})
    foundation = ((doc.get("responses") or {}).get(role) or {}).get("foundation") or []
    if foundation:
        out["items"].append({"heading": "Foundation Statement (parent's own words)", "text": " ".join(str(f.get("content", "")).strip() for f in foundation)[:2000]})
    if not out["items"]:
        out["items"].append({"heading": "Assessment", "text": "No completed assessment was available for this parent at the time this draft was generated."})
    return out


def _joint(doc: dict) -> dict:
    f = joint_findings(doc)
    if not f:
        return {"available": False, "alignment": [], "differences": [], "unresolved": [], "shared_priorities": [], "potential_agreement": [],
                "note": "No completed Joint Assessment was available at the time this draft was generated."}
    rep = generate_joint_report(doc)
    rows = rep.get("alignment_map") or []
    return {"available": True, "alignment": f["alignment"], "differences": f["differences"],
            "unresolved": [f"{r['area']} remains an open area for discussion." for r in rows if r.get("status") == "Needs discussion"],
            "shared_priorities": f["child_focused"], "potential_agreement": [f"{r['area']}: the parents share some common ground; further discussion may produce agreement." for r in rows if r.get("status") == "Moderate alignment"], "note": ""}


def _child_focused(doc: dict, joint: dict) -> list[dict]:
    out, seen = [], set()
    for s in _subjects(doc):
        topic = CHILD_TOPICS.get(s)
        if not topic or topic in seen:
            continue
        seen.add(topic)
        label = SUBJECTS.get(s, {}).get("label", s)
        status = "differences noted" if joint["differences"] else "alignment reported"
        out.append({"topic": topic, "text": f"{label}: both parents provided perspectives; {status} in the joint assessment." if joint["available"] else f"{label}: assessment information available for one or both parents."})
    return out


def _communication(doc: dict, joint: dict) -> list[dict]:
    subs = _subjects(doc)
    rows = [{"pattern": "Ability to exchange child-related information", "text": "Both parents completed independent assessments; neither viewed the other's responses." if joint["available"] else "Assessment information incomplete."}]
    if "communication" in subs or "technology" in subs:
        rows.append({"pattern": "Communication methods", "text": "Communication is an assessed subject in this case; see the parents' reported preferences in Section 4."})
    rows.append({"pattern": "Ability to make joint decisions", "text": f"{len(joint['alignment'])} aligned and {len(joint['differences'])} differing area(s) reported." if joint["available"] else "Not yet assessable."})
    if joint["differences"]:
        rows.append({"pattern": "Areas where structure may assist", "text": "; ".join(d.replace("Parents expressed different perspectives regarding ", "").rstrip(".") for d in joint["differences"][:4])})
    return rows


def build_draft(doc: dict) -> dict:
    joint = _joint(doc)
    subs = _subjects(doc)
    return {"parent_a_summary": _parent_summary(doc, "a"), "parent_b_summary": _parent_summary(doc, "b"), "joint": joint,
            "child_focused_summary": _child_focused(doc, joint), "communication_summary": _communication(doc, joint),
            "safety_notice": any(s in SAFETY_SUBJECT_KEYS for s in subs), "generated_at": _now()}


def information_reviewed(doc: dict, notes_count: int) -> list[str]:
    subs = _subjects(doc)
    items = [lbl for role, lbl in (("a", "Parent A Co-Parenting Assessment"), ("b", "Parent B Co-Parenting Assessment")) if _complete(doc, role)]
    items += [f"Parent {r.upper()} Foundation Statement" for r in ("a", "b") if ((doc.get("responses") or {}).get(r) or {}).get("foundation")]
    if _complete(doc, "a") and _complete(doc, "b"):
        items += ["Joint Co-Parenting Assessment", "Joint Report"]
    for key, lbl in (("education", "Educational Assessment"), ("medical", "Medical Assessment"), ("psychological", "Psychological Assessment"), ("communication", "Communication Assessment")):
        if key in subs:
            items.append(lbl)
    if any(s in SAFETY_SUBJECT_KEYS for s in subs):
        items.append("Family Violence / Safety Assessment")
    if notes_count:
        items.append("Professional Notes")
    return items


class PatchIn(BaseModel):
    fields: dict


class FinalizeIn(BaseModel):
    certified: bool
    certified_name: str
    certified_date: str
    title: str = ""
    bar_number: str = ""
    organization: str = ""
    email: str = ""
    phone: str = ""


class GenerateIn(BaseModel):
    regenerate: bool = False


DIFF_FIELDS = [("observations", "Professional Observations"), ("further_attention", "Issues Requiring Attention"), ("alignment_areas", "Areas of Existing Agreement"),
               ("partial_alignment", "Areas Appropriate for Further Agreement Building"), ("procedural_considerations", "Procedural Considerations"), ("professional_comments", "Other Professional Comments"),
               ("conflict_resolution_explanation", "Professional Explanation"), ("options_resources", "Options and Resources"), ("options_custom", "Own options"), ("conflict_resolution_paths", "Conflict-Resolution Paths")]


def _text_diff(a: str, b: str) -> list[dict]:
    """Word-level diff segments: [{op: equal|insert|delete, text}]."""
    import difflib
    wa, wb = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=wa, b=wb, autojunk=False).get_opcodes():
        if op == "equal":
            out.append({"op": "equal", "text": " ".join(wa[i1:i2])})
        else:
            if i2 > i1:
                out.append({"op": "delete", "text": " ".join(wa[i1:i2])})
            if j2 > j1:
                out.append({"op": "insert", "text": " ".join(wb[j1:j2])})
    return out


def report_diff(old: dict, new: dict) -> list[dict]:
    rows = []
    for key, label in DIFF_FIELDS:
        a, b = old.get(key), new.get(key)
        if isinstance(a, list) or isinstance(b, list):
            a, b = a or [], b or []
            if a != b:
                rows.append({"key": key, "label": label, "kind": "list", "added": [x for x in b if x not in a], "removed": [x for x in a if x not in b]})
        else:
            a, b = str(a or ""), str(b or "")
            if a != b:
                rows.append({"key": key, "label": label, "kind": "text", "segments": _text_diff(a, b)})
    return rows


def build_payload(doc: dict, notes: int) -> dict:
    st = doc.get("professional_statement") or {}
    return {"report": st, "status": st.get("legal_status") or ("draft" if st.get("legal_draft") else "not_started"), "availability": availability(doc, notes),
            "information_reviewed": information_reviewed(doc, notes), "purpose": PURPOSE, "safety_notice_text": SAFETY_NOTICE if (st.get("legal_draft") or {}).get("safety_notice") else "",
            "certification_text": CERTIFICATION, "options_library": OPTIONS_LIBRARY, "paths": PATHS, "ai_label": AI_LABEL,
            "versions": [{k: v for k, v in s.items() if k != "report"} for s in (doc.get("legal_report_versions") or [])],
            "case": {"id": doc["id"], "case_code": doc.get("case_code"), "child_name": doc.get("child_name"), "subject_label": doc.get("subject_label"),
                     "parent_a": (doc.get("participants") or {}).get("a", {}).get("name") or "Parent A", "parent_b": (doc.get("participants") or {}).get("b", {}).get("name") or "Parent B",
                     "court": doc.get("court") or {}}}


def build_router(db, get_current_user, log_event) -> APIRouter:
    r = APIRouter()

    async def own_case(rid: str, user: dict) -> dict:
        if user.get("role") not in ("professional", "admin"):
            raise HTTPException(status_code=403, detail="Professional access required.")
        q = {"id": rid} if user.get("role") == "admin" else {"id": rid, "professional_id": user["_id"]}
        doc = await db.joint_reports.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Case not found")
        if user.get("role") == "professional" and not user.get("approved"):
            raise HTTPException(status_code=403, detail="Professional approval required.")
        return doc

    async def notes_count(rid: str, user: dict) -> int:
        return await db.professional_notes.count_documents({"report_id": rid, "author_id": user["_id"]})

    def payload(doc: dict, notes: int) -> dict:
        return build_payload(doc, notes)

    @r.get("/cases/{rid}/professional-legal-report")
    async def get_report(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        await log_event(rid, "LEGAL_REPORT_VIEWED", user)
        return payload(doc, await notes_count(rid, user))

    @r.post("/cases/{rid}/professional-legal-report/generate")
    async def generate(rid: str, body: GenerateIn, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        st = doc.get("professional_statement") or {}
        if st.get("legal_status") == "finalized" and not body.regenerate:
            raise HTTPException(status_code=409, detail="Report is finalized. Use Regenerate to start a new version.")
        draft = build_draft(doc)
        lens, source = await draft_lens(draft, rid)
        created = not st.get("legal_draft")
        st = {**st, "legal_draft": draft, "ai_generated_content": {**lens, "source": source, "generated_at": draft["generated_at"]}, "legal_status": "draft", "purpose": PURPOSE}
        for ai_key, field in LENS_MAP.items():
            if body.regenerate or not (st.get(field) or "").strip():
                st[field] = lens[ai_key]
        st.setdefault("options_resources", [])
        st.setdefault("conflict_resolution_paths", [])
        st.setdefault("status", "draft")
        st["updated_at"] = _now()
        await db.joint_reports.update_one({"id": rid}, {"$set": {"professional_statement": st}})
        await log_event(rid, "LEGAL_REPORT_CREATED" if created else "LEGAL_REPORT_GENERATED", user)
        if not created:
            pass
        doc["professional_statement"] = st
        return payload(doc, await notes_count(rid, user))

    @r.patch("/professional-legal-reports/{rid}")
    async def patch_report(rid: str, body: PatchIn, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        st = doc.get("professional_statement") or {}
        changes = {k: v for k, v in body.fields.items() if k in EDITABLE}
        text = " ".join(str(v) for v in changes.values() if isinstance(v, str)).lower()
        if any(b in text for b in BANNED_LABELS):
            raise HTTPException(status_code=400, detail="Do not characterize a parent with diagnostic or pejorative labels unless quoting an identified documented source (name the source).")
        st.update({k: (v[:6000] if isinstance(v, str) else v) for k, v in changes.items()})
        st["professional_edited_content"] = {**(st.get("professional_edited_content") or {}), **{k: _now() for k in changes}}
        if st.get("legal_status") == "finalized":
            st["legal_status"] = "professional_review"
        elif st.get("legal_status") == "draft" and changes:
            st["legal_status"] = "professional_review"
        st["updated_at"] = _now()
        await db.joint_reports.update_one({"id": rid}, {"$set": {"professional_statement": st}})
        await log_event(rid, "LEGAL_REPORT_EDITED", user)
        doc["professional_statement"] = st
        return payload(doc, await notes_count(rid, user))

    @r.post("/professional-legal-reports/{rid}/preview")
    async def preview(rid: str, user=Depends(get_current_user)):
        await own_case(rid, user)
        await log_event(rid, "LEGAL_REPORT_PREVIEWED", user)
        return {"ok": True}

    @r.post("/professional-legal-reports/{rid}/finalize")
    async def finalize(rid: str, body: FinalizeIn, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        st = doc.get("professional_statement") or {}
        if not st.get("legal_draft"):
            raise HTTPException(status_code=400, detail="Generate a draft before finalizing.")
        if not (body.certified and body.certified_name.strip() and body.certified_date.strip()):
            raise HTTPException(status_code=400, detail="Certification checkbox, professional name and date are required.")
        for f in ("observations", "next_steps"):
            st.setdefault(f, "")
        versions = doc.get("legal_report_versions") or []
        version = len(versions) + 1
        now = _now()
        st.update({"legal_status": "finalized", "status": "ready", "version": max(int(st.get("version") or 0), version), "professional_certified": True,
                   "professional_certified_name": body.certified_name.strip()[:120], "professional_certified_at": now, "professional_certified_date": body.certified_date.strip()[:40],
                   "certification": {"title": body.title[:120], "bar_number": body.bar_number[:60], "organization": body.organization[:160], "email": body.email[:160], "phone": body.phone[:40]},
                   "finalized_at": now, "updated_at": now, "legal_version": version})
        snapshot = {"version": version, "finalized_at": now, "professional_name": body.certified_name.strip()[:120], "professional_id": user["_id"], "case_id": rid, "audit_timestamp": now, "report": st}
        await db.joint_reports.update_one({"id": rid}, {"$set": {"professional_statement": st}, "$push": {"legal_report_versions": snapshot}})
        await log_event(rid, "LEGAL_REPORT_FINALIZED", user)
        doc["professional_statement"] = st
        doc["legal_report_versions"] = versions + [snapshot]
        return payload(doc, await notes_count(rid, user))

    @r.get("/professional-legal-reports/{rid}/pdf")
    async def pdf(rid: str, user=Depends(get_current_user)):
        from pdf_report import build_legal_report_pdf
        doc = await own_case(rid, user)
        st = doc.get("professional_statement") or {}
        if not st.get("legal_draft"):
            raise HTTPException(status_code=400, detail="Generate a draft first.")
        pro = await db.users.find_one({"_id": doc["professional_id"]}, {"_id": 0, "name": 1, "profile": 1, "email": 1}) or {}
        await log_event(rid, "LEGAL_REPORT_EXPORTED", user)
        data = {**payload(doc, await notes_count(rid, user)), "professional": {"name": pro.get("name", ""), **(pro.get("profile") or {})}, "date": _now()[:10]}
        return Response(content=build_legal_report_pdf(data), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="professional-legal-report-{doc.get("case_code") or rid}.pdf"'})

    @r.get("/professional-legal-reports/{rid}/diff")
    async def diff(rid: str, from_version: int = 0, to_version: int = 0, user=Depends(get_current_user)):
        """Compare finalized versions (to_version=0 → current working copy)."""
        doc = await own_case(rid, user)
        versions = {v["version"]: v for v in (doc.get("legal_report_versions") or [])}
        if from_version not in versions:
            raise HTTPException(status_code=404, detail="Version not found")
        old = versions[from_version]["report"]
        new = versions[to_version]["report"] if to_version else (doc.get("professional_statement") or {})
        return {"from_version": from_version, "to_version": to_version or "current", "from_finalized_at": versions[from_version]["finalized_at"],
                "to_finalized_at": versions[to_version]["finalized_at"] if to_version else None, "changes": report_diff(old, new)}

    @r.get("/professional-legal-report/sample")
    async def sample():
        from sample_professional_report import sample_legal_report
        return sample_legal_report()

    @r.get("/professional-legal-report/sample/pdf")
    async def sample_pdf():
        from pdf_report import build_legal_report_pdf
        from sample_professional_report import sample_legal_report
        return Response(content=build_legal_report_pdf(sample_legal_report()), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="sample-professional-legal-report.pdf"'})

    return r
