"""Court workflow: judge refers case -> pro accepts -> parents -> Joint Report -> Professional Statement -> submit to court (frozen versions)."""
import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from html import escape

from bson import Binary
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import AliasChoices, BaseModel, Field

from joint_data import new_case_code
from joint_engine import generate_joint_report
from coparenting_tiers import TIERS, clean_library, framework_block, joint_findings, level_history, suggested_score, tier_for
from pdf_report import build_joint_pdf, build_professional_statement_pdf, merge_pdfs

STAGES = ["Court Referral", "Accepted", "Parents Invited", "Assessments Complete", "Joint Report Ready", "Professional Statement Ready", "Submitted to Court"]
STATEMENT_FIELDS = ("role_basis", "process_summary", "observations", "safety_considerations", "next_steps", "alignment_areas", "further_attention", "partial_alignment", "alignment_summary", "resources_considered", "current_status")
STATEMENT_ROLES = ("Mediator", "Therapist", "Parenting Facilitator", "Parenting Coordinator", "Amicus Attorney", "Attorney", "Other")
STATEMENT_MATERIALS = ("Parent A Assessment", "Parent B Assessment", "Joint Report", "Educational Assessment", "Medical Assessment", "Psychological Assessment", "Co-Parenting Agreement", "Safety Assessment", "Other")
STATEMENT_ATTESTATION = ("I attest that this Professional Assessment Statement reflects my professional observations of the facilitation process, "
                         "that it contains no recommendation regarding conservatorship or possession, and that I have authority to submit it to the court.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def court_stage(doc: dict) -> dict:
    """Derive the 7-step court workflow stage from existing case data."""
    stage = {"index": _stage_index(doc), "steps": STAGES, "court_referred": bool(doc.get("court_referral_id"))}
    return {**stage, "label": STAGES[stage["index"]]}


def _stage_index(doc: dict) -> int:
    both = bool(doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b"))
    if doc.get("court_submissions"):
        return 6
    if both and (doc.get("professional_statement") or {}).get("status") == "ready":
        return 5
    if both:
        return 4 if doc.get("report_generated_at") else 3
    if doc.get("status") not in (None, "draft") or doc.get("responses"):
        return 2
    return 1 if doc.get("court_referral_id") else 2


class ReferralIn(BaseModel):
    professional_id: str
    cause_number: str
    court_name: str = ""
    subject: str = "communication"
    child_initials: str = ""
    parent_a_name: str = ""
    parent_a_email: str = ""
    parent_b_name: str = ""
    parent_b_email: str = ""
    note: str = ""
    hearing_date: str = ""
    requested_reports: list[str] = []


REPORT_TYPES = {
    "co_parenting": ("Co-Parenting Joint Report", ["co_parenting"]),
    "education": ("Educational Joint Report", ["education"]),
    "medical": ("Medical Joint Report", ["medical"]),
    "psychological": ("Psychological Joint Report", ["psychological"]),
    "agreement": ("Co-Parenting Agreement", []),
    "family_violence": ("Family Violence / Safety Assessment", ["safety", "risk", "safety_communication", "safeguards"]),
}


def _valid_reports(keys: list[str]) -> list[str]:
    bad = [k for k in keys if k not in REPORT_TYPES]
    if bad:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {', '.join(bad)}")
    return list(dict.fromkeys(keys))


class HearingDateIn(BaseModel):
    hearing_date: str = ""


def _valid_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="Hearing date must be YYYY-MM-DD")


class DeclineIn(BaseModel):
    reason: str


class StatementIn(BaseModel):
    """Professional Report fields. The v8 'Legal Lens' template's camelCase names are accepted as aliases."""
    model_config = {"populate_by_name": True}
    role_basis: str = ""
    process_summary: str = ""
    observations: str = ""
    safety_considerations: str = ""
    next_steps: str = ""
    alignment_areas: str = Field("", validation_alias=AliasChoices("alignment_areas", "alignmentAgreements"))
    further_attention: str = Field("", validation_alias=AliasChoices("further_attention", "alignmentDisagreements"))
    partial_alignment: str = Field("", validation_alias=AliasChoices("partial_alignment", "partialAlignment"))
    alignment_summary: str = Field("", validation_alias=AliasChoices("alignment_summary", "alignmentSummary"))
    resources_considered: str = ""
    current_status: str = ""
    role: str = ""
    materials_reviewed: list[str] = []
    dynamic_score: int = 0
    framework_choices: dict = {}
    framework_custom: dict = {}
    level_change_note: str = ""
    status: str = "draft"


class CourtMessageIn(BaseModel):
    text: str


class SubmitIn(BaseModel):
    attest: bool = False
    include_legal_report: bool = False


SUMMARY_DISCLAIMER = ("Procedural status summary generated from authorized case-status records only. It does not draw on private parent journals, raw assessment answers, "
                      "parent-professional communications, or draft material, and it is not a legal conclusion, credibility determination, or judicial recommendation.")


def _stage_signature(ref: dict, case: dict | None, packets: list) -> str:
    st = court_stage(case) if case else {"index": 0}
    return "|".join([ref.get("status", ""), str(st.get("index", 0)), str(len((case or {}).get("court_submissions") or [])),
                     ((case or {}).get("professional_statement") or {}).get("status", "none"), ",".join(sorted(p.get("status", "") for p in packets))])


HEADLINES = {
    "declined": ("Referral declined", "Declined the referral{reason}.", "Re-referral to another professional.", "Refer the matter to another approved professional."),
    "pending": ("Awaiting professional acceptance", "Referral sent; not yet accepted.", "Professional acceptance.", "None until the professional responds; consider a follow-up if no response within 5 business days."),
    6: ("Ready for court review", "Referral accepted; documents submitted.", "Court review.", "Review the Joint Alignment Report and Professional Assessment Statement."),
    5: ("Submission pending", "Referral accepted; Professional Statement marked ready.", "Professional submission to the court.", "None; submission expected shortly."),
    3: ("Assessments complete; professional review in progress", "Referral accepted; reviewing the Joint Report.", "Professional Assessment Statement and submission.", "None; await submission."),
    0: ("In progress with the professional", "Referral accepted; case opened.", "Parent assessments and professional review.", "None; await submission."),
}


def _headline(ref: dict, idx: int) -> tuple:
    if ref.get("status") in ("declined", "pending"):
        h = HEADLINES[ref["status"]]
        reason = f": {ref['decline_reason']}" if ref.get("decline_reason") else ""
        return (h[0], h[1].format(reason=reason), h[2], h[3])
    return HEADLINES[6 if idx >= 6 else 5 if idx == 5 else 3 if idx >= 3 else 0]


def _parents_line(case: dict | None, both: bool, done: int) -> str:
    if not case:
        return "Case not yet opened."
    if both:
        return "Both parents completed the ordered assessments."
    return f"{done} of 2 parents completed the assessment." if case.get("status") != "draft" else "Parents not yet invited."


def _joint_line(case: dict | None, idx: int, both: bool, done: int) -> str:
    if idx >= 5:
        return "100% complete and professionally reviewed."
    if idx == 4:
        return "Complete; under professional review."
    if both:
        return "Complete; report pending professional review."
    return f"{done * 50}% complete." if case else "Not started."


def _statement_line(stmt: dict, subs: list) -> str:
    if subs:
        return f"Submitted (version {subs[-1]['version']}, {subs[-1]['submitted_at'][:10]})."
    return "Ready; not yet submitted." if stmt.get("status") == "ready" else "In draft." if stmt else "Not started."


def _communication_line(ref: dict, subs: list, latest_resp: dict | None) -> str:
    if subs:
        comm = f"Final reports submitted to the court portal on {subs[-1]['submitted_at'][:10]}."
        if latest_resp:
            comm += f" Court {'acknowledged receipt' if latest_resp['kind'] == 'acknowledged' else 'requested clarification'} on {latest_resp['at'][:10]}."
        return comm
    if ref.get("responded_at"):
        return f"Professional {ref['status']} the referral on {ref['responded_at'][:10]}."
    return f"Referral sent on {ref.get('created_at', '')[:10]}."


def build_status_summary(ref: dict, case: dict | None, packets: list) -> dict:
    """Rule-based, court-facing snapshot. Uses only stage/audit facts the court is authorized to see."""
    stage = court_stage(case) if case else {"index": 0, "label": STAGES[0]}
    idx = stage["index"]
    responses = (case or {}).get("responses", {})
    done = sum(1 for k in ("a", "b") if responses.get(k))
    both = done == 2
    stmt = (case or {}).get("professional_statement") or {}
    subs = (case or {}).get("court_submissions") or []
    latest_resp = max((x for p in packets for x in p.get("responses") or []), key=lambda x: x.get("at", ""), default=None)
    current, prof, outstanding, nxt = _headline(ref, idx)
    return {"current_status": current, "professional": prof, "parents": _parents_line(case, both, done), "joint_assessment": _joint_line(case, idx, both, done),
            "professional_statement": _statement_line(stmt, subs), "recent_communication": _communication_line(ref, subs, latest_resp),
            "outstanding": outstanding, "next_action": nxt, "stage_label": stage["label"],
            "generated_at": _iso(_now()), "signature": _stage_signature(ref, case, packets), "disclaimer": SUMMARY_DISCLAIMER}


def hearing_overdue(x: dict, today: date | None = None) -> bool:
    """True when the hearing is within 7 days (or past) and the referral has not been submitted."""
    hd = x.get("hearing_date")
    if not hd or x.get("status") not in ("pending", "accepted"):
        return False
    try:
        return (date.fromisoformat(hd) - (today or _now().date())).days <= 7
    except ValueError:
        return False


BANNED_STATEMENT_RE = re.compile(r"\b(should (be awarded|have|get) (sole|primary|joint) (custody|conservatorship)|award(ed)? custody|recommend(s|ed)? (sole|primary) (custody|conservatorship))\b", re.I)


def validated_statement(body: StatementIn, doc: dict, library: dict | None = None) -> dict:
    """Normalize + validate a Professional Statement payload; blocks custody recommendations."""
    status = body.status if body.status in ("draft", "ready") else "draft"
    st = {k: getattr(body, k).strip()[:5000] for k in STATEMENT_FIELDS}
    st["role"] = body.role.strip()[:80]
    st["materials_reviewed"] = [m for m in body.materials_reviewed if m in STATEMENT_MATERIALS][:20]
    if body.dynamic_score:
        findings = joint_findings(doc)
        st["dynamic_score"] = max(1, min(10, int(body.dynamic_score)))
        st["framework_choices"] = {k: [str(x) for x in v][:50] for k, v in body.framework_choices.items() if isinstance(v, list)}
        st["framework_custom"] = {k: [str(x).strip()[:300] for x in v if str(x).strip()][:10] for k, v in body.framework_custom.items() if isinstance(v, list)}
        st["framework"] = framework_block(st["dynamic_score"], st["framework_choices"], st["framework_custom"], (findings or {}).get("subject_options"), library)
    st["level_change_note"] = body.level_change_note.strip()[:300]
    prev = (doc.get("court_submissions") or [{}])[-1].get("level_score")
    st["level_changed_from"] = prev if prev and st.get("dynamic_score") and prev != st["dynamic_score"] else None
    if status == "ready" and st["level_changed_from"] and not st["level_change_note"]:
        raise HTTPException(status_code=400, detail=f"The Ability Level changed from {prev} to {st['dynamic_score']} since the last submission. Add a neutral one-line reason for the court.")
    if status == "ready" and not all(st[k] for k in ("role_basis", "process_summary", "observations", "next_steps")):
        raise HTTPException(status_code=400, detail="Complete role, process, observations and next steps before marking the statement ready")
    if BANNED_STATEMENT_RE.search(" ".join(st[k] for k in STATEMENT_FIELDS) + " " + st["level_change_note"]):
        raise HTTPException(status_code=400, detail="The statement must not recommend custody or conservatorship outcomes. Please rephrase as facilitation observations.")
    st.update({"status": status, "updated_at": _iso(_now()), "version": ((doc.get("professional_statement") or {}).get("version") or 0) + 1})
    return st


def assert_submittable(doc: dict, body: SubmitIn) -> dict:
    """Preconditions for a frozen court submission; returns the court block."""
    court = doc.get("court") or {}
    if not court.get("judge_email"):
        raise HTTPException(status_code=400, detail="This case was not referred by a court. Use Court Packets to send it to a judge directly.")
    if not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Both parents must complete their assessments first")
    if (doc.get("professional_statement") or {}).get("status") != "ready":
        raise HTTPException(status_code=400, detail="Mark the Professional Statement ready before submitting")
    if not body.attest:
        raise HTTPException(status_code=400, detail="Please attest before submitting to the court")
    return court


def _case_checklist(x: dict, stage: dict, done: list) -> list[dict]:
    idx = stage["index"]
    items = [("Court referral sent", True), ("Professional accepted", x["status"] in ("accepted", "submitted")), ("Parents invited", idx >= 2),
             ("Parent A completed assessment", done[0]), ("Parent B completed assessment", done[1]), ("Joint Report generated", idx >= 4),
             ("Professional Statement ready", idx >= 5), ("Submitted to court", idx >= 6)]
    return [{"label": label, "done": ok} for label, ok in items]


def _court_report_view(case: dict, packet: dict) -> dict:
    """Neutral, court-facing organization of a submitted Joint Report (no per-parent text)."""
    rep = generate_joint_report(case)
    return {"key": case.get("subject"), "label": case.get("subject_label"), "case_code": case.get("case_code"), "version": packet["submission_version"], "packet_id": packet["id"],
            "alignment": rep.get("alignment_statements") or [],
            "differences": [f"Parents expressed different perspectives regarding {d.get('area', '').lower()}." for d in (rep.get("differences") or []) if isinstance(d, dict)],
            "child_focused": rep.get("child_needs") or []}


def _submitted_material(case: dict | None, packets: list, done: list) -> tuple[list, dict | None, dict | None]:
    if case and packets:
        report = _court_report_view(case, packets[0])
        counts = {"alignment_areas": len(report["alignment"]), "discussion_areas": len(report["differences"]), "completion_pct": 100}
        statement = {**(packets[0].get("statement") or {}), "professional_name": packets[0].get("professional_name"), "submitted_at": packets[0].get("created_at"), "packet_id": packets[0]["id"],
                     "legal_report_included": packets[0].get("legal_report_included", False), "legal_version": packets[0].get("legal_version"), "legal_sha256": packets[0].get("legal_sha256", "")}
        return [report], counts, statement
    if case:
        return [], {"alignment_areas": None, "discussion_areas": None, "completion_pct": int(sum(done) / 2 * 100)}, None
    return [], None, None


def judicial_case_payload(x: dict, case: dict | None, packets: list, referral_public) -> dict:
    """Judicial case view: procedural status, authorized (submitted) reports and statement only. Never raw parent answers."""
    stage = court_stage(case) if case else {"index": 0, "label": STAGES[0], "steps": STAGES}
    responses = (case or {}).get("responses", {})
    done = [bool(responses.get("a")), bool(responses.get("b"))]
    reports, counts, statement = _submitted_material(case, packets, done)
    return {"referral": referral_public(x), "case_code": x.get("case_code") or (case or {}).get("case_code"), "stage": stage, "checklist": _case_checklist(x, stage, done),
            "parents_invited": 2 if case else 0, "parents_participating": sum(done), "status_summary": x.get("status_summary"), "counts": counts,
            "reports": reports, "statement": statement, "level_history": level_history(packets),
            "submissions": [{"version": p["submission_version"], "packet_id": p["id"], "at": p["created_at"], "sha256": p.get("sha256"), "superseded": p.get("superseded", False)} for p in packets],
            "communication_summary": x.get("communication_summary"), "disclaimer": SUMMARY_DISCLAIMER}


@dataclass(frozen=True)
class Ctx:
    """Dependencies shared by every court route factory (replaces 8 positional arguments)."""
    db: object
    get_current_user: object
    app_url: object
    send_email: object
    email_from_name: str
    logger: object
    log_report_event: object
    h: dict = field(default_factory=dict)


async def _load_judge_referral(db, ref_id: str, user: dict) -> dict:
    x = await db.court_referrals.find_one({"id": ref_id, "judge_id": user["_id"]}, {"_id": 0})
    if not x:
        raise HTTPException(status_code=404, detail="Referral not found")
    return x


async def _case_and_packets(db, x: dict, submitted_only: bool = False) -> tuple[dict | None, list]:
    if not x.get("case_id"):
        return None, []
    case = await db.joint_reports.find_one({"id": x["case_id"]}, {"_id": 0})
    if submitted_only:
        packets = await db.court_packets.find({"report_id": x["case_id"], "submission_version": {"$exists": True}}, {"_id": 0, "token_hash": 0, "code_hash": 0, "sessions": 0}).sort("submission_version", -1).to_list(50)
    else:
        packets = await db.court_packets.find({"report_id": x["case_id"]}, {"_id": 0, "responses": 1, "status": 1}).to_list(50)
    return case, packets


def _judge_row(x: dict, case: dict | None, packets: list, referral_public) -> dict:
    """One row of the Judicial Dashboard table."""
    stage = court_stage(case) if case else {"index": 0, "label": "Declined" if x["status"] == "declined" else STAGES[0], "steps": STAGES}
    item = {**referral_public(x), "stage": stage}
    if case:
        item.update({"case_code": case.get("case_code"), "submissions": len(case.get("court_submissions") or []),
                     "parents_done": sum(1 for k in ("a", "b") if case.get("responses", {}).get(k)),
                     "statement_status": (case.get("professional_statement") or {}).get("status")})
    saved = x.get("status_summary")
    item["status_summary"] = {**saved, "outdated": saved.get("signature") != _stage_signature(x, case, packets)} if saved else None
    return item


async def _court_event(db, case_id: str | None, action: str, user: dict, at: str | None = None) -> None:
    if case_id:
        await db.access_events.insert_one({"report_id": case_id, "kind": "court", "action": action, "at": at or _iso(_now()), "by": user["_id"], "by_name": user.get("name", ""), "by_role": "Court"})


async def _email_hearing_set(c: "Ctx", x: dict, user: dict, hd: str) -> None:
    pro = await c.db.users.find_one({"_id": x["professional_id"]}, {"name": 1, "email": 1})
    if not (pro and pro.get("email") and hd):
        return
    try:
        await c.send_email(to=pro["email"], case_id=x.get("case_id") or x["id"], kind="hearing_date", to_role="Professional", subject=f"Hearing date set - Cause No. {x['cause_number']}",
                           html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                 f"<p>Hi {escape(pro.get('name', ''))},</p><p>{escape(user.get('name', 'The court'))} has set the hearing for Cause No. {escape(x['cause_number'])} on <strong>{hd}</strong>. "
                                 "Align will remind you one week before if the Joint Report and Professional Statement have not yet been submitted.</p>"
                                 f'<p><a href="{c.app_url()}/dashboard#court-referrals" style="color:#5B2A86">Open Court-Referred Cases</a></p>'
                                 f'<p style="font-size:12px;color:#888">Sent by {escape(c.email_from_name)}.</p></td></tr></table>'))
    except Exception as exc:
        c.logger.warning("hearing date email failed: %s", exc)


