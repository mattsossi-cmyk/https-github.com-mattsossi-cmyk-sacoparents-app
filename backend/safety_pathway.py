"""Safety Pathway Engine — layers on Safety Screening v2 (A/B/C). Suggests a neutral pathway flag; the professional decides.

Nothing here restricts anything automatically. Labels are deliberately neutral (never custody-style wording).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

YN3 = ["Yes", "No", "Prefer not to say"]
EXTRA_PART = "Additional safety questions"
EXTRA_STEM = "Over the last 12 months, how often did your partner, an ex-partner, or someone you dated…"
EXTRA_ITEMS = [
    {"id": "x_1", "flag": "financialAbuse", "text": "prevent you from having or using money, or run up debts in your name?", "kind": "freq", "part": EXTRA_PART, "stem": EXTRA_STEM, "tier3": False},
    {"id": "x_2", "flag": "technologyStalking", "text": "track your phone, location, accounts, or messages without your agreement?", "kind": "freq", "part": EXTRA_PART, "stem": EXTRA_STEM, "tier3": False},
    {"id": "x_3", "flag": "childRelatedThreats", "text": "threaten to hurt, take, or keep your children from you?", "kind": "freq", "part": EXTRA_PART, "stem": EXTRA_STEM, "tier3": False},
    {"id": "x_4", "flag": "fearOfRetaliation", "text": "How often do you feel afraid of what might happen if they knew you answered these questions or asked for help?", "kind": "freq", "part": EXTRA_PART, "stem": None, "tier3": False},
    {"id": "x_5", "flag": "activeProtectiveOrder", "text": "Is there a protective order, restraining order, or no-contact order in place between you and your co-parent?", "kind": "yn3", "part": EXTRA_PART, "stem": None, "tier3": False},
]
FLAGS = ["threatsOrIntimidation", "physicalOrSexualViolence", "coerciveControl", "financialAbuse", "technologyStalking", "childRelatedThreats", "fearOfRetaliation", "activeProtectiveOrder", "imminentDangerReported"]
FLAG_LABEL = {"threatsOrIntimidation": "Threats or intimidation", "physicalOrSexualViolence": "Physical or sexual violence", "coerciveControl": "Coercive control", "financialAbuse": "Financial abuse",
              "technologyStalking": "Technology-facilitated stalking", "childRelatedThreats": "Child-related threats", "fearOfRetaliation": "Fear of retaliation", "activeProtectiveOrder": "Active protective / no-contact order", "imminentDangerReported": "Not safe to go home today"}
# Version item ids -> flag (Sometimes/Frequently => true; skipped / Prefer not to say never infer)
FLAG_MAP_B = {
    "cdc": {"b_5": "threatsOrIntimidation", "b_6": "threatsOrIntimidation", "b_14": "threatsOrIntimidation", "b_15": "threatsOrIntimidation",
            "b_9": "physicalOrSexualViolence", "b_10": "physicalOrSexualViolence", "b_11": "physicalOrSexualViolence", "b_12": "physicalOrSexualViolence", "b_13": "physicalOrSexualViolence",
            "b_2": "coerciveControl", "b_3": "coerciveControl", "b_4": "coerciveControl", "b_7": "coerciveControl", "b_8": "coerciveControl"},
    "velonis": {"b5": "threatsOrIntimidation", "b6": "threatsOrIntimidation", "b7": "physicalOrSexualViolence", "b8": "physicalOrSexualViolence", "b9": "physicalOrSexualViolence", "b4": "coerciveControl"},
}
FLAG_MAP = {
    "A": {"a2": "threatsOrIntimidation", "a3": "physicalOrSexualViolence", "a4": "physicalOrSexualViolence", "a5": "coerciveControl"},
    "B": FLAG_MAP_B["cdc"],
    "C": {"c_3": "threatsOrIntimidation", "c_4": "threatsOrIntimidation", "c_5": "physicalOrSexualViolence", "c_6": "physicalOrSexualViolence", "c_2": "coerciveControl", "c_7": "coerciveControl"},
}
PATHWAYS = ["standard", "structured", "protected_review"]
RANK = {p: i for i, p in enumerate(PATHWAYS)}
LABEL = {"standard": "Standard", "structured": "Structured communication recommended", "protected_review": "Protected participation review recommended"}
P1 = ("imminentDangerReported", "physicalOrSexualViolence", "childRelatedThreats", "activeProtectiveOrder")
P2 = ("coerciveControl", "threatsOrIntimidation", "technologyStalking", "fearOfRetaliation", "financialAbuse")
COURT_ORDER_NOTICE = "Active court or protective orders reported. All recommendations must be reviewed against existing legal restrictions."
RESTRICTED_NOTICE = "Sensitive narratives, personal locations, and raw individual responses remain restricted in compliance with safety parameters."
PATHWAY_NOTE = "The pathway label is the assigned professional's confirmed process consideration. It is not a finding, a risk determination, or a custody recommendation."
SAFEGUARDS = {
    "standard": ["Standard co-parenting communication tools (shared calendar, app-based messaging) are appropriate."],
    "structured": ["Written-only communication through a logged co-parenting platform.", "Third-party or professional-assisted exchange of information when direct contact is not productive.", "Agreed response windows and child-focused subject lines; no in-person negotiation of disputed items."],
    "protected_review": ["Written-only communication through a logged co-parenting platform; no direct contact outside it.", "Third-party or professional-assisted exchanges and transitions.", "Professional-assisted sessions only; no joint in-person sessions unless the professional confirms safeguards are in place."],
}
DECISIONS = {
    "standard": ["Joint decision-making with standard tools; disputed child choices referred to the professional for discussion."],
    "structured": ["Category-based decision assignments (e.g., one parent leads medical, the other education), reviewed at each reassessment.", "Independent professional review of disputed child choices before either parent acts."],
    "protected_review": ["Category-based decision assignments with written notice only.", "Independent professional review of all disputed child choices; no joint decision meetings without the professional present."],
}


def _hit(v) -> bool:
    return v in ("Sometimes", "Frequently")


def compute_flags(version: str, responses: dict, b_source: str | None = None) -> dict:
    r = responses or {}
    flags = {f: False for f in FLAGS}
    fmap = FLAG_MAP_B[b_source] if version == "B" and b_source in FLAG_MAP_B else FLAG_MAP.get(version, {})
    for item_id, flag in fmap.items():
        if _hit(r.get(item_id)):
            flags[flag] = True
    for it in EXTRA_ITEMS:
        v = r.get(it["id"])
        flags[it["flag"]] = flags[it["flag"]] or (v == "Yes" if it["kind"] == "yn3" else _hit(v))
    flags["imminentDangerReported"] = r.get("safe") == "Not safe"
    return flags


def pathway_from_flags(flags: dict) -> dict:
    f = {k: bool((flags or {}).get(k)) for k in FLAGS}
    if any(f[k] for k in P1):
        p, trig = "protected_review", [k for k in P1 if f[k]]
    elif any(f[k] for k in P2):
        p, trig = "structured", [k for k in P2 if f[k]]
    else:
        p, trig = "standard", []
    return {"pathway": p, "label": LABEL[p], "triggered": trig, "triggered_labels": [FLAG_LABEL[k] for k in trig]}


def normalize_import(payload_flags, payload_pathway) -> tuple[dict | None, str | None]:
    """Bridge may send `safety_flags` (dict of booleans) and/or `safety_pathway` (key or label). Unknown -> None (fall back to computing)."""
    flags = {k: bool(payload_flags.get(k)) for k in FLAGS} if isinstance(payload_flags, dict) else None
    p = None
    if isinstance(payload_pathway, str):
        s = payload_pathway.strip().lower()
        p = next((k for k in PATHWAYS if s == k or s == LABEL[k].lower()), None) or ({"protected": "protected_review", "structured_communication": "structured"}.get(s))
    return flags, p


def highest(pathways: list) -> str | None:
    ps = [p for p in pathways if p in RANK]
    return max(ps, key=RANK.get) if ps else None


def confirmed_pathway(doc: dict, role: str) -> str | None:
    st = (doc.get("safety_pathway") or {}).get(role) or {}
    return st.get("confirmed") if st.get("status") == "confirmed" else None


def case_pathway(doc: dict) -> str | None:
    """Highest restriction among the professional's CONFIRMED pathways only. Suggestions never count."""
    return highest([confirmed_pathway(doc, r) for r in ("a", "b")])


