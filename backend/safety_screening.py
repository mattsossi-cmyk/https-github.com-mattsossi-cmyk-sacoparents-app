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
INTRO_C = ("These questions are private. Your co-parent will not see your answers. Skip any you prefer not to answer. These questions are for people of any gender or orientation. "
           "If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (text START to 88788). LGBTQ+ support: The Network/La Red, 1-800-832-1901.")
LABEL_C = "Screening questions, not a diagnostic tool. Adapted from published guidance; not a validated instrument."
# TODO(permission): Version B items are HITS-based (Velonis et al. 2021, J. Interpersonal Violence; © SAGE). Written permission from the author is pending.
SOURCES = {"A": "Adapted from the WPSI Screening for Intimate Partner and Domestic Violence in Women — Resource Guide & Clinical Workflow (9.9.25).",
           "B": "Adapted from Velonis et al. (2021), Journal of Interpersonal Violence (HITS-based, 9 items). © SAGE Publications; used with attribution, permission pending.",
           "C": "Adapted from the Safe & Together Institute behavior/pattern-based approach and LGBTQ+ IPV screening guidance (NCAVP; The Network/La Red; LGBTQ health education sources)."}
_C_FREQ = [("c_1", "insult you, put you down, or yell at you?", False), ("c_2", "control who you see, where you go, your money, or your phone?", False), ("c_3", "make you feel afraid of them?", False),
           ("c_4", "threaten to harm you or someone you care about?", True), ("c_5", "physically hurt you?", True), ("c_6", "force or pressure you into sexual activity?", True),
           ("c_7", "isolate you from friends, family, or LGBTQ+ community?", False)]
_C_IDENTITY = [("c_8", "threaten to out you to family, friends, an employer, or others?", True), ("c_9", "threaten to use your sexual orientation, gender identity, or HIV status against you?", True),
               ("c_10", "pressure you to change or hide your gender expression, name, pronouns, or transition?", False), ("c_11", "hide, destroy, or withhold medication, hormones, or other personal items?", False),
               ("c_12", "tell you no one will believe you, or that you won't get help because of who you are?", False)]

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
    "C": {"version": "C", "title": "Safety Screening — Version C (LGBTQ+ Relationship Self-Assessment)", "intro": INTRO_C, "source": SOURCES["C"], "label": LABEL_C, "items": [
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _C_FREQ],
        *[_item(i, t, "freq", "Part 2 · Identity-based tactics", t3, STEM) for i, t, t3 in _C_IDENTITY],
        *[_item(i, t, "yn", "Part 3 · Your children") for i, t, _k in _CHILD],
        _item("c_15", "Do you worry about losing contact with your children, or how a court would view you, if you ask for help?", "yn", "Part 3 · Your children"),
        _item("safe", "How safe do you feel going home today?", "safe", "Closing")]},
}
TIER_LABEL = {1: "Tier 1 — resources only", 2: "Tier 2 — review resources; professional follow-up suggested", 3: "Tier 3 — professional follow-up recommended"}
# Report/PDF/co-parent-safe labels: never name identity. Full names live in VERSION_LABEL_PRO (professional-only screens).
VERSION_LABEL = {"A": "Version A", "B": "Version B", "C": "Version C"}
VERSION_LABEL_PRO = {"A": "Version A (women)", "B": "Version B (men)", "C": "Version C (LGBTQ+ relationship)"}
CHOICE_LABEL = {"A": "The questions for women (Version A)", "B": "The questions for men (Version B)", "C": "I'd like the LGBTQ+ relationship version (Version C)"}
GENDER_DEFAULT = {"woman": "A", "female": "A", "f": "A", "man": "B", "male": "B", "m": "B"}


