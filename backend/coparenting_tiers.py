"""Co-Parenting Dynamic Scale (1-10) → tier library used ONLY in the professional/legal report."""
from joint_engine import generate_joint_report

TIERS = {
    1: {"key": "high_risk", "range": (1, 3), "label": "Level 1-3: High Risk / IPV / Severe Conflict", "color": "#dc2626", "safety_alert": True,
        "framework_title": "Parallel Parenting with Zero Direct Contact",
        "framework": "Parenting functions are entirely disengaged from one another. Direct verbal or in-person contact is limited or strictly prohibited. Exchange locations must be neutral, public, or professionally supervised to ensure emotional and physical safety.",
        "techniques": ["BIFF Method Only: all written exchanges adhere to Brief, Informative, Friendly, Firm standards; hostile remarks are not answered.",
                       "No Verbal Communication: no phone calls or texting; court-admissible communication applications only.",
                       "Strict Third-Party Transfers: neutral public drop-off locations (e.g., police-station exchange zones) or supervised exchange services.",
                       "Boundaries via Order: adhere strictly to judicial decrees without verbal negotiation or informal modifications."],
        "tools": ["AppClose / OurFamilyWizard (required): court-monitored messaging, tamper-proof logs, GPS-verified exchanges.",
                  "Talkabout / CivilCommunicator: third-party filtering of hostile language before it reaches the recipient."],
        "resources": ["National Domestic Violence Hotline: 1-800-799-SAFE (24/7).", "Family Violence Prevention Services (San Antonio): emergency shelter and legal advocacy.",
                      "Bexar County Dispute Resolution Center: high-conflict court-ordered mediation.", "Texas Advocacy Project: free legal advice for domestic safety concerns."]},
    2: {"key": "moderate", "range": (4, 6), "label": "Level 4-6: Moderate Conflict / Low Trust", "color": "#d97706", "safety_alert": False,
        "framework_title": "Structured Parallel Parenting transitioning to Co-Parenting",
        "framework": "Parents maintain distinct boundaries but share basic responsibilities. Interactions are limited to practical scheduling, health, and education updates without personal interference.",
        "techniques": ["BIFF Communication: responses focus purely on logistics; emotional hooks, passive aggression, and past history are ignored.",
                       "Shared Digital Calendars: schedule changes are managed through a centralized app rather than debated.",
                       "Clear Transition Protocols: handoffs are brief, neutral, and focused on the child's comfort.",
                       "24-Hour Cooling-Off Rule: non-urgent requests or disagreements wait 24 hours before a response."],
        "tools": ["AppClose (recommended): shared expense tracking, schedules, exportable communications.", "Google Workspace / Shared Drive: central storage for child records, medical information, and school reports."],
        "resources": ["Bexar County DRC Co-Parenting Sessions: structured mediation for schedule disputes.", "SA CoParents support groups and parent education classes.",
                      "San Antonio Family Mediation Services: neutral third-party resolution."]},
    3: {"key": "collaborative", "range": (7, 10), "label": "Level 7-10: Collaborative Co-Parenting", "color": "#16a34a", "safety_alert": False,
        "framework_title": "Cooperative Co-Parenting Framework",
        "framework": "High level of trust, direct flexibility, and shared decision-making. Both parents coordinate schedules, attend shared events, and maintain consistent rules across both households.",
        "techniques": ["Direct Alignment Meetings: monthly or bi-monthly sync-ups on school, extracurricular, and health planning.",
                       "Unified Household Rules: shared expectations on screen time, homework, and discipline.",
                       "Flexible Scheduling: cooperative adjustments for holidays, travel, and family events without formal legal changes.",
                       "Joint Attendance: both parents attend school functions, games, and milestones."],
        "tools": ["Shared Google / Apple Calendar: synchronization of activities and appointments.", "Splitwise or Zelle: direct reimbursement of shared child-related expenses."],
        "resources": ["Family Enrichment Workshops (San Antonio): joint parenting-skills seminars.", "SA CoParents community events and child-advocacy programs."]},
}


def tier_for(score: int) -> dict:
    score = max(1, min(10, int(score)))
    t = next(t for t in TIERS.values() if t["range"][0] <= score <= t["range"][1])
    return {**t, "score": score}


def suggested_score(case: dict) -> dict:
    """Neutral, data-derived suggestion from the joint assessment: alignment ratio and safety flags. Professional may override."""
    rep = generate_joint_report(case)
    aligned = len(rep.get("alignment_statements") or [])
    differing = len(rep.get("differences") or [])
    total = aligned + differing
    ratio = aligned / total if total else 0.5
    score = round(2 + ratio * 8)
    if case.get("is_safety"):
        score = min(score, 3)
    rationale = f"{aligned} aligned and {differing} differing subject area{'s' if differing != 1 else ''} in the Joint Report" + ("; safety-focused assessment caps the suggestion at Level 3." if case.get("is_safety") else ".")
    return {"score": max(1, min(10, score)), "aligned": aligned, "differing": differing, "rationale": rationale}


def framework_block(score: int, chosen: dict | None = None) -> dict:
    """Final block stored in the statement: tier + the items the professional kept (defaults to all)."""
    t = tier_for(score)
    chosen = chosen or {}
    pick = lambda k: [i for i in t[k] if i in (chosen.get(k) or t[k])]  # noqa: E731
    return {"score": t["score"], "tier_key": t["key"], "label": t["label"], "color": t["color"], "safety_alert": t["safety_alert"],
            "framework_title": t["framework_title"], "framework": t["framework"],
            "techniques": pick("techniques"), "tools": pick("tools"), "resources": pick("resources")}