def _child_needs(doc: dict, rep: dict | None) -> list[str]:
    """Deduplicated category labels only — no narratives, no locations, no raw responses."""
    from lens_data import CHILD_FOCUS_CATEGORIES
    labels = dict(CHILD_FOCUS_CATEGORIES)
    cf = (rep or {}).get("child_focus") or {}
    picked = [labels[k] for k, _ in CHILD_FOCUS_CATEGORIES if (cf.get(k) or {}).get("checked")]
    if not picked:
        subj = (doc.get("subject") or "").lower()
        picked = [lbl for k, lbl in CHILD_FOCUS_CATEGORIES if k in subj] or ["Communication between parents", "Transitions between households"]
    return list(dict.fromkeys(picked))


def public_pathway(doc: dict, rep: dict | None = None) -> dict | None:
    """Report-safe block (web, PDF, court): neutral label + sanitized guidance. No flags, no answers, no version names."""
    p = case_pathway(doc)
    if not p:
        return None
    order = any(((doc.get("safety_screenings") or {}).get(r) or {}).get("flags", {}).get("activeProtectiveOrder") for r in ("a", "b") if confirmed_pathway(doc, r))
    return {"pathway": p, "label": LABEL[p], "child_needs": _child_needs(doc, rep), "safeguards": SAFEGUARDS[p], "decisions": DECISIONS[p],
            "court_order_notice": COURT_ORDER_NOTICE if order else None, "restricted_notice": RESTRICTED_NOTICE, "note": PATHWAY_NOTE}


