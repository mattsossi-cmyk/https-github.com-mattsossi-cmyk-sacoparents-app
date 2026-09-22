"""Co-Parenting Ability Level (1-10 scale) → tier library used ONLY in the Professional Report (professional + court)."""
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
LIBRARY_KEYS = ("techniques", "tools", "resources")


def tier_for(score: int) -> dict:
    score = max(1, min(10, int(score)))
    t = next(t for t in TIERS.values() if t["range"][0] <= score <= t["range"][1])
    return {**t, "score": score}


def _complete(case: dict) -> bool:
    return bool(case.get("responses", {}).get("a") and case.get("responses", {}).get("b")) and case.get("kind", "joint_report") == "joint_report"


def joint_findings(case: dict) -> dict | None:
    """Neutral findings infused from the Joint Report: alignment, differences (area only), child-focused considerations, subject options."""
    if not _complete(case):
        return None
    rep = generate_joint_report(case)
    diffs = [d.get("area", "") for d in (rep.get("differences") or []) if isinstance(d, dict)]
    return {"subject_label": rep.get("subject_label"), "alignment": rep.get("alignment_statements") or [],
            "differences": [f"Parents expressed different perspectives regarding {a.lower()}." for a in diffs],
            "child_focused": rep.get("child_needs") or [], "alignment_map": rep.get("alignment_map") or [],
            "subject_options": (rep.get("options") or []) if diffs else [], "is_safety": bool(case.get("is_safety"))}


def suggested_score(case: dict) -> dict | None:
    """Data-derived suggestion: alignment ratio, number of differences, safety flag and communication-area alignment. Professional may override."""
    f = joint_findings(case)
    if not f:
        return None
    aligned, differing = len(f["alignment"]), len(f["differences"])
    total = aligned + differing
    ratio = aligned / total if total else 0.5
    score = round(2 + ratio * 8)
    notes = [f"{aligned} aligned and {differing} differing area{'s' if differing != 1 else ''} in the Joint Report"]
    if differing >= 4:
        score -= 1
        notes.append("four or more differing areas")
    comm = [r for r in f["alignment_map"] if "communicat" in str(r.get("area", "")).lower() or "communicat" in str(f.get("subject_label", "")).lower()]
    if comm and all(r.get("status") == "Needs discussion" for r in comm):
        score -= 1
        notes.append("communication areas need discussion")
    if f["is_safety"]:
        score = min(score, 3)
        notes.append("safety-focused assessment caps the suggestion at Level 3")
    score = max(1, min(10, score))
    return {"score": score, "aligned": aligned, "differing": differing, "label": tier_for(score)["label"], "rationale": "; ".join(notes) + ". Neutral, data-derived; not a finding about either parent."}


def framework_block(score: int, chosen: dict | None = None, custom: dict | None = None, subject_options: list | None = None, library: dict | None = None) -> dict:
    """Block stored in the Professional Report: level + kept library items (tier + professional's saved library) + own additions + subject options."""
    t = tier_for(score)
    chosen, custom, library = chosen or {}, custom or {}, library or {}
    out = {"score": t["score"], "tier_key": t["key"], "label": t["label"], "color": t["color"], "safety_alert": t["safety_alert"],
           "framework_title": t["framework_title"], "framework": t["framework"]}
    for k in LIBRARY_KEYS:
        pool = t[k] + [i for i in (library.get(k) or []) if i not in t[k]]
        kept = [i for i in pool if k not in chosen or i in chosen[k]]
        extra = [str(x).strip()[:300] for x in (custom.get(k) or []) if str(x).strip()][:10]
        out[k] = kept + extra
    opts = subject_options or []
    out["subject_options"] = [o for o in opts if "subject_options" not in chosen or o in chosen["subject_options"]]
    return out


def clean_library(raw: dict) -> dict:
    """Professional's personal saved resources/tools/techniques (stored on the user)."""
    return {k: list(dict.fromkeys(str(x).strip()[:300] for x in (raw.get(k) or []) if str(x).strip()))[:40] for k in LIBRARY_KEYS}


def level_history(packets: list) -> list[dict]:
    """Ability Level per submitted version (oldest first) — shows how the assessed dynamic evolved."""
    rows = []
    for p in sorted(packets, key=lambda p: p.get("submission_version") or 0):
        fw = (p.get("statement") or {}).get("framework") or {}
        st = p.get("statement") or {}
        rows.append({"version": p.get("submission_version"), "at": p.get("created_at"), "score": fw.get("score"), "label": fw.get("label"), "color": fw.get("color"), "superseded": p.get("superseded", False),
                     "note": st.get("level_change_note") or "", "changed_from": st.get("level_changed_from"), "growth": _growth_progress(p.get("legal_summary"))})
    return rows


def _growth_progress(summary: dict | None) -> dict | None:
    """Met / total Key Growth Areas per parent from the frozen Professional Evaluation Report snapshot."""
    if not summary or not summary.get("growth"):
        return None
    g = summary["growth"]
    return {role: {"met": sum(1 for x in g.get(role) or [] if x.get("met")), "total": len(g.get(role) or []), "items": g.get(role) or []} for role in ("a", "b")}