def public_spec(version: str) -> dict:
    v = VERSIONS[version]
    from safety_pathway import EXTRA_ITEMS, YN3
    items = [i for i in v["items"] if i["id"] != "safe"] + EXTRA_ITEMS + [i for i in v["items"] if i["id"] == "safe"]
    return {**v, "items": items, "label": v.get("label", LABEL), "trigger_warning": TRIGGER_WARNING, "scale_note": SCALE_NOTE, "scales": {"freq": FREQ, "yn": YN, "safe": SAFE, "yn3": YN3}, "resources": RESOURCES,
            "safe_device_notice": "Use a device your co-parent cannot see. The Quick Exit button (or pressing Escape twice) leaves this page immediately and clears it from this browser."}


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


def build_record(version: str, responses: dict, source: str = "sacoparentsalign.com", completed_at: str | None = None, tier: int | None = None, answered_count: int | None = None,
                 flags: dict | None = None, pathway: str | None = None) -> dict:
    from safety_pathway import EXTRA_ITEMS, compute_flags, pathway_from_flags
    items = VERSIONS[version]["items"] + EXTRA_ITEMS
    clean = {i["id"]: str(responses[i["id"]])[:1000].strip() for i in items if responses.get(i["id"]) not in (None, "")}
    skipped = [i["id"] for i in items if i["id"] not in clean or clean[i["id"]] == "Prefer not to say"]
    t = tier if tier in (1, 2, 3) else compute_tier(version, clean)
    fl = flags if isinstance(flags, dict) else compute_flags(version, clean)
    sugg = pathway_from_flags(fl) if not pathway else {"pathway": pathway, "label": __import__("safety_pathway").LABEL[pathway], "triggered": [k for k, v in fl.items() if v], "triggered_labels": [__import__("safety_pathway").FLAG_LABEL[k] for k, v in fl.items() if v]}
    concern = sum(1 for i in items if i["kind"] == "freq" and clean.get(i["id"]) in ("Sometimes", "Frequently")) + (1 if clean.get("safe") == "Not safe" else 0)
    return {"source": source, "version": version, "title": VERSIONS[version]["title"], "completed_at": completed_at or datetime.now(timezone.utc).isoformat(), "tier": t,
            "answered_count": answered_count if isinstance(answered_count, int) else len([k for k in clean if clean[k] != "Prefer not to say"]), "skipped_count": len(skipped),
            "item_count": len(items), "concern_count": concern, "responses": clean, "flags": fl, "pathway_suggested": sugg}


def public_record(scr: dict | None) -> dict | None:
    """Report-safe projection: receipt metadata only — never responses or items."""
    if not scr:
        return None
    return {k: scr.get(k) for k in ("source", "version", "completed_at", "tier", "answered_count", "skipped_count", "item_count")}


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
             "flag": i["kind"] == "freq" and r.get(i["id"]) in ("Sometimes", "Frequently") or (i["id"] == "safe" and r.get("safe") == "Not safe") or (i["kind"] == "yn3" and r.get(i["id"]) == "Yes")}
            for i in VERSIONS[ver]["items"] + __import__("safety_pathway").EXTRA_ITEMS]


class SubmitIn(BaseModel):
    responses: dict


class AssignIn(BaseModel):
    role: str
    version: str


class ChooseIn(BaseModel):
    version: str


def _status(doc: dict) -> dict:
    out = {}
    for r in ("a", "b"):
        p = doc["participants"][r]
        scr = (doc.get("safety_screenings") or {}).get(r) or None
        ver = (doc.get("safety_version") or {}).get(r) or default_version(p.get("gender"))
        confirmed = bool((doc.get("safety_version_confirmed") or {}).get(r))
        out[r] = {"name": p.get("name") or f"Parent {r.upper()}", "gender": p.get("gender"), "version": ver, "needs_assignment": ver is None, "received": bool(scr),
                  "choice_needed": not confirmed and not scr, "default_version": ver if ver in ("A", "B") else None, "chosen_by_parent": confirmed,
                  "tier": scr.get("tier") if scr else None, "tier_label": TIER_LABEL.get(scr.get("tier")) if scr else None, "version_label": VERSION_LABEL.get(ver or ""),
                  "completed_at": (scr or {}).get("completed_at"), "source": (scr or {}).get("source"), "receipt": receipt(scr, p.get("name") or f"Parent {r.upper()}"),
                  "reminded_at": (doc.get("safety_reminded_at") or {}).get(r)}
    return out


