from datetime import datetime, timezone

from report_engine import generate_report
from joint_engine import generate_joint_report


def build_complete_report(cases: list, joints: list, user_name: str) -> dict:
    sections = []
    totals = {"aligned": 0, "different": 0, "info": 0}
    children = []

    for c in cases:
        if not (c.get("responses", {}).get("a") and c.get("responses", {}).get("b")):
            continue
        rep = generate_report(c)
        s = rep["snapshot"]
        totals["aligned"] += s["aligned"]
        totals["different"] += s["different"]
        totals["info"] += s["info"]
        if c.get("child_name"):
            children.append(c["child_name"])
        sections.append({
            "kind": "assessment",
            "title": rep["assessment_title"],
            "child_name": c.get("child_name", ""),
            "snapshot": s,
            "alignments": rep["alignments"],
            "differences": rep["differences"],
            "child_needs": [n["title"] for n in rep["child_needs"]],
            "options": rep["options"][:4],
            "questions": rep["conversation_questions"],
            "priority": rep["summary"]["priority"],
        })

    for j in joints:
        if j.get("status") != "ready":
            continue
        rep = generate_joint_report(j)
        strong = sum(1 for r in rep["alignment_map"] if r["status"] == "Strong alignment")
        moderate = sum(1 for r in rep["alignment_map"] if r["status"] == "Moderate alignment")
        discussion = sum(1 for r in rep["alignment_map"] if r["status"] == "Needs discussion")
        totals["aligned"] += strong
        totals["different"] += discussion
        totals["info"] += moderate
        if rep.get("child_name"):
            children.append(rep["child_name"])
        sections.append({
            "kind": "joint",
            "title": f"Focused Joint Report: {rep['subject_label']}",
            "child_name": rep.get("child_name", ""),
            "alignment_statements": rep["alignment_statements"],
            "alignment_map": rep["alignment_map"],
            "differences": rep["differences"],
            "child_needs": rep["child_needs"],
            "options": rep["options"],
            "questions": rep["questions"],
        })

    return {
        "title": "Complete Joint Alignment Report",
        "subtitle": "Complete Family View",
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "prepared_by": user_name,
        "children": sorted(set(children)),
        "totals": totals,
        "totals_note": "These numbers are not scores. They are a roadmap for conversation.",
        "sections": sections,
        "is_empty": not sections,
        "empty_note": "No completed assessments from both parents are available yet. Complete an assessment or a Focused Joint Report first, then return here.",
        "purpose": (
            "This report brings together all available completed assessments from both parents "
            "into one comprehensive child-focused view. It is not designed to determine which "
            "parent is right or wrong."
        ),
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy": "We value the parenting system by how well it supports the child, not by how friendly the adults appear.",
        "philosophy_note": "You don't have to see everything the same way to begin working toward meeting your child's needs.",
    }
