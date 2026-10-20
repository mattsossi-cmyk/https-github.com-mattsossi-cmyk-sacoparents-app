"""Two private safety self-assessments (Version A — women, Version B — men). Screening questions, not a diagnostic tool.

Routing: a parent's answers go only to the assigned professional — never to the co-parent, never into a report or PDF.
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

LABEL = "Screening questions, not a diagnostic tool"
SCALE_NOTE = "Screening questions adapted from published sources. Not a validated or diagnostic instrument. Tiers are a design guide, not a clinical cutoff."
FREQ = ["Never", "Rarely", "Sometimes", "Frequently", "Prefer not to say"]
YN = ["Yes", "No", "Not sure", "Prefer not to say"]
SAFE = ["Very safe", "Somewhat safe", "Not safe", "Prefer not to say"]
TRIGGER_WARNING = "Content note: these questions ask about fear, control, and physical or sexual harm in a relationship. Take a break at any time; your progress is saved so you can come back later."
INTRO = ("These questions are private. Your co-parent will not see your answers. Skip any you prefer not to answer. "
         "If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (or text START to 88788).")
INTRO_B = "Partner violence can happen to anyone, including men."
RESOURCES = [
    {"name": "National Domestic Violence Hotline", "contact": "1-800-799-7233 · text START to 88788", "url": "https://www.thehotline.org", "verified": True},
    {"name": "Family Violence Prevention Services (San Antonio) 24-hour line", "contact": "210-733-8810", "url": "https://fvps.org", "verified": True},
]
INTRO_C = ("These questions are private. Your co-parent will not see your answers. Skip any you prefer not to answer. These questions are for people of any gender or orientation. "
           "If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (text START to 88788). LGBTQ+ support: The Network/La Red, 1-800-832-1901.")
LABEL_C = "Screening questions, not a diagnostic tool. Adapted from published guidance; not a validated instrument."
EXTERNAL_LINK_NOTE = "Opens in a new tab and leaves SA CoParents."
RESOURCES_C = [
    {"name": "The Network/La Red (LGBTQ+ partner abuse hotline)", "contact": "1-800-832-1901", "url": "https://tnlr.org", "verified": True},
    {"name": "LGBTQ+ survivor resources from the National LGBTQ Institute on IPV, including a personal safety planning tool", "contact": "", "url": "https://lgbtqipvinstitute.org/resources-for-survivors/", "verified": True, "external": True},
]
# Crisis Resources popup (owner-approved 2026-10-14). Order: 911 → 24-hour lines (+ version-specific) → daytime office with hours labelled.
CRISIS_911 = {"name": "Immediate danger", "contact": "Call 911", "tel": "911", "hours": "Now", "kind": "emergency"}
CRISIS_24H = [
    {"name": "National Domestic Violence Hotline", "contact": "1-800-799-7233 · text START to 88788", "tel": "18007997233", "hours": "24 hours", "kind": "hotline"},
    {"name": "San Antonio Family Violence Prevention Services 24-hour line", "contact": "210-733-8810", "tel": "2107338810", "hours": "24 hours", "kind": "hotline"},
]
CRISIS_B = [{"name": "VictimConnect", "contact": "1-855-484-2846 · call, text or chat", "tel": "18554842846", "hours": "24/7", "kind": "hotline"}]
CRISIS_C = [
    {"name": "The Network/La Red", "contact": "1-800-832-1901 (main)", "tel": "18008321901", "hours": "24 hours", "kind": "hotline"},
    {"name": "The Trevor Project (for young people under 25)", "contact": "1-866-488-7386 · text START to 678-678", "tel": "18664887386", "hours": "24/7", "kind": "hotline"},
]
CRISIS_BEXAR = {"name": "Bexar County Family Justice Center (San Antonio)", "contact": "210-631-0100 · 126 E. Nueva, 2nd Floor", "tel": "2106310100",
                "hours": "Open Monday to Friday, 8:00 AM to 5:00 PM; closed on county holidays. Not a 24-hour line.", "note": "Advocacy and legal help.", "kind": "office"}
CRISIS_TITLE = "Crisis Resources"
CRISIS_INTRO = "Help is available any time. Choosing a resource here does not change anything in your account."
# Full crisis box shown on the Family check-in (owner 2026-10-18): same list as the approved popup, hours labelled, FJC after the 24-hour lines.
FV_RESOURCES = [
    {"name": "National Domestic Violence Hotline", "contact": "1-800-799-7233 · text START to 88788", "hours": "24 hours", "verified": True},
    {"name": "San Antonio Family Violence Prevention Services 24-hour line", "contact": "210-733-8810", "hours": "24 hours", "verified": True},
    {"name": "Bexar County Family Justice Center", "contact": "210-631-0100 · 126 E. Nueva, 2nd Floor", "hours": "Open Monday to Friday, 8:00 AM to 5:00 PM; closed on county holidays. Not a 24-hour line.", "verified": True},
    {"name": "VictimConnect", "contact": "1-855-484-2846", "hours": "24/7", "verified": True},
    {"name": "The Network/La Red", "contact": "1-800-832-1901", "hours": "24 hours", "verified": True},
    {"name": "The Trevor Project (for young people under 25)", "contact": "1-866-488-7386 · text START to 678-678", "hours": "24/7", "verified": True},
    {"name": "Immediate danger", "contact": "Call 911", "verified": True},
]


def crisis_resources_for(version: str | None) -> dict:
    extra = CRISIS_B if version == "B" else CRISIS_C if version == "C" else []
    return {"title": CRISIS_TITLE, "intro": CRISIS_INTRO, "version": version, "items": [CRISIS_911, *CRISIS_24H, *extra, CRISIS_BEXAR]}


SAFETY_BANNER_TEXT = "Start with Safety. A private check-in is available any time."
# Owner-approved 2026-10-15. Single editable string; bump STEP_NOTICE_VERSION so every parent sees the step screen again.
STEP_NOTICE_VERSION = "2026-10-19.1"
PROFESSIONAL_ACCESS_NOTICE = """Who can see your information