def spec_export() -> dict:
    """Machine-readable spec for the parent app: identical wording, scales, tiering, and the import payload contract."""
    return {"schema_version": 2, "label": LABEL, "scale_note": SCALE_NOTE, "trigger_warning": TRIGGER_WARNING, "scales": {"freq": FREQ, "yn": YN, "safe": SAFE}, "resources": RESOURCES,
            "versions": {k: {"version": k, "title": v["title"], "intro": v["intro"], "label": v.get("label", LABEL), "source": v["source"],
                             "items": [{"id": i["id"], "part": i["part"], "stem": i["stem"], "text": i["text"], "kind": i["kind"], "scale": {"freq": "freq", "yn": "yn", "safe": "safe", "text": None}[i["kind"]], "tier3": i["tier3"]} for i in v["items"]]} for k, v in VERSIONS.items()},
            "tiers": {"note": "Design guide, not a validated or clinical cutoff. Skipped and 'Prefer not to say' never raise the tier.",
                      "1": "All frequency items Never/Rarely AND closing Very safe or Somewhat safe.",
                      "2": "Any frequency item Sometimes/Frequently, OR closing Somewhat safe with any frequency item above Never.",
                      "3": "Any item flagged tier3 answered Sometimes/Frequently, OR closing Not safe.",
                      "tier3_items": {k: [i["id"] for i in v["items"] if i["tier3"]] for k, v in VERSIONS.items()}},
            "additional_items": __import__("safety_pathway").EXTRA_ITEMS, "scales_extra": {"yn3": __import__("safety_pathway").YN3},
            "safety_pathway": {"flags": __import__("safety_pathway").FLAGS, "flag_map": __import__("safety_pathway").FLAG_MAP, "rules": {"protected_review": list(__import__("safety_pathway").P1), "structured": list(__import__("safety_pathway").P2)}, "labels": __import__("safety_pathway").LABEL,
                               "export_fields": {"safety_flags": "dict of the 9 booleans (optional)", "safety_pathway": "standard|structured|protected_review (optional)"}, "note": "Suggested flag only; the assigned professional confirms. Highest restriction wins across parents."},
            "assignment": {"choice_screen": "Which questions fit your situation best?", "default_by_gender": {"woman": "A", "man": "B"}, "no_gender_or_non_binary": ["A", "B", "C"], "always_offer": "C",
                           "store_only": "version letter (A|B|C) — never infer or store orientation"},
            "export_contract": {"path": "GET /api/integrations/export-assessments?email=<parent email>", "field": "safety_screening",
                                "shape": {"version": "A|B|C", "completed_at": "ISO-8601", "tier": "1|2|3 (optional; recomputed if missing)", "answered_count": "int (optional)", "responses": {"<item id>": "<scale value or free text>"}},
                                "privacy": "Reports/PDFs/co-parent views show only Received, version letter, tier, date. Raw responses go to the assigned professional only."}}


