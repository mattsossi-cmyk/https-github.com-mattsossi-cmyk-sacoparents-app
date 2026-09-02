import re
from datetime import datetime, timezone

from joint_data import SUBJECTS, QUESTIONS, NEXT_STEPS

STOPWORDS = set(
    "the a an and or of to in for with on at is are was were be been being this that these those "
    "it its as by from your you their our we i my me he she his her they them him his hers do does "
    "did have has had will would should could can may might must just really very more most right "
    "now about when how what which who whom not no yes but if then than so such own same also "
    "child child's children kid kids parent parents need needs".split()
)

PURPOSE_TEXT = (
    "This report compares the independently provided perspectives of both parents. It is designed "
    "to identify areas of shared understanding, differences in perspective, and subjects that may "
    "benefit from additional discussion or professional assistance. It is not designed to determine "
    "which parent is right or wrong."
)

REFRAME_TEMPLATE = (
    "Both parents agree that this subject matters for {child}. The difference concerns how the "
    "shared goal should be accomplished, rather than the underlying goal itself."
)


def keywords(text):
    words = re.findall(r"[a-z']+", (text or "").lower())
    return [w for w in words if len(w) > 3 and w not in STOPWORDS]


def shared_terms(a, b):
    ka = set(keywords(a))
    kb = set(keywords(b))
    return sorted(ka & kb)


def generate_joint_report(doc):
    cfg = SUBJECTS[doc["subject"]]
    subject_label = doc["subject_label"]
    child = doc.get("child_name") or "the child"
    ra = doc["responses"]["a"]["answers"]
    rb = doc["responses"]["b"]["answers"]
    pa = doc["participants"]["a"].get("name") or "Parent A"
    pb = doc["participants"]["b"].get("name") or "Parent B"

    alignment_rows = []
    alignment_statements = []
    differences = []
    for key, area, question in QUESTIONS:
        common = shared_terms(ra.get(key, ""), rb.get(key, ""))
        if len(common) >= 2:
            status = "Strong alignment"
        elif len(common) == 1:
            status = "Moderate alignment"
        else:
            status = "Needs discussion"
        alignment_rows.append({"area": area, "status": status})
        if common:
            alignment_statements.append(
                f"Both parents mentioned \"{', '.join(common[:3])}\" when describing {area.lower()}."
            )
        else:
            differences.append({
                "area": area,
                "parent_a": ra.get(key, ""),
                "parent_b": rb.get(key, ""),
                "reframe": REFRAME_TEMPLATE.replace("{child}", child),
            })

    if not alignment_statements:
        alignment_statements = [
            f"Both parents chose to participate regarding {subject_label.lower()} for {child} — "
            "participation itself reflects a shared commitment to the child."
        ]

    paragraph = (
        f"Both parents appear aligned around the goal of supporting {child} regarding "
        f"{subject_label.lower()}. Although they currently describe different perspectives in some "
        f"areas, both parents agree that {child}'s needs come first and that working toward a "
        "shared understanding is worthwhile."
    )

    return {
        "report_title": "Joint Parenting Alignment Report",
        "subject_label": subject_label,
        "child_name": child,
        "parent_a_name": pa,
        "parent_b_name": pb,
        "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "purpose": PURPOSE_TEXT,
        "alignment_statements": alignment_statements,
        "differences": differences,
        "child_needs": cfg["needs"],
        "alignment_map": alignment_rows,
        "conversation": cfg["conversation"],
        "options": cfg["options"],
        "alignment_paragraph": paragraph,
        "questions": cfg["questions"],
        "next_steps": NEXT_STEPS,
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy": "We value the parenting system by how well it supports the child, not by how friendly the adults appear.",
        "philosophy_note": "You don't have to see everything the same way to begin working toward meeting your child's needs.",
    }
