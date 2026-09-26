"""Safety gate: family-violence / IPV indicators → Parallel Parenting variant, court warnings, Foundation share routing."""
from joint_data import SAFETY_SUBJECT_KEYS

HIGH = {"Moderate-to-High Risk", "High Risk"}
FOUNDATION_SAFETY_QUESTIONS = [
    ("fear", "Do you feel afraid of the other parent, or afraid of what may happen if you disagree with them?"),
    ("threats", "Has the other parent threatened, intimidated, stalked or physically hurt you or your child?"),
    ("control", "Does the other parent control your money, movements, communication or access to your child in ways that frighten you?"),
]
SAFETY_ROUTE_NOTE = ("Your answers indicate a safety concern. SA CoParents does not route parents with safety concerns into joint agreements or direct negotiation. "
                     "Your statement stays private; the professional will use the Family Violence / Safety pathway with safeguards instead.")


def _emails(doc: dict) -> set:
    return {((doc.get("participants", {}).get(s) or {}).get("email") or "").lower() for s in ("a", "b")} - {""}


def parent_safety_flag(statement: dict | None) -> bool:
    return any((statement or {}).get("safety", {}).get(k) is True for k, _ in FOUNDATION_SAFETY_QUESTIONS)


async def safety_status(db, emails: set, pro_id: str | None = None) -> dict:
    """Neutral, professional-facing flags for these two parents (no per-parent answers exposed)."""
    reasons = []
    if not emails:
        return {"flagged": False, "reasons": []}
    q = {"$or": [{"participants.a.email": {"$in": list(emails)}}, {"participants.b.email": {"$in": list(emails)}}]}
    if pro_id:
        q["created_by"] = pro_id
    cases = await db.joint_reports.find(q, {"_id": 0, "id": 1, "subject": 1, "subject_keys": 1, "participants": 1}).to_list(200)
    cases = [c for c in cases if _emails(c) == emails]
    if any(set(c.get("subject_keys") or [c.get("subject")]) & SAFETY_SUBJECT_KEYS for c in cases):
        reasons.append("A Family Violence / Safety assessment case exists for these parents.")
    ids = [c["id"] for c in cases]
    if ids:
        async for rep in db.professional_reports.find({"case_id": {"$in": ids}}, {"_id": 0, "risk_screening": 1, "joint_process_appropriate": 1}):
            high = [k for k, v in (rep.get("risk_screening") or {}).items() if (v or {}).get("level") in HIGH]
            if high:
                reasons.append("Professional risk screening recorded moderate-to-high or high risk indicators.")
            if (rep.get("joint_process_appropriate") or "").strip().lower().startswith("no"):
                reasons.append("The professional determined a joint process is not appropriate at this time.")
    async for u in db.users.find({"email": {"$in": list(emails)}}, {"_id": 1}):
        fs = await db.foundation_statements.find_one({"user_id": u["_id"]}, {"_id": 0, "safety": 1})
        if parent_safety_flag(fs):
            reasons.append("A parent's private safety screening indicates a safety concern.")
    return {"flagged": bool(reasons), "reasons": list(dict.fromkeys(reasons))}


PARALLEL = {
    "banner": "Safety Override — Parallel Parenting Structure",
    "note": ("Family-violence or safety indicators were identified. This agreement therefore follows a Parallel Parenting structure: no direct negotiation between parents, "
             "written app-only communication, neutral or third-party exchanges, and professional or court oversight for disputes. Court orders and safety plans take priority over every term below."),
    "communication": ["All communication is in writing through the SA CoParents app or another court-approved platform — no phone calls, texts or in-person discussion.",
                      "Messages are limited to child-related logistics, brief, informative, friendly and firm (BIFF).",
                      "Neither parent contacts the other's household, workplace or family members about the child.",
                      "Emergencies concerning the child are reported through the platform and, where required, to the appropriate authority."],
    "communication_choices": [("Primary Method", "Written, app-only communication"), ("Response Goal", "Within 24 hours; logistics only"), ("Direct Contact", "None — no calls, texts or in-person discussion")],
    "transitions": ["Exchanges occur at a neutral site (school, daycare or a supervised exchange center) or through a third party — never at either parent's home.",
                    "Parents do not arrive at the exchange location at the same time; a staggered arrival window is used.",
                    "No conversation takes place at exchanges; the child's belongings travel in a shared bag with a written log.",
                    "Any change to the schedule is requested in writing at least 48 hours ahead."],
    "conflict_intro": "Disputes are not negotiated directly between the parents. They move straight to written communication and professional or court process.",
    "conflict_steps": [("Step 1", "Structured written communication (app only)"), ("Step 2", "SA CoParents reflection tools — no joint sessions"), ("Step 3", "Parent facilitator / parenting coordinator"),
                       ("Step 4", "Attorney-assisted process"), ("Step 5", "Court motion or safety plan review"), ("Step 6", "Emergency: 911 / protective order process")],
    "options": ["Supervised or neutral-site exchange services.", "Parent facilitation / parenting coordination (court-appointed).", "Individual (not joint) counseling for each parent.",
                "Child therapy with a safety-informed provider.", "Domestic violence advocacy and safety planning resources.", "Attorney consultation regarding protective orders and court-ordered structures."],
}


def apply_parallel(model: dict, safety: dict) -> dict:
    """Rewrite the joint-negotiation sections of the agreement model into the Parallel Parenting structure."""
    if not (safety or {}).get("flagged"):
        return model | {"safety_override": None}
    return model | {k: v for k, v in PARALLEL.items() if k not in ("banner", "note")} | {
        "conflict_agreed": [], "safety_override": {"banner": PARALLEL["banner"], "note": PARALLEL["note"], "reasons": safety.get("reasons") or []},
        "purpose": model["purpose"] + " Because safety indicators were identified, the structure below is Parallel Parenting rather than cooperative co-parenting."}