def build_router(db, get_current_user, get_joint_report_doc, report_role, log_access) -> APIRouter:
    r = APIRouter()

    async def _tier3_alert(doc: dict, role: str, rec: dict) -> None:
        """Immediate professional alert for a Tier 3 screening — receipt, version letter, tier only; never answers, never identity."""
        from core import _pro_email_wrap, app_url
        from email_utils import EMAIL_FROM_NAME, send_email
        from html import escape
        pro = await db.users.find_one({"_id": doc.get("professional_id") or doc.get("created_by"), "role": {"$in": ["professional", "admin"]}}, {"email": 1, "name": 1})
        if not pro or doc.get("is_demo"):
            return
        code = doc.get("case_code") or doc["id"][:8]
        name = escape((doc["participants"][role].get("name")) or f"Parent {role.upper()}")
        html = _pro_email_wrap(
            f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
            f"<p><strong>{name}</strong> completed a private safety screening ({VERSION_LABEL[rec['version']]}) on Case {escape(code)} and it landed at "
            f"<strong>{TIER_LABEL[3]}</strong>.</p>"
            f"<p>Only the assigned professional can open item-level responses; access is logged. The co-parent and the court see nothing of this.</p>"
            f'<p><a href="{app_url()}/joint/{doc["id"]}/safety-screening/{role}" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open screening (professional-only)</a></p>'
            f"<p style=\"color:#666;font-size:13px\">{SCALE_NOTE}</p>")
        await send_email(to=pro["email"], subject=f"Safety screening Tier 3 — Case {code} - {EMAIL_FROM_NAME}", html=html, case_id=doc["id"], kind="safety_tier3_alert", to_role="Professional")

    def _is_pro(doc, user):
        return user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))

    @r.get("/joint/reports/{rid}/safety-screening")
    async def screening_overview(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role, pro = report_role(doc, user["_id"]), _is_pro(doc, user)
        st = _status(doc)
        if pro:
            for v in st.values():
                v["version_label"] = VERSION_LABEL_PRO.get(v["version"] or "")
        else:
            st = {role: st[role]} if role else {}
        mine = st.get(role) if role else None
        spec = public_spec(mine["version"]) if mine and mine["version"] and not mine["choice_needed"] else None
        choice = None
        if mine and mine["choice_needed"]:
            choice = {"question": "Which questions fit your situation best?", "intro": INTRO, "trigger_warning": TRIGGER_WARNING,
                      "options": ([{"version": mine["default_version"], "label": CHOICE_LABEL[mine["default_version"]]}] if mine["default_version"] else [{"version": v, "label": CHOICE_LABEL[v]} for v in ("A", "B")]) + [{"version": "C", "label": CHOICE_LABEL["C"]}],
                      "note": None if mine["default_version"] else "Pick whichever set of questions fits your situation. Your professional can adjust this later."}
        return {"my_role": role, "is_professional": pro, "roles": st, "spec": spec, "choice": choice, "versions": VERSION_LABEL_PRO if pro else VERSION_LABEL, "scale_note": SCALE_NOTE}

    @r.put("/joint/reports/{rid}/safety-screening/choose")
    async def choose_version(rid: str, body: ChooseIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents can choose a screening version")
        st = _status(doc)[role]
        allowed = {"C", st["default_version"]} if st["default_version"] else set(VERSIONS)
        if body.version not in allowed:
            raise HTTPException(status_code=400, detail="Choose one of the versions offered to you")
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_version.{role}": body.version, f"safety_version_confirmed.{role}": True}})
        return {"version": body.version, "spec": public_spec(body.version)}

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
            raise HTTPException(status_code=409, detail="Please choose a screening version first")
        rec = build_record(version, body.responses or {})
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_screenings.{role}": rec, f"safety_flags.{role}": rec["tier"] >= 2}})
        if rec["tier"] == 3:
            try:
                await _tier3_alert(doc, role, rec)
            except Exception as exc:  # alert must never block the parent's submission
                import logging
                logging.getLogger("safety_screening").warning("Tier 3 alert not sent for case %s: %s", rid, exc)
        return {"tier": rec["tier"], "tier_label": TIER_LABEL[rec["tier"]], "resources": RESOURCES, "answered_count": rec["answered_count"], "skipped_count": rec["skipped_count"], "scale_note": SCALE_NOTE}

    @r.get("/joint/reports/{rid}/safety-screening/{role}/responses")
    async def screening_responses(rid: str, role: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Item-level screening responses are visible only to the assigned professional")
        scr = (doc.get("safety_screenings") or {}).get(role) if role in ("a", "b") else None
        if not scr:
            raise HTTPException(status_code=404, detail="No safety screening on file for this parent")
        await log_access(doc, user, f"Viewed Parent {role.upper()} safety screening responses (professional-only)", "safety_screening")
        st = _status(doc)[role]
        st["version_label"] = VERSION_LABEL_PRO.get(scr.get("version") or "", "legacy format")
        st["title"] = scr.get("title")
        from safety_pathway import LABEL as _PL, PATHWAYS as _PW
        decision = (doc.get("safety_pathway") or {}).get(role) or {}
        pathway = {"suggested": scr.get("pathway_suggested") or {"pathway": "standard", "label": "Standard", "triggered": [], "triggered_labels": []}, "decision": decision or None,
                   "options": [{"key": k, "label": _PL[k]} for k in _PW], "note": "Suggested flag only — nothing is restricted automatically. Confirm, change, or dismiss; only your confirmed pathway reaches the report."}
        return {"status": st, "items": item_view(scr), "pathway": pathway, "scale_note": SCALE_NOTE, "source_credit": SOURCES.get(scr.get("version") or "", ""),
                "notice": "Parent-reported screening responses, shown to the assigned professional only. Not findings. Never shared with the co-parent, the court, or any report."}

    return r


REMINDER_AFTER_DAYS = 7


async def run_screening_reminders(db, send_email, app_url, from_name: str, logger) -> int:
    """Daily: one gentle nudge per parent whose assigned (or offered) safety screening is still not received 7+ days after they joined. Neutral — no version name, no answers."""
    from datetime import timedelta
    from html import escape
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=REMINDER_AFTER_DAYS)).isoformat()
    sent = 0
    async for doc in db.joint_reports.find({"kind": {"$ne": "foundation"}, "closed_at": {"$exists": False}, "is_demo": {"$ne": True},
                                            "$or": [{"participants.a.user_id": {"$ne": None}}, {"participants.b.user_id": {"$ne": None}}]},
                                           {"_id": 0, "id": 1, "case_code": 1, "child_name": 1, "participants": 1, "safety_screenings": 1, "safety_reminded_at": 1, "created_at": 1}):
        for role in ("a", "b"):
            p = doc["participants"][role]
            if not p.get("user_id") or (doc.get("safety_screenings") or {}).get(role) or (doc.get("safety_reminded_at") or {}).get(role):
                continue
            inv = await db.invitations.find_one({"report_id": doc["id"], "role": role, "status": "accepted"}, {"accepted_at": 1})
            joined = (inv or {}).get("accepted_at") or doc.get("created_at") or ""
            if not joined or joined > cutoff:
                continue
            user = await db.users.find_one({"_id": p["user_id"]}, {"email": 1, "name": 1})
            if not user or not user.get("email"):
                continue
            code = doc.get("case_code") or doc["id"][:8]
            html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                    f"<p>Hi {escape(user.get('name') or 'there')},</p>"
                    f"<p>A short, private safety screening is still waiting for you on case <strong>{escape(code)}</strong>. It takes about five minutes. "
                    "Every question can be skipped, and your co-parent will never see your answers — only your professional can.</p>"
                    f'<p><a href="{app_url()}/joint/{doc["id"]}/safety-screening" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open my private screening</a></p>'
                    "<p style=\"color:#666;font-size:13px\">If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (text START to 88788).</p>"
                    f'<p style="font-size:12px;color:#888">Sent by {escape(from_name)}. We never ask for your password by email.</p></td></tr></table>')
            try:
                await send_email(to=user["email"], subject=f"A private screening is waiting for you — Case {code} - {from_name}", html=html, case_id=doc["id"], kind="safety_screening_reminder", to_role=f"Parent {role.upper()}")
            except Exception as exc:
                logger.warning("safety screening reminder failed for %s/%s: %s", doc["id"], role, exc)
                continue
            await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {f"safety_reminded_at.{role}": now.isoformat()}})
            sent += 1
    return sent