Your co-parent never sees your answers. Nothing you write in the safety check-in is ever shown to them.

The professionals assigned to your case can see:
• Your individual answers, including anything you write in your own words
• Which questions you skipped (they see that you skipped, not why)
• The safe ways to contact you, if you choose to share them
• A concern level based on your answers, which helps your professional decide what support to offer
• Whether you have started, finished, or declined this step

A small number of SA CoParents administrators can also open your answers, only to check that the service is working safely.

Your answers are kept on a protected screen. Each time anyone opens it, that is recorded, and you can see who looked and when in your privacy records.

Court documents and reports show only whether this step was completed, not started, or declined. They never show your answers, what you wrote, or your concern level.

If your answers suggest a child has been abused or neglected, the professional who reads them must report it. Texas law requires anyone who suspects child abuse or neglect to report it.

Every question can be skipped, and you can stop at any time.
If you skip a question about immediate danger, physical or sexual harm, or harm to your children, your professional will be asked to check in with you."""
# Version B source switch. "cdc" (default, TEMPORARY) = CDC NISVS behavior-category adaptation.
# "velonis" = HITS-based items (Velonis et al. 2021, J. Interpersonal Violence; © SAGE) — kept, switched OFF until written permission is obtained.
VERSION_B_SOURCE = os.environ.get("VERSION_B_SOURCE", "cdc")
SOURCES_B = {"cdc": "Adapted from the CDC National Intimate Partner and Sexual Violence Survey (NISVS) behavior categories. Screening questions, not a diagnostic tool; not a validated instrument. Temporary version.",
             "velonis": "Adapted from Velonis et al. (2021), Journal of Interpersonal Violence (HITS-based, 9 items). © SAGE Publications; used with attribution, permission pending."}
SOURCES = {"A": "Adapted from the WPSI Screening for Intimate Partner and Domestic Violence in Women — Resource Guide & Clinical Workflow (9.9.25).",
           "B": SOURCES_B["cdc"],
           "C": "Adapted from the Safe & Together Institute behavior/pattern-based approach and LGBTQ+ IPV screening guidance (NCAVP; The Network/La Red; LGBTQ health education sources). "
                "Informed by guidance from the National LGBTQ Institute on Intimate Partner Violence (lgbtqipvinstitute.org)."}
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
# CDC NISVS-adapted Version B (TEMPORARY). Tier 3 items: Q5, Q10, Q11, Q12, Q13.
_B_CDC_FREQ = [("b_1", "insult, humiliate, or make fun of you in front of others?", False), ("b_2", "keep you from having your own money?", False),
               ("b_3", "try to keep you from seeing or talking to family or friends?", False), ("b_4", "keep track of you by demanding to know where you were and what you were doing?", False),
               ("b_5", "make threats to physically harm you?", True), ("b_6", "threaten to hurt themselves or commit suicide because they were upset with you?", False),
               ("b_7", "make decisions that should have been yours to make?", False), ("b_8", "destroy something important to you?", False),
               ("b_9", "slap, push, or shove you?", False), ("b_10", "hit you with a fist or something hard, kick you, pull your hair, or slam you against something?", True),
               ("b_11", "try to hurt you by choking or suffocating you, burn you on purpose, or use a knife or gun?", True),
               ("b_12", "pressure you into unwanted sex, force you, or make you penetrate them?", True), ("b_13", "touch your sexual body parts when you didn't want them to?", True),
               ("b_14", "follow, watch, or repeatedly contact you in ways that made you feel afraid?", False)]
STEM = "Over the last 12 months, how often did your partner, an ex-partner, or someone you dated…"


def _item(i, text, kind, part, tier3=False, stem=None):
    return {"id": i, "text": text, "kind": kind, "part": part, "tier3": tier3, "stem": stem}


_B_CHILD = [*[_item(i, t, "yn", "Part 2 · Your children") for i, t, _k in _CHILD], _item("c3", "Do you worry about losing contact with your children if you ask for help?", "yn", "Part 2 · Your children")]
B_VARIANTS = {
    "velonis": {"version": "B", "title": "Safety Screening — Version B (Men)", "intro": f"{INTRO} {INTRO_B}", "source": SOURCES_B["velonis"], "b_source": "velonis", "items": [
        _item("b1", "Over the last 12 months, how often did you feel uncomfortable doing or saying things around your current partner or someone you're currently dating?", "freq", "Part 1 · Your relationship"),
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _B_FREQ], *_B_CHILD,
        _item("safe", "How safe do you feel going home today?", "safe", "Closing")]},
    "cdc": {"version": "B", "title": "Safety Screening — Version B (Men)", "intro": f"{INTRO} {INTRO_B}", "source": SOURCES_B["cdc"], "b_source": "cdc", "items": [
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _B_CDC_FREQ],
        _item("b_15", "How often do you feel afraid of them?", "freq", "Part 1 · Your relationship"), *_B_CHILD,
        _item("safe", "How safe do you feel going home today?", "safe", "Closing")]},
}
IMPORT_SOURCE_B = {"cdc_nisvs_adapted": "cdc", "velonis_hits": "velonis"}

VERSIONS = {
    "A": {"version": "A", "title": "Safety Screening — Version A (Women)", "intro": INTRO, "source": SOURCES["A"], "items": [
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _A_FREQ],
        _item("a6", "How often do you feel you have to change what you say or do to avoid conflict with them?", "freq", "Part 1 · Your relationship"),
        *[_item(i, t, "yn", "Part 2 · Your children") for i, t, _k in _CHILD],
        _item("a9", "What makes it hard to stay safe or get help (money, fear of losing custody, immigration status, lack of support)?", "text", "Part 3 · Optional"),
        _item("safe", "How safe is it for you to go home today?", "safe", "Closing")]},
    "B": B_VARIANTS["cdc"],
    "FV": __import__("fv_screening").SPEC,
    "C": {"version": "C", "title": "Safety Screening — Version C (LGBTQ+ Relationship Self-Assessment)", "intro": INTRO_C, "source": SOURCES["C"], "label": LABEL_C, "items": [
        *[_item(i, t, "freq", "Part 1 · Your relationship", t3, STEM) for i, t, t3 in _C_FREQ],
        *[_item(i, t, "freq", "Part 2 · Identity-based tactics", t3, STEM) for i, t, t3 in _C_IDENTITY],
        *[_item(i, t, "yn", "Part 3 · Your children") for i, t, _k in _CHILD],
        _item("c_15", "Do you worry about losing contact with your children, or how a court would view you, if you ask for help?", "yn", "Part 3 · Your children"),
        _item("safe", "How safe do you feel going home today?", "safe", "Closing")]},
}
TIER_LABEL = {1: "Tier 1 — resources only", 2: "Tier 2 — review resources; professional follow-up suggested", 3: "Tier 3 — professional follow-up recommended"}
# Report/PDF/co-parent-safe labels: never name identity. Full names live in VERSION_LABEL_PRO (professional-only screens).
VERSION_LABEL = {"A": "Version A", "B": "Version B", "C": "Version C", "FV": "Family check-in"}
VERSION_LABEL_PRO = {"A": "Version A (women)", "B": "Version B (men)", "C": "Version C (LGBTQ+ relationship)", "FV": "Family check-in (8 domains)"}
# 2026-10-17 (owner, final): the 8-domain Family check-in is the single live screening; the A/B/C choice screen is removed (definitions kept only to read legacy records).
OFFERED_VERSION = "FV"
# Owner-approved 2026-10-16: every parent sees the SAME four options; nothing is inferred from the profile. Only the version letter is stored.
CHOICE_LABEL = {"A": "Questions written for women (Version A)", "B": "Questions written for men (Version B)", "C": "Questions written for LGBTQ+ relationships (Version C)"}
CHOICE_HELP_LABEL = "Prefer not to say (I'll help you choose)"
CHOICE_HELP_TEXT = ("Any set works. Pick the one whose wording feels closest to your situation — the questions cover the same topics. "
                    "Nothing about this choice is recorded except the version letter.")
CHOICE_SWITCH_NOTE = "You can switch to a different set of questions later."
GENDER_DEFAULT: dict = {}  # intentionally empty — no profile-based default (2026-10-16)


def configure_version_b(source: str) -> None:
    """Switch the live Version B between 'cdc' (temporary default) and 'velonis' (off until written permission)."""
    global VERSION_B_SOURCE
    if source not in B_VARIANTS:
        raise ValueError("VERSION_B_SOURCE must be 'cdc' or 'velonis'")
    import safety_pathway
    VERSION_B_SOURCE = source
    VERSIONS["B"] = B_VARIANTS[source]
    SOURCES["B"] = SOURCES_B[source]
    safety_pathway.FLAG_MAP["B"] = safety_pathway.FLAG_MAP_B[source]


def _spec_for(version: str, b_source: str | None = None) -> dict:
    return B_VARIANTS[b_source] if version == "B" and b_source in B_VARIANTS else VERSIONS[version]


def resources_for(version: str) -> list[dict]:
    return RESOURCES + RESOURCES_C if version == "C" else RESOURCES


def public_spec(version: str) -> dict:
    v = VERSIONS[version]
    from safety_pathway import EXTRA_ITEMS, YN3
    items = [i for i in v["items"] if i["id"] != "safe"] + EXTRA_ITEMS + [i for i in v["items"] if i["id"] == "safe"]
    if version == "FV":
        import fv_screening as fv
        pub_items = [{k: x for k, x in i.items() if k not in ("weight", "tier3")} for i in v["items"]]  # rule weights are professional-only
        return {**v, "items": pub_items, "label": LABEL, "trigger_warning": TRIGGER_WARNING, "scale_note": None, "scales": {**fv.SCALES, "yn3": YN3}, "resources": FV_RESOURCES, "external_link_note": EXTERNAL_LINK_NOTE,
                "safe_device_notice": "Use a device your co-parent cannot see. The Quick Exit button (or pressing Escape twice) leaves this page immediately and clears it from this browser."}
    return {**v, "items": items, "label": v.get("label", LABEL), "trigger_warning": TRIGGER_WARNING, "scale_note": SCALE_NOTE, "scales": {"freq": FREQ, "yn": YN, "safe": SAFE, "yn3": YN3}, "resources": resources_for(version),
            "external_link_note": EXTERNAL_LINK_NOTE,
            "safe_device_notice": "Use a device your co-parent cannot see. The Quick Exit button (or pressing Escape twice) leaves this page immediately and clears it from this browser."}


def compute_tier(version: str, responses: dict, b_source: str | None = None) -> int:
    """Design guide, not a validated cutoff. Skipped / 'Prefer not to say' items never raise the tier."""
    if version == "FV":
        return __import__("fv_screening").compute(responses)["tier"]
    items = _spec_for(version, b_source)["items"]
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
    return OFFERED_VERSION  # every parent gets the same family check-in; nothing inferred from the profile


def build_record(version: str, responses: dict, source: str = "sacoparentsalign.com", completed_at: str | None = None, tier: int | None = None, answered_count: int | None = None,
                 flags: dict | None = None, pathway: str | None = None, b_source: str | None = None) -> dict:
    from safety_pathway import EXTRA_ITEMS, compute_flags, pathway_from_flags
    spec = _spec_for(version, b_source)
    items = spec["items"] + (EXTRA_ITEMS if version != "FV" else [])
    clean = {i["id"]: str(responses[i["id"]])[:1000].strip() for i in items if responses.get(i["id"]) not in (None, "")}
    if version == "FV":
        import fv_screening as fv
        res = fv.compute(clean)
        skipped = [i["id"] for i in items if i["kind"] != "gate" and (i["id"] not in clean or clean[i["id"]] in fv.SKIP)]
        return {"source": source, "version": "FV", "b_source": None, "title": spec["title"], "completed_at": completed_at or datetime.now(timezone.utc).isoformat(), "tier": res["tier"],
                "app_tier": res["app_tier"], "triggered_rules": res["triggered_rules"], "answered_count": len([k for k in clean if clean[k] not in fv.SKIP and k != "gate"]),
                "skipped_count": len(skipped), "item_count": len([i for i in items if i["kind"] != "gate"]), "concern_count": len(res["triggered_rules"]), "responses": clean,
                "flags": {}, "pathway_suggested": {"pathway": None, "label": None, "triggered": res["triggered_rules"], "triggered_labels": [fv.RULE_LABEL.get(k, k) for k in res["triggered_rules"]]}}
    skipped = [i["id"] for i in items if i["id"] not in clean or clean[i["id"]] == "Prefer not to say"]
    t = tier if tier in (1, 2, 3) else compute_tier(version, clean, spec.get("b_source"))
    fl = flags if isinstance(flags, dict) else compute_flags(version, clean, spec.get("b_source"))
    sugg = pathway_from_flags(fl) if not pathway else {"pathway": pathway, "label": __import__("safety_pathway").LABEL[pathway], "triggered": [k for k, v in fl.items() if v], "triggered_labels": [__import__("safety_pathway").FLAG_LABEL[k] for k, v in fl.items() if v]}
    concern = sum(1 for i in items if i["kind"] == "freq" and clean.get(i["id"]) in ("Sometimes", "Frequently")) + (1 if clean.get("safe") == "Not safe" else 0)
    return {"source": source, "version": version, "b_source": spec.get("b_source"), "title": spec["title"], "completed_at": completed_at or datetime.now(timezone.utc).isoformat(), "tier": t,
            "answered_count": answered_count if isinstance(answered_count, int) else len([k for k in clean if clean[k] != "Prefer not to say"]), "skipped_count": len(skipped),
            "item_count": len(items), "concern_count": concern, "responses": clean, "flags": fl, "pathway_suggested": sugg}


def public_record(scr: dict | None) -> dict | None:
    """Report-safe projection: receipt metadata only — never responses or items."""
    if not scr:
        return None
    return {k: scr.get(k) for k in ("source", "version", "completed_at", "tier", "answered_count", "skipped_count", "item_count")}


def entry_status(doc: dict, role: str) -> str:
    """Start-with-Safety step: completed | declined | not_started. Declined satisfies the step; it is never a fault."""
    if (doc.get("safety_screenings") or {}).get(role):
        return "completed"
    return "declined" if (doc.get("safety_declined") or {}).get(role) else "not_started"


def safety_step_satisfied(doc: dict, role: str | None) -> bool:
    return role is not None and entry_status(doc, role) != "not_started"


ENTRY_LABELS = {"completed": "Received", "declined": "Declined", "not_started": "Not started"}


def entry_label(doc: dict, role: str) -> str:
    st = entry_status(doc, role)
    date = str(((doc.get("safety_screenings") or {}).get(role) or {}).get("completed_at") or (doc.get("safety_declined") or {}).get(role) or "")[:10]
    return f"{ENTRY_LABELS[st]}{f' · {date}' if date and st != 'not_started' else ''}"


def receipt(scr: dict | None, parent_label: str, declined_at: str | None = None) -> str:
    """Court-safe line: receipt, version, date. Never answer text, never a tier (owner 2026-10-18). Declined is a neutral status, not a finding."""
    if not scr and declined_at:
        return f"{parent_label}: safety screening — Declined (parent chose not to answer at this time, {str(declined_at)[:10]})."
    if not scr:
        return f"{parent_label}: safety screening — Not started."
    ver = VERSION_LABEL.get(scr.get("version") or "", "legacy format")
    date = str(scr.get("completed_at") or "")[:10]
    return f"{parent_label}: safety screening — Received ({ver}, {scr.get('source') or 'sacoparentsalign.com'}){f', completed {date}' if date else ''}."


def item_view(scr: dict) -> list[dict]:
    """Professional-only item-level view (access must be logged by the caller)."""
    ver = scr.get("version")
    if ver not in VERSIONS:
        return [{"id": k, "question": k, "answer": v, "kind": "text"} for k, v in (scr.get("responses") or {}).items()] or [{"id": it.get("question"), "question": it.get("question"), "answer": it.get("answer"), "kind": "text"} for it in scr.get("items") or []]
    r = scr.get("responses") or {}
    return [{"id": i["id"], "question": (f"{i['stem']} {i['text']}" if i.get("stem") else i["text"]), "answer": r.get(i["id"]) or "Skipped", "kind": i["kind"], "part": i["part"],
             "flag": i["kind"] == "freq" and r.get(i["id"]) in ("Sometimes", "Frequently") or (i["id"] == "safe" and r.get("safe") == "Not safe") or (i["kind"] == "yn3" and r.get(i["id"]) == "Yes")}
            for i in _spec_for(ver, scr.get("b_source"))["items"] + __import__("safety_pathway").EXTRA_ITEMS]


SAFE_CONTACT_METHODS = ("email", "phone call", "text", "through my professional only", "in person only", "Prefer not to say")
SAFE_CONTACT_FIELDS = ("method", "address", "safe_times", "voicemail_ok", "code_word")


def clean_safe_contact(sc: dict | None) -> dict | None:
    """Optional, skippable. Professional-only; never in reports, PDFs, exports, invitations, emails or the bridge."""
    if not isinstance(sc, dict) or not sc:
        return None
    out = {k: str(sc.get(k) or "")[:300].strip() for k in SAFE_CONTACT_FIELDS}
    if out["method"] not in SAFE_CONTACT_METHODS:
        out["method"] = "Prefer not to say" if out["method"] else ""
    return out if any(out.values()) else None


class SubmitIn(BaseModel):
    responses: dict
    safe_contact: dict | None = None


class AssignIn(BaseModel):
    role: str
    version: str


class DraftIn(BaseModel):
    responses: dict = {}


class ChooseIn(BaseModel):
    version: str


def _status(doc: dict) -> dict:
    out = {}
    for r in ("a", "b"):
        p = doc["participants"][r]
        scr = (doc.get("safety_screenings") or {}).get(r) or None
        ver = (doc.get("safety_version") or {}).get(r) or OFFERED_VERSION
        confirmed = bool((doc.get("safety_version_confirmed") or {}).get(r))
        out[r] = {"name": p.get("name") or f"Parent {r.upper()}", "gender": p.get("gender"), "version": ver, "needs_assignment": ver is None, "received": bool(scr),
                  "choice_needed": (not confirmed and not scr) and ver != "FV", "default_version": ver if ver in ("A", "B") else None, "chosen_by_parent": confirmed,
                  "app_tier": (scr or {}).get("app_tier"), "app_tier_label": __import__("fv_screening").APP_TIER_LABEL.get((scr or {}).get("app_tier")) if scr else None,
                  "triggered_rules": [__import__("fv_screening").RULE_LABEL.get(k, k) for k in ((scr or {}).get("triggered_rules") or [])] if scr else [],
                  "tier": scr.get("tier") if scr else None, "tier_label": TIER_LABEL.get(scr.get("tier")) if scr else None, "version_label": VERSION_LABEL.get(ver or ""),
                  "completed_at": (scr or {}).get("completed_at"), "source": (scr or {}).get("source"), "receipt": receipt(scr, p.get("name") or f"Parent {r.upper()}", (doc.get("safety_declined") or {}).get(r)),
                  "reminded_at": (doc.get("safety_reminded_at") or {}).get(r), "communication_received": bool((doc.get("communication_readiness") or {}).get(r)),
                  "declined_at": (doc.get("safety_declined") or {}).get(r),
                  "entry_status": entry_status(doc, r), "entry_label": entry_label(doc, r)}
    return out


def spec_export() -> dict:
    """Machine-readable spec for the parent app: identical wording, scales, tiering, and the import payload contract."""
    def _items(v, with_weights):
        out = []
        for i in v["items"]:
            row = {"id": i["id"], "part": i["part"], "stem": i.get("stem"), "text": i["text"], "kind": i["kind"], "follow": i.get("follow")}
            if with_weights:
                row["tier3"] = bool(i.get("tier3"))
            out.append(row)
        return out
    fv = __import__("fv_screening")
    legacy = {k: {"version": k, "title": v["title"], "intro": v["intro"], "label": v.get("label", LABEL), "source": v["source"], "items": _items(v, True)} for k, v in VERSIONS.items() if k != "FV"}
    return {"schema_version": 4, "label": LABEL, "trigger_warning": TRIGGER_WARNING, "resources": FV_RESOURCES, "external_link_note": EXTERNAL_LINK_NOTE,
            "offered": {"version": OFFERED_VERSION, "title": fv.TITLE, "intro": fv.PRIVACY_NOTE, "items": _items(VERSIONS["FV"], False), "scales": {**fv.SCALES, "yn3": __import__("safety_pathway").YN3},
                        "note": "One Family check-in, identical for every parent. No choice screen, no gender inference. Rule weights and tiers are professional-only and are not exported."},
            "legacy_versions": {"note": "A/B/C were retired 2026-10-18; listed only so previously imported records can be read.", "scales": {"freq": FREQ, "yn": YN, "safe": SAFE}, "scale_note": SCALE_NOTE,
                                "resources_c": RESOURCES_C, "version_b_source": VERSION_B_SOURCE, "version_b_import_sources": IMPORT_SOURCE_B, "versions": legacy},
            "additional_items": __import__("safety_pathway").EXTRA_ITEMS,
            "safety_pathway": {"flags": __import__("safety_pathway").FLAGS, "flag_map": __import__("safety_pathway").FLAG_MAP, "labels": __import__("safety_pathway").LABEL,
                               "export_fields": {"safety_flags": "dict of the 9 booleans (optional)", "safety_pathway": "standard|structured|protected_review (optional)"}, "note": "Suggested flag only; the assigned professional confirms. Highest restriction wins across parents."},
            "communication_readiness": {"items": COMM_ITEMS, "export_field": "communication_readiness", "shape": {"completed_at": "ISO-8601", "responses": {"cr_conflict": "Low|Moderate|High|Safety concerns", "cr_direct": "Yes|Only in writing|Not comfortable", "cr_channel": "one of the listed channels", "cr_child": "free text (optional)"}}},
            "assignment": {"choice_screen": None, "note": "No assignment step. Every parent receives the Family check-in (version FV)."},
            "check_in_links": {"alias": "https://sacoparentsalign.com/check-in?case=<SA case code>", "direct": "https://sacoparentsalign.com/joint/<report_id>/safety-screening", "report_id_source": "GET /api/integrations/case-invite/{token} → report_id"},
            "export_contract": {"path": "GET /api/integrations/export-assessments?email=<parent email>", "field": "safety_screening",
                                "shape": {"version": "FV (A|B|C accepted for legacy records)", "completed_at": "ISO-8601", "answered_count": "int (optional)", "responses": {"<item id>": "<scale value or free text>"}},
                                "privacy": "Reports/PDFs/co-parent views show only Received, version and date — never a tier, flag or answer. Raw responses go to the assigned professional only."}}


def build_router(db, get_current_user, get_joint_report_doc, report_role, log_access) -> APIRouter:
    r = APIRouter()

    async def _tier3_alert(doc: dict, role: str, rec: dict) -> None:
        """Immediate professional alert for a Tier 3 screening — receipt, version letter, tier only; never answers, never identity."""
        from html import escape

        from core import _pro_email_wrap, app_url
        from email_utils import EMAIL_FROM_NAME, send_email
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
        from email_utils import MINIMAL_NOTIFICATIONS as _MIN
        await send_email(to=pro["email"], subject=(f"Priority follow-up — Case {code} - {EMAIL_FROM_NAME}" if _MIN else f"Safety screening Tier 3 — Case {code} - {EMAIL_FROM_NAME}"), html=html, case_id=doc["id"], kind="safety_tier3_alert", to_role="Professional")

    def _is_pro(doc, user):
        return user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))

    @r.put("/joint/reports/{rid}/redactions")
    async def set_redactions(rid: str, body: dict, user=Depends(get_current_user)):
        """Professional redacts a parent's free-text answer before the Joint Report is released (GAP-15)."""
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can redact")
        role, key, on = body.get("role"), str(body.get("key") or "")[:40], bool(body.get("redacted", True))
        if role not in ("a", "b") or not key:
            raise HTTPException(status_code=400, detail="role (a|b) and key required")
        op = {"$addToSet" if on else "$pull": {f"redactions.{role}": key}}
        await db.joint_reports.update_one({"id": rid}, op)
        await log_access(doc, user, f"{'Redacted' if on else 'Un-redacted'} Parent {role.upper()} answer '{key}' in Joint Report", "redaction")
        fresh = await db.joint_reports.find_one({"id": rid}, {"redactions": 1})
        return {"redactions": (fresh or {}).get("redactions") or {}}

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
            for v in st.values():  # parents never see a tier, flag or triggered rule (review fix 2026-10-18)
                for k in ("app_tier", "app_tier_label", "triggered_rules", "tier", "tier_label"):
                    v.pop(k, None)
        mine = st.get(role) if role else None
        spec = public_spec(mine["version"]) if mine and mine["version"] and not mine["choice_needed"] else None
        choice = None
        if mine and mine["choice_needed"]:
            choice = {"question": "Which questions fit your situation best?", "intro": INTRO, "trigger_warning": TRIGGER_WARNING,
                      "options": [{"version": v, "label": CHOICE_LABEL[v]} for v in ("A", "B", "C")] + [{"version": "help", "label": CHOICE_HELP_LABEL, "help": CHOICE_HELP_TEXT}],
                      "note": CHOICE_SWITCH_NOTE}
        my_draft = ((doc.get("safety_drafts") or {}).get(role) or {}).get("responses") if (role and not pro) else None
        return {"my_role": role, "is_professional": pro, "roles": st, "spec": spec, "choice": choice, "versions": VERSION_LABEL_PRO if pro else VERSION_LABEL, "scale_note": SCALE_NOTE, "my_draft": my_draft}

    @r.put("/joint/reports/{rid}/safety-screening/draft")
    async def save_screening_draft(rid: str, body: DraftIn, user=Depends(get_current_user)):
        """Resume support: partial answers kept on the parent's own account only; never visible to the co-parent or the professional; cleared on submit."""
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents can save progress")
        if (doc.get("safety_screenings") or {}).get(role):
            return {"ok": True, "saved": False}
        clean = {str(k)[:40]: str(v)[:40] for k, v in (body.responses or {}).items()}
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_drafts.{role}": {"responses": clean, "saved_at": datetime.now(timezone.utc).isoformat()}}})
        return {"ok": True, "saved": True}

    @r.post("/joint/reports/{rid}/safety-screening/decline")
    async def decline_screening(rid: str, user=Depends(get_current_user)):
        """Parent chooses "I'd rather not answer these right now". Satisfies the step; records status + date only; no notification."""
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents can use this step")
        if (doc.get("safety_screenings") or {}).get(role):
            return {"entry_status": "completed"}
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_declined.{role}": datetime.now(timezone.utc).isoformat()}})
        return {"entry_status": "declined"}

    @r.get("/me/safety-entry")
    async def my_safety_entry(user=Depends(get_current_user)):
        """Parent home banner state. Identical shape for every parent; only completion status, never tier/flags."""
        if user.get("role") != "parent":
            return {"applies": False}
        notice = {"notice": PROFESSIONAL_ACCESS_NOTICE, "notice_version": STEP_NOTICE_VERSION,
                  "needs_notice": (user.get("safety_step_notice") or {}).get("version") != STEP_NOTICE_VERSION}
        cur = db.joint_reports.find({"$or": [{"participants.a.user_id": user["_id"]}, {"participants.b.user_id": user["_id"]}], "archived": {"$ne": True}},
                                    {"id": 1, "participants": 1, "safety_screenings": 1, "safety_declined": 1, "created_at": 1}).sort("created_at", -1)
        docs = await cur.to_list(50)
        if not docs:
            return {"applies": True, "has_case": False, "status": "not_started", "report_id": None, "text": SAFETY_BANNER_TEXT, **notice}
        statuses = []
        for d in docs:
            role = "a" if (d["participants"].get("a") or {}).get("user_id") == user["_id"] else "b"
            statuses.append((d["id"], entry_status(d, role)))
        pending = next((s for s in statuses if s[1] == "not_started"), None)
        rid, status = pending or statuses[0]
        return {"applies": True, "has_case": True, "status": status, "report_id": rid, "text": SAFETY_BANNER_TEXT, **notice}

    @r.get("/joint/reports/{rid}/safety-screening/who-looked")
    async def who_looked(rid: str, user=Depends(get_current_user)):
        """Parent-facing, read-only: every recorded professional/admin opening of this parent's information (owner ruling 2026-10-19). Admins appear by role, never by name."""
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if not role or _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Available to the parent whose answers these are")
        what = {"safety_screening": "Your individual answers and safe-contact details", "safety_review": "Your check-in status and concern level (not your answers)",
                "redaction": "A single answer in the joint report", "safety_review_export": "Safety provisions document (no answers)",
                "view": "Your assessment answers (report)", "download": "Your assessment answers (report)", "foundation_view": "Your Foundation Statement (report)"}
        tag = f"Parent {role.upper()}"
        rows = await db.access_events.find({"report_id": rid, "kind": {"$in": list(what)}}, {"_id": 0}).sort("at", -1).to_list(500)
        ids = {e.get("by") for e in rows if e.get("by")}
        admins = {u["_id"] async for u in db.users.find({"_id": {"$in": list(ids)}, "role": "admin"}, {"_id": 1})}
        out = []
        for e in rows:
            if e["kind"] in ("safety_screening", "redaction") and tag not in (e.get("action") or ""):
                continue
            if (e.get("by_role") or "").startswith("Parent"):
                continue  # a parent opening their own report is not a professional view
            label = what[e["kind"]]
            if "Communications Log" in (e.get("action") or ""):
                label = "Communications log (report)"
            admin = e.get("by") in admins
            out.append({"at": e.get("at"), "viewer": "SA CoParents administrator" if admin else (e.get("by_name") or "Professional"),
                        "viewer_role": "SA CoParents administrator" if admin else (e.get("by_role") or "Assigned professional"), "what": label})
        return {"role": role, "events": out, "note": "Every time a professional or administrator opens your safety answers, your assessment answers in the report, or your Foundation Statement, it is recorded here. Your co-parent never appears in this list because they can never open your answers."}


    @r.get("/me/check-in")
    async def my_check_in(case: str | None = None, user=Depends(get_current_user)):
        """Stable alias for the parent app: resolves the signed-in parent's case (optionally by shared SA code) to the check-in route id. Status only."""
        if user.get("role") != "parent":
            raise HTTPException(status_code=403, detail="Parents only")
        q = {"$or": [{"participants.a.user_id": user["_id"]}, {"participants.b.user_id": user["_id"]}], "archived": {"$ne": True}}
        if case:
            q["case_code"] = case.strip().upper()
        docs = await db.joint_reports.find(q, {"id": 1, "case_code": 1, "participants": 1, "safety_screenings": 1, "safety_declined": 1, "created_at": 1}).sort("created_at", -1).to_list(50)
        if not docs:
            raise HTTPException(status_code=404, detail="No case found for this account" + (" and code" if case else ""))
        role_of = lambda d: "a" if (d["participants"].get("a") or {}).get("user_id") == user["_id"] else "b"  # noqa: E731
        doc = next((d for d in docs if entry_status(d, role_of(d)) == "not_started"), docs[0])
        return {"report_id": doc["id"], "case_code": doc.get("case_code"), "path": f"/joint/{doc['id']}/safety-screening"}


    @r.post("/me/safety-entry/ack-notice")
    async def ack_step_notice(user=Depends(get_current_user)):
        """Parent has seen the step screen with the current Professional Access Notice. Status only; nothing else changes."""
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"safety_step_notice": {"version": STEP_NOTICE_VERSION, "seen_at": datetime.now(timezone.utc).isoformat()}}})
        return {"ok": True, "notice_version": STEP_NOTICE_VERSION}

    @r.get("/safety/crisis-resources")
    async def crisis_resources(version: str | None = None, user=Depends(get_current_user)):
        return crisis_resources_for(version if version in ("A", "B", "C") else None)

    @r.put("/joint/reports/{rid}/safety-screening/choose")
    async def choose_version(rid: str, body: ChooseIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents can choose a screening version")
        if body.version not in set(VERSIONS):
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
        from parent_app_contract import (
            PARENT_APP_LINK_CONTRACT,
            assign_screening_version,
            case_context,
        )
        if PARENT_APP_LINK_CONTRACT:
            parent_uid = ((doc.get("participants") or {}).get(body.role) or {}).get("user_id")
            link = await db.account_links.find_one({"user_id": parent_uid}) if parent_uid else None
            if link:
                try:
                    await assign_screening_version(link["external_email"], body.version, *case_context(doc))
                except HTTPException as e:
                    from core import logger
                    logger.warning("parent-app screening/assign not applied for case %s: %s", rid, e.status_code)
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
        sc = clean_safe_contact(body.safe_contact)
        if sc:
            rec["safe_contact"] = sc
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_screenings.{role}": rec, f"safety_flags.{role}": rec["tier"] >= 2}, "$unset": {f"safety_drafts.{role}": ""}})
        if rec["tier"] == 3:
            try:
                await _tier3_alert(doc, role, rec)
            except Exception as exc:  # alert must never block the parent's submission
                import logging
                logging.getLogger("safety_screening").warning("Tier 3 alert not sent for case %s: %s", rid, exc)
        if version == "FV":  # parents never see a tier, score or flag
            return {"ok": True, "close_note": __import__("fv_screening").CLOSE_NOTE, "resources": RESOURCES, "external_link_note": EXTERNAL_LINK_NOTE, "answered_count": rec["answered_count"], "skipped_count": rec["skipped_count"]}
        return {"tier": rec["tier"], "tier_label": TIER_LABEL[rec["tier"]], "resources": resources_for(version), "external_link_note": EXTERNAL_LINK_NOTE, "answered_count": rec["answered_count"], "skipped_count": rec["skipped_count"], "scale_note": SCALE_NOTE}

    @r.get("/joint/reports/{rid}/safety-screening/{role}/responses")
    async def screening_responses(rid: str, role: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Item-level screening responses are visible only to the assigned professional")
        from pro_training import require_training
        await require_training(db, user)
        scr = (doc.get("safety_screenings") or {}).get(role) if role in ("a", "b") else None
        if not scr and not (doc.get("communication_readiness") or {}).get(role):
            return {"status": {**_status(doc)[role], "version_label": None}, "items": [], "pathway": None, "scale_note": SCALE_NOTE, "source_credit": "", "not_completed": True,
                    "communication": {"received": False}, "notice": "This parent has not completed the Family check-in yet. Nothing has been recorded; there is nothing to review."}
        await log_access(doc, user, f"Viewed Parent {role.upper()} safety screening responses (professional-only)", "safety_screening")
        if not scr:
            comm = (doc.get("communication_readiness") or {}).get(role)
            return {"status": {**_status(doc)[role], "version_label": None}, "items": [], "pathway": None, "scale_note": SCALE_NOTE, "source_credit": "",
                    "communication": {"received": True, "completed_at": comm.get("completed_at"), "source": comm.get("source"), "flag_for_professional": comm.get("flag_for_professional"), "items": comm_items_view(comm), "note": "Parent's private communication readiness answers — a flag input for you, not a decision."},
                    "notice": "Parent-reported answers, shown to the assigned professional only. Not findings. Never shared with the co-parent, the court, or any report."}
        st = _status(doc)[role]
        st["version_label"] = VERSION_LABEL_PRO.get(scr.get("version") or "", "legacy format")
        st["title"] = scr.get("title")
        from safety_pathway import LABEL as _PL
        from safety_pathway import PATHWAYS as _PW
        decision = (doc.get("safety_pathway") or {}).get(role) or {}
        pathway = {"suggested": scr.get("pathway_suggested") or {"pathway": "standard", "label": "Standard", "triggered": [], "triggered_labels": []}, "decision": decision or None,
                   "options": [{"key": k, "label": _PL[k]} for k in _PW], "note": "Suggested flag only — nothing is restricted automatically. Confirm, change, or dismiss; only your confirmed pathway reaches the report."}
        comm = (doc.get("communication_readiness") or {}).get(role)
        communication = {"received": True, "completed_at": comm.get("completed_at"), "source": comm.get("source"), "flag_for_professional": comm.get("flag_for_professional"), "items": comm_items_view(comm),
                         "note": "Parent's private communication readiness answers — a flag input for you, not a decision."} if comm else {"received": False}
        return {"status": st, "items": item_view(scr), "pathway": pathway, "communication": communication, "scale_note": SCALE_NOTE,
                "safe_contact": scr.get("safe_contact"),  # professional-only, access-logged screen
                "source_credit": SOURCES_B.get(scr.get("b_source"), SOURCES["B"]) if scr.get("version") == "B" else SOURCES.get(scr.get("version") or "", ""),
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
            from email_utils import MINIMAL_NOTIFICATIONS, NEUTRAL_SUBJECT
            if MINIMAL_NOTIFICATIONS:
                html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                        f"<p>Hi {escape(user.get('name') or 'there')},</p>"
                        "<p>You have an optional step waiting in your SA CoParents account. It takes about five minutes and every question can be skipped.</p>"
                        f'<p><a href="{app_url()}/joint/{doc["id"]}/safety-hub" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Sign in to continue</a></p>'
                        f'<p style="font-size:12px;color:#888">Sent by {escape(from_name)}. We never ask for your password by email.</p></td></tr></table>')
                subject = NEUTRAL_SUBJECT
            else:
                html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                    f"<p>Hi {escape(user.get('name') or 'there')},</p>"
                    f"<p>A short, private safety screening is still waiting for you on case <strong>{escape(code)}</strong>. It takes about five minutes. "
                    "Every question can be skipped, and your co-parent will never see your answers — only your professional can.</p>"
                    f'<p><a href="{app_url()}/joint/{doc["id"]}/safety-screening" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open my private screening</a></p>'
                    "<p style=\"color:#666;font-size:13px\">If you are in danger now, call 911 or the National Hotline at 1-800-799-7233 (text START to 88788).</p>"
                    f'<p style="font-size:12px;color:#888">Sent by {escape(from_name)}. We never ask for your password by email.</p></td></tr></table>')
            try:
                if not MINIMAL_NOTIFICATIONS:
                    subject = f"A private screening is waiting for you — Case {code} - {from_name}"
                await send_email(to=user["email"], subject=subject, html=html, case_id=doc["id"], kind="safety_screening_reminder", to_role=f"Parent {role.upper()}")
            except Exception as exc:
                logger.warning("safety screening reminder failed for %s/%s: %s", doc["id"], role, exc)
                continue
            await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {f"safety_reminded_at.{role}": now.isoformat()}})
            sent += 1
    return sent


