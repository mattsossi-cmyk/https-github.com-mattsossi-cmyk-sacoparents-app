"""Two private safety self-assessments (Version A — women, Version B — men). Screening questions, not a diagnostic tool.

Routing: a parent's answers go only to the assigned professional — never to the co-parent, never into a report or PDF.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

LABEL = "Screening questions, not a diagnostic tool"
SCALE_NOTE = "Screening questions adapted from published sources. Not a validated or diagnostic instrument. Tiers are a design guide, not a clinical cutoff."
FREQ = ["Never", "Rarely", "Sometimes", "Frequently", "Prefer not to say"]
YN = ["Yes", "No", "Not sure", "Prefer not to say"]
SAFE = ["Very safe", "Somewhat safe", "Not safe", "Prefer not to say"]
TRIGGER_WARNING = "Content note: these questions ask about fear, control, and physical or sexual harm in a relationship. Take a break at any time; your progress is saved only when you submit."
INTRO = ("These questions are private. Your co-parent will not see your answers. Skip any you prefer not to answer. "
         "If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (or text START to 88788).")
INTRO_B = "Partner violence can happen to anyone, including men."
# TODO(verify): San Antonio Family Violence Prevention Services 210-733-8810 is UNVERIFIED — pending verification before publication.
RESOURCES = [
    {"name": "National Domestic Violence Hotline", "contact": "1-800-799-7233 · text START to 88788", "url": "https://www.thehotline.org", "verified": True},
    {"name": "Family Violence Prevention Services (San Antonio)", "contact": "210-733-8810", "url": "https://fvps.org", "verified": False},
]
# TODO(permission): Version B items are HITS-based (Velonis et al. 2021, J. Interpersonal Violence; © SAGE). Written permission from the author is pending.
SOURCES = {"A": "Adapted from the WPSI Screening for Intimate Partner and Domestic Violence in Women — Resource Guide & Clinical Workflow (9.9.25).",
           "B": "Adapted from Velonis et al. (2021), Journal of Interpersonal Violence (HITS-based, 9 items). © SAGE Publications; used with attribution, permission pending."}

_CHILD = [("c1", "Have your children seen or heard any of the above?", "yn"), ("c2", "Have you noticed changes in them (sleep problems, fear, anxiety, school trouble, acting out)?", "yn")]
_A_FREQ = [("a1", "humiliate you or emotionally abuse you?", False), ("a2", "make you feel afraid of them?", True), ("a3", "force or pressure you into sexual activity?", True),
           ("a4", "hit, kick, or otherwise physically hurt you?", True), ("a5", "control your money, phone, transportation, or who you see?", False)]
_B_FREQ = [("b2", "insult you or talk down to you?", False), ("b3", "yell, shout, or curse at you?", False), ("b4", "control who you see, where you go, what you do, or what you wear?", False),
           ("b5", "make you feel afraid or scared of them?", False), ("b6", "threaten to harm you or someone you care about?", True), ("b7", "physically hurt you?", True),
           ("b8", "beat, punch, kick, strangle, or hurt you with a weapon?", True), ("b9", "force, threaten, or pressure you to participate in any sexual activity when you didn't want to?", True)]
STEM = "Over the last 12 months, how often did your partner, an ex-partner, or someone you dated…"


def _item(i, text, kind, part, tier3=False, stem=None):
    return {"id": i, "text": text, "kind": kind, "part": part, "tier3": tier3, "stem": stem}


VERSIONS = {
    "A": {"version": "A", "title": "Safety Screening — Version A (Women)", "intro": INTRO, "source": SOURCES["A"], "items": [
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _A_FREQ],
        _item("a6", "How often do you feel you have to change what you say or do to avoid conflict with them?", "freq", "Part 1 · Your relationship"),
        *[_item(i, t, "yn", "Part 2 · Your children") for i, t, _k in _CHILD],
        _item("a9", "What makes it hard to stay safe or get help (money, fear of losing custody, immigration status, lack of support)?", "text", "Part 3 · Optional"),
        _item("safe", "How safe is it for you to go home today?", "safe", "Closing")]},
    "B": {"version": "B", "title": "Safety Screening — Version B (Men)", "intro": f"{INTRO} {INTRO_B}", "source": SOURCES["B"], "items": [
        _item("b1", "Over the last 12 months, how often did you feel uncomfortable doing or saying things around your current partner or someone you're currently dating?", "freq", "Part 1 · Your relationship"),
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _B_FREQ],
        *[_item(i, t, "yn", "Part 2 · Your children") for i, t, _k in _CHILD],
        _item("c3", "Do you worry about losing contact with your children if you ask for help?", "yn", "Part 2 · Your children"),
        _item("safe", "How safe do you feel going home today?", "safe", "Closing")]},
}
TIER_LABEL = {1: "Tier 1 — resources only", 2: "Tier 2 — review resources; professional follow-up suggested", 3: "Tier 3 — professional follow-up recommended"}
VERSION_LABEL = {"A": "Version A (women)", "B": "Version B (men)"}
GENDER_DEFAULT = {"woman": "A", "female": "A", "f": "A", "man": "B", "male": "B", "m": "B"}


def public_spec(version: str) -> dict:
    v = VERSIONS[version]
    return {**v, "label": LABEL, "trigger_warning": TRIGGER_WARNING, "scale_note": SCALE_NOTE, "scales": {"freq": FREQ, "yn": YN, "safe": SAFE}, "resources": RESOURCES}


def compute_tier(version: str, responses: dict) -> int:
    """Design guide, not a validated cutoff. Skipped / 'Prefer not to say' items never raise the tier."""
    items = VERSIONS[version]["items"]
    freq = {i["id"]: (responses.get(i["id"]) or "") for i in items if i["kind"] == "freq"}
    safe = responses.get("safe") or ""
    high = {k for k, v in freq.items() if v in ("Sometimes", "Frequently")}
    above_never = {k for k, v in freq.items() if v in ("Rarely", "Sometimes", "Frequently")}
    tier3_ids = {i["id"] for i in items if i.get("tier3")}
    if safe == "Not safe" or (high & tier3_ids):
        return 3
    if high or (safe == "Somewhat safe" and above_never):
        return 2
    return 1


def default_version(gender: str | None) -> str | None:
    return GENDER_DEFAULT.get((gender or "").strip().lower())


def build_record(version: str, responses: dict, source: str = "sacoparentsalign.com", completed_at: str | None = None, tier: int | None = None, answered_count: int | None = None) -> dict:
    items = VERSIONS[version]["items"]
    clean = {i["id"]: str(responses[i["id"]])[:1000].strip() for i in items if responses.get(i["id"]) not in (None, "")}
    skipped = [i["id"] for i in items if i["id"] not in clean or clean[i["id"]] == "Prefer not to say"]
    t = tier if tier in (1, 2, 3) else compute_tier(version, clean)
    concern = sum(1 for i in items if i["kind"] == "freq" and clean.get(i["id"]) in ("Sometimes", "Frequently")) + (1 if clean.get("safe") == "Not safe" else 0)
    return {"source": source, "version": version, "title": VERSIONS[version]["title"], "completed_at": completed_at or datetime.now(timezone.utc).isoformat(), "tier": t,
            "answered_count": answered_count if isinstance(answered_count, int) else len([k for k in clean if clean[k] != "Prefer not to say"]), "skipped_count": len(skipped),
            "item_count": len(items), "concern_count": concern, "responses": clean}


def receipt(scr: dict | None, parent_label: str) -> str:
    """Court-safe line: receipt, version, tier, date. Never answer text."""
    if not scr:
        return f"{parent_label}: safety screening — Not Received."
    ver = VERSION_LABEL.get(scr.get("version") or "", "legacy format")
    date = str(scr.get("completed_at") or "")[:10]
    tier = TIER_LABEL.get(scr.get("tier"), "Tier not available (legacy format)")
    return f"{parent_label}: safety screening — Received ({ver}, {scr.get('source') or 'sacoparentsalign.com'}){f', completed {date}' if date else ''}. {tier}."


def item_view(scr: dict) -> list[dict]:
    """Professional-only item-level view (access must be logged by the caller)."""
    ver = scr.get("version")
    if ver not in VERSIONS:
        return [{"id": k, "question": k, "answer": v, "kind": "text"} for k, v in (scr.get("responses") or {}).items()] or [{"id": it.get("question"), "question": it.get("question"), "answer": it.get("answer"), "kind": "text"} for it in scr.get("items") or []]
    r = scr.get("responses") or {}
    return [{"id": i["id"], "question": (f"{i['stem']} {i['text']}" if i.get("stem") else i["text"]), "answer": r.get(i["id"]) or "Skipped", "kind": i["kind"], "part": i["part"],
             "flag": i["kind"] == "freq" and r.get(i["id"]) in ("Sometimes", "Frequently") or (i["id"] == "safe" and r.get("safe") == "Not safe")} for i in VERSIONS[ver]["items"]]


class SubmitIn(BaseModel):
    responses: dict


class AssignIn(BaseModel):
    role: str
    version: str


def _status(doc: dict) -> dict:
    out = {}
    for r in ("a", "b"):
        p = doc["participants"][r]
        scr = ((doc.get("responses") or {}).get(r) or {}).get("safety_screening") or None
        ver = (doc.get("safety_version") or {}).get(r) or default_version(p.get("gender"))
        out[r] = {"name": p.get("name") or f"Parent {r.upper()}", "gender": p.get("gender"), "version": ver, "needs_assignment": ver is None, "received": bool(scr),
                  "tier": scr.get("tier") if scr else None, "tier_label": TIER_LABEL.get(scr.get("tier")) if scr else None, "version_label": VERSION_LABEL.get(ver or ""),
                  "completed_at": (scr or {}).get("completed_at"), "source": (scr or {}).get("source"), "receipt": receipt(scr, p.get("name") or f"Parent {r.upper()}")}
    return out


def build_router(db, get_current_user, get_joint_report_doc, report_role, log_access) -> APIRouter:
    r = APIRouter()

    def _is_pro(doc, user):
        return user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))

    @r.get("/joint/reports/{rid}/safety-screening")
    async def screening_overview(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role, pro = report_role(doc, user["_id"]), _is_pro(doc, user)
        st = _status(doc)
        if not pro:
            st = {role: st[role]} if role else {}
        spec = public_spec(st[role]["version"]) if role and st.get(role, {}).get("version") else None
        return {"my_role": role, "is_professional": pro, "roles": st, "spec": spec, "versions": VERSION_LABEL, "scale_note": SCALE_NOTE}

    @r.put("/joint/reports/{rid}/safety-screening/assign")
    async def assign_version(rid: str, body: AssignIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can assign a screening version")
        if body.role not in ("a", "b") or body.version not in VERSIONS:
            raise HTTPException(status_code=400, detail="Invalid role or version")
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_version.{body.role}": body.version}})
        return _status(await get_joint_report_doc(rid, user))

    @r.put("/joint/reports/{rid}/safety-screening")
    async def submit_screening(rid: str, body: SubmitIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents can complete a safety screening")
        version = _status(doc)[role]["version"]
        if not version:
            raise HTTPException(status_code=409, detail="Your professional has not assigned a screening version yet")
        rec = build_record(version, body.responses or {})
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"responses.{role}.safety_screening": rec, f"responses.{role}.safety_route": rec["tier"] >= 2}})
        return {"tier": rec["tier"], "tier_label": TIER_LABEL[rec["tier"]], "resources": RESOURCES, "answered_count": rec["answered_count"], "skipped_count": rec["skipped_count"], "scale_note": SCALE_NOTE}

    @r.get("/joint/reports/{rid}/safety-screening/{role}/responses")
    async def screening_responses(rid: str, role: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Item-level screening responses are visible only to the assigned professional")
        scr = ((doc.get("responses") or {}).get(role) or {}).get("safety_screening") if role in ("a", "b") else None
        if not scr:
            raise HTTPException(status_code=404, detail="No safety screening on file for this parent")
        await log_access(doc, user, f"Viewed Parent {role.upper()} safety screening responses (professional-only)", "safety_screening")
        return {"status": _status(doc)[role], "items": item_view(scr), "scale_note": SCALE_NOTE, "source_credit": SOURCES.get(scr.get("version") or "", ""),
                "notice": "Parent-reported screening responses, shown to the assigned professional only. Not findings. Never shared with the co-parent, the court, or any report."}

    return r