def _shared(db, get_current_user, app_url, send_email, email_from_name, logger, log_report_event) -> dict:
    """Helpers shared by the judge and professional route groups."""

    def referral_public(x: dict) -> dict:
        out = {k: x.get(k) for k in ("id", "judge_name", "judge_email", "court_name", "cause_number", "subject", "child_initials", "parent_a_name", "parent_a_email",
                                     "parent_b_name", "parent_b_email", "note", "professional_id", "professional_name", "status", "decline_reason", "case_id", "created_at", "responded_at", "hearing_date", "case_code", "communication_summary")}
        out["overdue"] = hearing_overdue(x)
        out["requested_reports"] = [{"key": k, "label": REPORT_TYPES[k][0], "subjects": REPORT_TYPES[k][1]} for k in (x.get("requested_reports") or []) if k in REPORT_TYPES]
        return out

    async def require_judge(user: dict) -> None:
        if user.get("role") != "judge":
            raise HTTPException(status_code=403, detail="Court accounts only")
        if not user.get("approved"):
            raise HTTPException(status_code=403, detail="Your court account is awaiting SA CoParents approval")

    def require_pro(user: dict) -> None:
        if user.get("role") not in ("professional", "admin") or not user.get("approved", True):
            raise HTTPException(status_code=403, detail="Approved professional accounts only")

    async def pro_profile(pid: str) -> dict:
        u = await db.users.find_one({"_id": pid}, {"name": 1, "email": 1, "profile": 1, "verification_level": 1}) or {}
        prof = u.get("profile") or {}
        return {"name": u.get("name", ""), "email": u.get("email", ""), "credentials_verified": u.get("verification_level") == "credentials_verified",
                **{k: prof.get(k, "") for k in ("pro_role", "organization", "license_number", "phone", "city", "state")}}

    return {'referral_public': referral_public, 'require_judge': require_judge, 'require_pro': require_pro, 'pro_profile': pro_profile}