# ---- Communication Readiness (private flag input for the professional; never a decision, never shown to the co-parent) ----
COMM_ITEMS = [
    {"id": "cr_conflict", "text": "Right now, how does conflict with your co-parent feel?", "kind": "choice", "options": ["Low", "Moderate", "High", "Safety concerns"]},
    {"id": "cr_direct", "text": "Do you feel safe communicating with your co-parent directly?", "kind": "choice", "options": ["Yes", "Only in writing", "Not comfortable"]},
    {"id": "cr_channel", "text": "Which communication channel feels safest for your family?", "kind": "choice", "options": ["Direct messaging", "Written-only through a logged platform", "Structured third-party communication", "Prefer not to say"]},
    {"id": "cr_child", "text": "Is there anything about communication you are concerned about for your child? (optional)", "kind": "text", "options": None},
]
COMM_NOTE = "A private flag input for your professional — not a decision. Your co-parent will never see these answers."


def comm_record(responses: dict, source: str = "sacoparentsalign.com", completed_at: str | None = None) -> dict:
    clean = {}
    for it in COMM_ITEMS:
        v = (responses or {}).get(it["id"])
        if v in (None, ""):
            continue
        v = str(v)[:1000].strip()
        if it["kind"] == "choice" and v not in it["options"]:
            continue
        clean[it["id"]] = v
    flag = clean.get("cr_conflict") in ("High", "Safety concerns") or clean.get("cr_direct") == "Not comfortable" or clean.get("cr_channel") == "Structured third-party communication"
    return {"source": source, "completed_at": completed_at or datetime.now(timezone.utc).isoformat(), "responses": clean, "answered_count": len(clean), "flag_for_professional": flag}


def comm_items_view(rec: dict) -> list[dict]:
    r = rec.get("responses") or {}
    return [{"id": it["id"], "question": it["text"], "answer": r.get(it["id"]) or "Skipped", "kind": it["kind"]} for it in COMM_ITEMS]


class CommIn(BaseModel):
    responses: dict


def comm_router(db, get_current_user, get_joint_report_doc, report_role) -> APIRouter:
    r = APIRouter()

    @r.get("/joint/reports/{rid}/communication-readiness")
    async def comm_get(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents complete the communication readiness check")
        rec = (doc.get("communication_readiness") or {}).get(role)
        return {"items": COMM_ITEMS, "note": COMM_NOTE, "received": bool(rec), "completed_at": (rec or {}).get("completed_at")}

    @r.put("/joint/reports/{rid}/communication-readiness")
    async def comm_put(rid: str, body: CommIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        role = report_role(doc, user["_id"])
        if role is None:
            raise HTTPException(status_code=403, detail="Only invited parents complete the communication readiness check")
        rec = comm_record(body.responses or {})
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"communication_readiness.{role}": rec}})
        return {"received": True, "answered_count": rec["answered_count"], "note": COMM_NOTE}

    return r