def pathway_lines(block: dict | None) -> list[str]:
    if not block:
        return []
    out = [f"Confirmed pathway: {block['label']}", f"Child-focused needs (categories only): {', '.join(block['child_needs'])}", "Communication safeguards:"] + [f"• {s}" for s in block["safeguards"]]
    out += ["Decision-making options:"] + [f"• {d}" for d in block["decisions"]]
    if block.get("court_order_notice"):
        out.append(block["court_order_notice"])
    out += [block["restricted_notice"], block["note"]]
    return out


class DecideIn(BaseModel):
    action: str  # confirm | change | dismiss
    pathway: str | None = None


def build_router(db, get_current_user, get_joint_report_doc, log_access, is_pro) -> APIRouter:
    r = APIRouter()

    @r.put("/joint/reports/{rid}/safety-pathway/{role}")
    async def decide(rid: str, role: str, body: DecideIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can decide a safety pathway")
        scr = (doc.get("safety_screenings") or {}).get(role) if role in ("a", "b") else None
        if not scr:
            raise HTTPException(status_code=404, detail="No safety screening on file for this parent")
        suggested = (scr.get("pathway_suggested") or {}).get("pathway") or "standard"
        if body.action == "dismiss":
            rec = {"status": "dismissed", "suggested": suggested, "confirmed": None}
        elif body.action in ("confirm", "change"):
            chosen = body.pathway if body.action == "change" else suggested
            if chosen not in PATHWAYS:
                raise HTTPException(status_code=400, detail="Unknown pathway")
            rec = {"status": "confirmed", "suggested": suggested, "confirmed": chosen}
        else:
            raise HTTPException(status_code=400, detail="action must be confirm, change or dismiss")
        rec.update({"by": user["_id"], "at": datetime.now(timezone.utc).isoformat()})
        await db.joint_reports.update_one({"id": rid}, {"$set": {f"safety_pathway.{role}": rec}})
        await log_access(doc, user, f"Safety pathway {rec['status']} for Parent {role.upper()}: {LABEL.get(rec['confirmed'] or suggested)}", "safety_pathway")
        if rec["status"] == "confirmed":
            from safety_status_webhook import notify_safety_mode
            notify_safety_mode(rid, case_pathway({**doc, "safety_pathway": {**(doc.get("safety_pathway") or {}), role: rec}}), user.get("name", ""))
        return {**rec, "label": LABEL.get(rec["confirmed"]) if rec["confirmed"] else None, "case_pathway": case_pathway({**doc, "safety_pathway": {**(doc.get("safety_pathway") or {}), role: rec}})}

    return r