def _judge_routes(c: Ctx) -> APIRouter:
    db, get_current_user, app_url, send_email, email_from_name, logger, h = c.db, c.get_current_user, c.app_url, c.send_email, c.email_from_name, c.logger, c.h
    r = APIRouter()
    referral_public, require_judge = h["referral_public"], h["require_judge"]
    # ---------- judge: refer ----------

    @r.get("/court-dashboard/professionals")
    async def referable_professionals(user=Depends(get_current_user)):
        await require_judge(user)
        docs = await db.users.find({"role": {"$in": ["professional", "admin"]}, "approved": True, "profile.accept_court_referrals": {"$ne": False}},
                                   {"name": 1, "profile": 1, "verification_level": 1}).sort("name", 1).to_list(500)
        return [{"id": d["_id"], "name": d.get("name", ""), "pro_role": (d.get("profile") or {}).get("pro_role", ""), "organization": (d.get("profile") or {}).get("organization", ""),
                 "city": (d.get("profile") or {}).get("city", ""), "state": (d.get("profile") or {}).get("state", ""), "credentials_verified": d.get("verification_level") == "credentials_verified"} for d in docs]

    @r.post("/court-dashboard/referrals")
    async def create_referral(body: ReferralIn, user=Depends(get_current_user)):
        await require_judge(user)
        pro = await db.users.find_one({"_id": body.professional_id, "approved": True, "role": {"$in": ["professional", "admin"]}}, {"name": 1, "email": 1})
        if not pro:
            raise HTTPException(status_code=404, detail="Professional not found or not approved")
        if not body.cause_number.strip():
            raise HTTPException(status_code=400, detail="Cause number is required")
        now = _now()
        ref = {"id": str(uuid.uuid4()), "judge_id": user["_id"], "judge_name": user.get("name", ""), "judge_email": user["email"].lower(),
               "court_name": body.court_name.strip()[:160] or (user.get("profile") or {}).get("organization", ""), "cause_number": body.cause_number.strip()[:80],
               "subject": body.subject or "communication", "child_initials": body.child_initials.strip()[:10], "parent_a_name": body.parent_a_name.strip()[:120],
               "parent_a_email": body.parent_a_email.strip().lower()[:200], "parent_b_name": body.parent_b_name.strip()[:120], "parent_b_email": body.parent_b_email.strip().lower()[:200],
               "note": body.note.strip()[:2000], "hearing_date": _valid_date(body.hearing_date), "requested_reports": _valid_reports(body.requested_reports), "professional_id": pro["_id"], "professional_name": pro.get("name", ""), "status": "pending", "created_at": _iso(now),
               "case_code": new_case_code(next((REPORT_TYPES[k][1][0] for k in _valid_reports(body.requested_reports) if REPORT_TYPES[k][1]), "co_parenting"))}
        await db.court_referrals.insert_one(ref)
        try:
            await send_email(to=pro["email"], case_id=ref["id"], kind="court_referral", to_role="Professional", subject=f"Court referral from {user.get('name', 'the court')} - Cause No. {ref['cause_number']}",
                             html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                   f"<p>Hi {escape(pro.get('name', ''))},</p><p><strong>{escape(ref['judge_name'])}</strong> ({escape(ref['court_name'] or 'court')}) has referred a co-parenting matter to you "
                                   f"(Cause No. {escape(ref['cause_number'])}). Accept it in your dashboard to invite both parents; the Joint Report and your Professional Statement return to the court through Align.</p>"
                                   f'<p><a href="{app_url()}/dashboard" style="color:#5B2A86">Open Court Referrals</a></p>'
                                   f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'))
        except Exception as exc:
            logger.warning("referral email failed: %s", exc)
        return referral_public(ref)

    return r


def _judge_case_routes(c: Ctx) -> APIRouter:
    """Judge: list referrals, judicial case view, AI status summary, hearing date."""
    r, db, get_current_user = APIRouter(), c.db, c.get_current_user
    referral_public, require_judge = c.h["referral_public"], c.h["require_judge"]

    @r.get("/court-dashboard/referrals")
    async def judge_referrals(user=Depends(get_current_user)):
        await require_judge(user)
        refs = await db.court_referrals.find({"judge_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(300)
        return [_judge_row(x, *await _case_and_packets(db, x), referral_public) for x in refs]

    @r.post("/court-dashboard/referrals/{ref_id}/refresh-summary")
    async def refresh_summary(ref_id: str, user=Depends(get_current_user)):
        await require_judge(user)
        x = await _load_judge_referral(db, ref_id, user)
        case, packets = await _case_and_packets(db, x)
        summary = build_status_summary(x, case, packets)
        await db.court_referrals.update_one({"id": ref_id}, {"$set": {"status_summary": summary}})
        await _court_event(db, x.get("case_id"), f"Court status summary refreshed by {user.get('name', '')}", user, summary["generated_at"])
        return {**summary, "outdated": False}

    @r.get("/court-dashboard/cases/{ref_id}")
    async def judge_case(ref_id: str, user=Depends(get_current_user)):
        await require_judge(user)
        x = await _load_judge_referral(db, ref_id, user)
        case, packets = await _case_and_packets(db, x, submitted_only=True)
        return judicial_case_payload(x, case, packets, referral_public)

    @r.patch("/court-dashboard/referrals/{ref_id}/hearing-date")
    async def set_hearing_date(ref_id: str, body: HearingDateIn, user=Depends(get_current_user)):
        await require_judge(user)
        x = await _load_judge_referral(db, ref_id, user)
        hd = _valid_date(body.hearing_date)
        await db.court_referrals.update_one({"id": ref_id}, {"$set": {"hearing_date": hd}, "$unset": {"hearing_reminder_sent": ""}})
        await _court_event(db, x.get("case_id"), f"Hearing date {'set to ' + hd if hd else 'cleared'} by {user.get('name', '')}", user)
        await _email_hearing_set(c, x, user, hd)
        return {"ok": True, "hearing_date": hd}

    return r


async def run_hearing_reminders(db, send_email, app_url, email_from_name, logger, today: date | None = None) -> int:
    """Email professional + judge 7 days before a hearing when the referral is not yet submitted."""
    today = today or _now().date()
    cutoff = (today + timedelta(days=7)).isoformat()
    refs = await db.court_referrals.find({"hearing_date": {"$gt": "", "$lte": cutoff, "$gte": today.isoformat()}, "status": {"$in": ["pending", "accepted"]},
                                          "hearing_reminder_sent": {"$in": [None]}}, {"_id": 0}).to_list(500)
    sent = 0
    for x in refs:
        pro = await db.users.find_one({"_id": x["professional_id"]}, {"name": 1, "email": 1}) or {}
        days = (date.fromisoformat(x["hearing_date"]) - today).days
        cause = escape(x["cause_number"])
        foot = f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'
        head = '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        try:
            if pro.get("email"):
                await send_email(to=pro["email"], case_id=x.get("case_id") or x["id"], kind="hearing_reminder", to_role="Professional", subject=f"Hearing in {days} days - Cause No. {x['cause_number']} not yet submitted",
                                 html=(head + f"<p>Hi {escape(pro.get('name', ''))},</p><p>The hearing for Cause No. {cause} ({escape(x.get('court_name') or 'court')}) is on <strong>{x['hearing_date']}</strong>. "
                                       "The Joint Alignment Report and Professional Assessment Statement have not yet been submitted to the court.</p>"
                                       f'<p><a href="{app_url()}/dashboard#court-referrals" style="color:#5B2A86">Open Court-Referred Cases</a></p>' + foot))
            await send_email(to=x["judge_email"], case_id=x.get("case_id") or x["id"], kind="hearing_reminder", to_role="Court", subject=f"Hearing in {days} days - Cause No. {x['cause_number']} awaiting submission",
                             html=(head + f"<p>Your Honor,</p><p>The hearing for Cause No. {cause} is on <strong>{x['hearing_date']}</strong>. The referred professional, {escape(x.get('professional_name', ''))}, "
                                   "has not yet submitted the Joint Alignment Report and Professional Assessment Statement. The professional has been reminded as well.</p>"
                                   f'<p><a href="{app_url()}/court-dashboard" style="color:#5B2A86">Open Court Dashboard</a></p>' + foot))
        except Exception as exc:
            logger.warning("hearing reminder failed for %s: %s", x["id"], exc)
            continue
        now = _iso(_now())
        await db.court_referrals.update_one({"id": x["id"]}, {"$set": {"hearing_reminder_sent": now}})
        if x.get("case_id"):
            await db.access_events.insert_one({"report_id": x["case_id"], "kind": "lifecycle", "action": f"Hearing reminder emailed (hearing {x['hearing_date']})",
                                               "at": now, "by": "system", "by_name": "SA CoParents Align", "by_role": "System"})
        sent += 1
    return sent


def _pro_routes(c: Ctx) -> APIRouter:
    db, get_current_user, app_url, send_email, logger, h = c.db, c.get_current_user, c.app_url, c.send_email, c.logger, c.h
    r = APIRouter()
    referral_public, require_pro = h['referral_public'], h['require_pro']
    # ---------- professional: referral inbox ----------

    @r.get("/professional/court-referrals")
    async def pro_referrals(user=Depends(get_current_user)):
        require_pro(user)
        refs = await db.court_referrals.find({"professional_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return [referral_public(x) for x in refs]

    @r.get("/professional/court-referrals/{ref_id}")
    async def pro_referral(ref_id: str, user=Depends(get_current_user)):
        require_pro(user)
        x = await db.court_referrals.find_one({"id": ref_id, "professional_id": user["_id"]}, {"_id": 0})
        if not x:
            raise HTTPException(status_code=404, detail="Referral not found")
        return referral_public(x)

    @r.post("/professional/court-referrals/{ref_id}/accept")
    async def accept_referral(ref_id: str, user=Depends(get_current_user)):
        require_pro(user)
        x = await db.court_referrals.find_one({"id": ref_id, "professional_id": user["_id"], "status": "pending"}, {"_id": 0})
        if not x:
            raise HTTPException(status_code=404, detail="Pending referral not found")
        await db.court_referrals.update_one({"id": ref_id}, {"$set": {"status": "accepted", "responded_at": _iso(_now())}})
        return {**referral_public(x), "status": "accepted", "next": f"/joint/new?referral={ref_id}"}

    @r.post("/professional/court-referrals/{ref_id}/decline")
    async def decline_referral(ref_id: str, body: DeclineIn, user=Depends(get_current_user)):
        require_pro(user)
        x = await db.court_referrals.find_one({"id": ref_id, "professional_id": user["_id"], "status": "pending"}, {"_id": 0})
        if not x:
            raise HTTPException(status_code=404, detail="Pending referral not found")
        reason = body.reason.strip()[:500]
        if not reason:
            raise HTTPException(status_code=400, detail="Please give the court a brief reason")
        await db.court_referrals.update_one({"id": ref_id}, {"$set": {"status": "declined", "decline_reason": reason, "responded_at": _iso(_now())}})
        try:
            await send_email(to=x["judge_email"], case_id=x["id"], kind="court_referral_declined", to_role="Court", subject=f"Referral declined - Cause No. {x['cause_number']}",
                             html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                   f"<p>Your Honor,</p><p>{escape(user.get('name', ''))} is unable to accept the referral for Cause No. {escape(x['cause_number'])}.</p>"
                                   f"<blockquote style=\"border-left:3px solid #5B2A86;padding-left:12px;color:#444\">{escape(reason)}</blockquote>"
                                   f'<p><a href="{app_url()}/court-dashboard" style="color:#5B2A86">Refer to another professional</a></p></td></tr></table>'))
        except Exception as exc:
            logger.warning("decline email failed: %s", exc)
        return {"ok": True}

    return r


def _pro_statement_routes(c: Ctx) -> APIRouter:
    """Professional: Professional Assessment Statement + frozen submission to court."""
    db, get_current_user, app_url, send_email, email_from_name, logger, log_report_event, h = c.db, c.get_current_user, c.app_url, c.send_email, c.email_from_name, c.logger, c.log_report_event, c.h
    r = APIRouter()
    require_pro, pro_profile = h['require_pro'], h['pro_profile']

    async def own_case(rid: str, user: dict) -> dict:
        doc = await db.joint_reports.find_one({"id": rid, "professional_id": user["_id"]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Case not found")
        return doc

    # ---------- professional statement ----------

    def org_key(user: dict) -> str:
        return ((user.get("profile") or {}).get("organization") or "").strip().lower()

    async def org_library(user: dict) -> dict:
        key = org_key(user)
        d = await db.org_libraries.find_one({"key": key}, {"_id": 0}) if key else None
        return clean_library((d or {}).get("library") or {})

    async def effective_library(user: dict) -> dict:
        own, org = clean_library(user.get("resource_library") or {}), await org_library(user)
        return {k: list(dict.fromkeys(own[k] + org[k])) for k in own}

    @r.get("/me/resource-library")
    async def get_library(user=Depends(get_current_user)):
        require_pro(user)
        return {**clean_library(user.get("resource_library") or {}), "organization": (user.get("profile") or {}).get("organization") or "", "org_library": await org_library(user)}

    @r.put("/me/resource-library")
    async def put_library(body: dict, user=Depends(get_current_user)):
        require_pro(user)
        lib = clean_library(body)
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"resource_library": lib}})
        return lib

    @r.put("/org/resource-library")
    async def put_org_library(body: dict, user=Depends(get_current_user)):
        require_pro(user)
        key = org_key(user)
        if not key:
            raise HTTPException(status_code=400, detail="Add an organization to your professional profile to share a library")
        lib = clean_library(body)
        await db.org_libraries.update_one({"key": key}, {"$set": {"key": key, "name": (user.get("profile") or {}).get("organization"), "library": lib, "updated_by": user.get("name", ""), "updated_at": _iso(_now())}}, upsert=True)
        return lib

    @r.get("/joint/reports/{rid}/professional-statement")
    async def get_statement(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        findings = joint_findings(doc)
        lens = await db.professional_reports.find_one({"case_id": rid}, {"_id": 0, "status": 1, "signature_name": 1})
        return {"statement": doc.get("professional_statement") or {k: "" for k in STATEMENT_FIELDS} | {"status": "draft", "role": "", "materials_reviewed": []}, "attestation_text": STATEMENT_ATTESTATION,
                "legal_lens": {"status": (lens or {}).get("status", "not_started"), "signature_name": (lens or {}).get("signature_name", "")},
                "roles": STATEMENT_ROLES, "materials": STATEMENT_MATERIALS, "suggested_score": suggested_score(doc), "tiers": [tier_for(t["range"][0]) for t in TIERS.values()],
                "findings": findings, "subject_options": (findings or {}).get("subject_options") or [], "library": clean_library(user.get("resource_library") or {}),
                "org_library": await org_library(user), "organization": (user.get("profile") or {}).get("organization") or "",
                "court": doc.get("court"), "stage": court_stage(doc), "submissions": doc.get("court_submissions") or []}

    @r.put("/joint/reports/{rid}/professional-statement")
    async def save_statement(rid: str, body: StatementIn, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        st = {**validated_statement(body, doc, await effective_library(user)), "updated_by": user.get("name", "")}
        status = st["status"]
        await db.joint_reports.update_one({"id": rid}, {"$set": {"professional_statement": st}})
        await log_report_event(rid, f"Professional Statement {'marked ready' if status == 'ready' else 'draft saved'} (v{st['version']})", user)
        return {"statement": st, "stage": court_stage({**doc, "professional_statement": st})}

    async def legal_pdf_bytes(doc: dict) -> bytes:
        """Finalized Legal Lens Review and Report to Court PDF for attachment to a frozen court submission."""
        from legal_lens import classify_individual, classify_joint, readiness
        from pdf_report import build_legal_lens_pdf
        rep = await db.professional_reports.find_one({"case_id": doc["id"]}, {"_id": 0})
        if not rep or rep.get("status") not in ("final", "submitted_to_court"):
            raise HTTPException(status_code=400, detail="Finalize the Legal Lens Review and Report to Court before attaching it to a court submission")
        view = {"report": rep, "readiness": readiness(doc), "classification": {"parent_a": classify_individual(rep.get("parent_a_rating")), "parent_b": classify_individual(rep.get("parent_b_rating")), "joint": classify_joint(rep.get("joint_rating"))},
                "notes": {"tagline": "SA CoParents — Starting With Alignment, Ending With Agreement", "safety": "Safety findings may alter or override ordinary co-parenting, mediation, communication, or joint-process recommendations.",
                          "rating": "The rating does not automatically determine the process. Safety screening, professional judgment, court orders, and the specific needs of the child remain controlling considerations."},
                "case": {"id": doc["id"], "case_code": doc.get("case_code"), "child_name": doc.get("child_name"), "subject_label": doc.get("subject_label")}}
        await db.professional_reports.update_one({"case_id": doc["id"]}, {"$set": {"status": "submitted_to_court", "updated_at": _iso(_now())}})
        return build_legal_lens_pdf(view)


    async def statement_pdf_bytes(doc: dict) -> bytes:
        st = doc.get("professional_statement") or {}
        subs = doc.get("court_submissions") or []
        hist = [{"version": s["version"], "at": s.get("submitted_at"), "score": s.get("level_score"), "label": s.get("level_label"), "note": s.get("level_change_note"), "changed_from": s.get("level_changed_from")} for s in subs]
        return build_professional_statement_pdf({"professional": await pro_profile(doc["professional_id"]), "statement": st, "court": doc.get("court") or {}, "findings": joint_findings(doc), "level_history": hist,
                                                 "case_code": doc.get("case_code"), "subject_label": doc.get("subject_label"), "child_name": doc.get("child_name"),
                                                 "attestation_text": STATEMENT_ATTESTATION, "date": _iso(_now())[:10]})

    @r.get("/joint/reports/{rid}/professional-statement.pdf")
    async def statement_pdf(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        if not doc.get("professional_statement"):
            raise HTTPException(status_code=400, detail="Write the Professional Statement first")
        return Response(content=await statement_pdf_bytes(doc), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="professional-statement-{doc.get("case_code") or rid[:8]}.pdf"'})

    # ---------- submit to court ----------

    @r.post("/joint/reports/{rid}/submit-to-court")
    async def submit_to_court(rid: str, body: SubmitIn, user=Depends(get_current_user)):
        require_pro(user)
        doc = await own_case(rid, user)
        court = assert_submittable(doc, body)
        pro = await pro_profile(user["_id"])
        rep = generate_joint_report(doc)
        joint_pdf = build_joint_pdf({**rep, "professional": {"name": pro["name"], "credentials_verified": pro["credentials_verified"]},
                                     "verify": {"case_code": doc.get("case_code"), "url": f"{app_url()}/verify?code={doc.get('case_code')}"}})
        stmt_pdf = await statement_pdf_bytes(doc)
        legal_pdf = await legal_pdf_bytes(doc) if body.include_legal_report else None
        combined = merge_pdfs([stmt_pdf, joint_pdf] + ([legal_pdf] if legal_pdf else []))
        version = len(doc.get("court_submissions") or []) + 1
        now = _now()
        pid = str(uuid.uuid4())
        legal_meta = {"legal_report_included": bool(legal_pdf), "legal_sha256": _sha(legal_pdf) if legal_pdf else "", "legal_version": version if legal_pdf else None}
        await db.court_frozen_pdfs.insert_one({"packet_id": pid, "report_id": rid, "version": version, "pdf": Binary(combined), "sha256": _sha(combined),
                                               "joint_sha256": _sha(joint_pdf), "statement_sha256": _sha(stmt_pdf), "created_at": _iso(now), **legal_meta,
                                               **({"legal_pdf": Binary(legal_pdf)} if legal_pdf else {})})
        if version > 1:
            await db.court_packets.update_many({"report_id": rid, "submission_version": {"$exists": True}}, {"$set": {"superseded": True}})
        st = doc["professional_statement"]
        packet = {"id": pid, "report_id": rid, "professional_id": user["_id"], "professional_name": user.get("name", ""), "judge_name": court.get("judge_name", ""),
                  "judge_email": court["judge_email"], "court_name": court.get("court_name", ""), "cause_number": court.get("cause_number", ""),
                  "cover_letter": st.get("process_summary", ""), "statement": st, "report_ids": [rid], "include_session_outcome": False, "include_closing_summary": False,
                  "attestation_text": STATEMENT_ATTESTATION, "attested_at": _iso(now), "token_hash": hashlib.sha256(secrets.token_bytes(32)).hexdigest(), "code_hash": "",
                  "code_attempts": 0, "sessions": [], "status": "sent", "responses": [], "opened_count": 0, "download_count": 0, "submission_version": version,
                  "frozen": True, "sha256": _sha(combined), "created_at": _iso(now), "expires_at": _iso(now + timedelta(days=3650)), **legal_meta}
        await db.court_packets.insert_one(packet)
        sub = {"version": version, "packet_id": pid, "submitted_at": _iso(now), "submitted_by": user.get("name", ""), "sha256": _sha(combined), **legal_meta,
               "joint_sha256": _sha(joint_pdf), "statement_sha256": _sha(stmt_pdf), "statement_version": st.get("version"), "judge_name": court.get("judge_name", ""), "court_name": court.get("court_name", ""),
               "level_score": (st.get("framework") or {}).get("score"), "level_label": (st.get("framework") or {}).get("label"),
               "level_change_note": st.get("level_change_note") or "", "level_changed_from": st.get("level_changed_from")}
        await db.joint_reports.update_one({"id": rid}, {"$push": {"court_submissions": sub}, "$set": {"report_generated_at": doc.get("report_generated_at") or _iso(now)}})
        await log_report_event(rid, f"Submitted Joint Report + Professional Statement{' + Professional Legal Report' if legal_pdf else ''} to {court.get('court_name') or 'the court'} (v{version}, SHA-256 {sub['sha256'][:12]}…)", user)
        if legal_pdf:
            await log_report_event(rid, "LEGAL_REPORT_SHARED", user)
        if doc.get("court_referral_id"):
            await db.court_referrals.update_one({"id": doc["court_referral_id"]}, {"$set": {"status": "submitted", "submitted_at": _iso(now)}})
        try:
            await send_email(to=court["judge_email"], case_id=doc["id"], kind="court_submission", to_role="Court", subject=f"Submission received - Cause No. {court.get('cause_number', '')} (v{version})",
                             html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                   f"<p>Your Honor,</p><p>{escape(user.get('name', ''))} has submitted the Joint Alignment Report and Professional Assessment Statement for Cause No. {escape(court.get('cause_number', ''))}"
                                   f" (version {version}). Both documents are locked and hash-sealed; open them in your Court Dashboard.</p>"
                                   f'<p><a href="{app_url()}/court-dashboard" style="color:#5B2A86">Open the Court Dashboard</a></p>'
                                   f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'))
        except Exception as exc:
            logger.warning("submission email failed: %s", exc)
        return {"submission": sub, "stage": court_stage({**doc, "court_submissions": [sub]})}

    return r


def build_router(db, get_current_user, app_url, send_email, email_from_name, logger, log_report_event) -> APIRouter:
    h = _shared(db, get_current_user, app_url, send_email, email_from_name, logger, log_report_event)
    c = Ctx(db, get_current_user, app_url, send_email, email_from_name, logger, log_report_event, h)
    r = APIRouter()
    for factory in (_judge_routes, _judge_case_routes, _pro_routes, _pro_statement_routes):
        r.include_router(factory(c))
    from court_messages import build_router as build_messages
    r.include_router(build_messages(db, get_current_user, app_url, send_email, email_from_name, h["require_judge"], h["require_pro"]))
    return r
