import re
from datetime import datetime, timezone

from joint_data import SUBJECTS, QUESTIONS, NEXT_STEPS, merged_subject_config, SAFETY_CONFIDENTIALITY, SAFETY_PURPOSE, AGREEMENT_AREAS, AGREEMENT_PURPOSE, AGREEMENT_CONFIDENTIALITY

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


def _status_for(common):
    if len(common) >= 2:
        return "Strong alignment"
    if len(common) == 1:
        return "Moderate alignment"
    return "Needs discussion"


def _analyze_answers(ra, rb, child):
    rows, statements, differences = [], [], []
    for key, area, _question in QUESTIONS:
        common = shared_terms(ra.get(key, ""), rb.get(key, ""))
        rows.append({"area": area, "status": _status_for(common)})
        if common:
            statements.append(
                f"Both parents mentioned \"{', '.join(common[:3])}\" when describing {area.lower()}."
            )
        else:
            differences.append({
                "area": area,
                "parent_a": ra.get(key, ""),
                "parent_b": rb.get(key, ""),
                "reframe": REFRAME_TEMPLATE.replace("{child}", child),
            })
    return rows, statements, differences


def _alignment_statements(statements, subject_label, child):
    if statements:
        return statements
    return [
        f"Both parents chose to participate regarding {subject_label.lower()} for {child} — "
        "participation itself reflects a shared commitment to the child."
    ]


def _alignment_paragraph(subject_label, child):
    return (
        f"Both parents appear aligned around the goal of supporting {child} regarding "
        f"{subject_label.lower()}. Although they currently describe different perspectives in some "
        f"areas, both parents agree that {child}'s needs come first and that working toward a "
        "shared understanding is worthwhile."
    )


THEMES = {
    "Communication": ["communication", "communicate", "message", "talk", "inform", "share information", "update"],
    "Routine & Consistency": ["routine", "consistent", "consistency", "bedtime", "schedule", "predictable"],
    "School & Homework": ["school", "homework", "teacher", "education", "academic", "grades", "attendance", "tutor"],
    "Medical Care": ["medical", "doctor", "medication", "pediatrician", "health", "appointment"],
    "Emotional Wellbeing": ["emotional", "anxiety", "stress", "worried", "feelings", "therapy", "counselor"],
    "Exchanges & Transitions": ["exchange", "transition", "pickup", "pick-up", "dropoff", "drop-off"],
    "Conflict": ["conflict", "argument", "argue", "fight", "disagreement", "tension"],
    "Activities": ["activities", "sports", "extracurricular", "practice", "lessons"],
}


def _external_corpus(payload):
    texts = []
    for a in payload.get("assessments", []):
        texts.append(str(a.get("title", "")))
        for v in (a.get("responses") or {}).values():
            texts.append(str(v))
    for s in payload.get("statements", []):
        texts.append(str(s.get("title", "")))
        texts.append(str(s.get("content", "")))
    return " ".join(texts)


def _corpus(resp):
    if resp.get("imported"):
        return _external_corpus(resp.get("external") or {})
    return " ".join(resp.get("answers", {}).values())


def _theme_row(theme: str, in_a: bool, in_b: bool, pa: str, pb: str, child: str) -> tuple:
    if in_a and in_b:
        return {"area": theme, "status": "Strong alignment"}, f"Both parents' material addresses {theme.lower()}.", None
    if in_a or in_b:
        difference = {
            "area": theme,
            "parent_a": f"{theme} is addressed in {pa}'s material." if in_a else "Not addressed in the imported material.",
            "parent_b": f"{theme} is addressed in {pb}'s material." if in_b else "Not addressed in the imported material.",
            "reframe": REFRAME_TEMPLATE.replace("{child}", child),
        }
        return {"area": theme, "status": "Needs discussion"}, None, difference
    return None, None, None


def _theme_analysis(corpus_a: str, corpus_b: str, pa: str, pb: str, child: str) -> tuple:
    pres_a = {name: any(k in corpus_a.lower() for k in kws) for name, kws in THEMES.items()}
    pres_b = {name: any(k in corpus_b.lower() for k in kws) for name, kws in THEMES.items()}
    rows, statements, differences = [], [], []
    for theme in THEMES:
        row, statement, difference = _theme_row(theme, pres_a[theme], pres_b[theme], pa, pb, child)
        if row:
            rows.append(row)
        if statement:
            statements.append(statement)
        if difference:
            differences.append(difference)
    return rows, statements, differences


def generate_joint_report(doc: dict) -> dict:
    cfg = merged_subject_config(doc.get("subjects") or [doc["subject"]])
    subject_label = doc["subject_label"]
    child = doc.get("child_name") or "the child"
    resp_a = doc["responses"]["a"]
    resp_b = doc["responses"]["b"]
    pa = doc["participants"]["a"].get("name") or "Parent A"
    pb = doc["participants"]["b"].get("name") or "Parent B"
    imported = {"a": bool(resp_a.get("imported")), "b": bool(resp_b.get("imported"))}

    if imported["a"] or imported["b"]:
        rows, statements, differences = _theme_analysis(_corpus(resp_a), _corpus(resp_b), pa, pb, child)
    else:
        rows, statements, differences = _analyze_answers(resp_a["answers"], resp_b["answers"], child)

    return {
        "report_title": "Joint Parenting Alignment Report",
        "subject_label": subject_label,
        "child_name": child,
        "parent_a_name": pa,
        "parent_b_name": pb,
        "imported": imported,
        "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "is_safety": bool(doc.get("is_safety")),
        "confidentiality_note": SAFETY_CONFIDENTIALITY if doc.get("is_safety") else None,
        "purpose": SAFETY_PURPOSE if doc.get("is_safety") else PURPOSE_TEXT,
        "alignment_statements": _alignment_statements(statements, subject_label, child),
        "differences": differences,
        "child_needs": cfg["needs"],
        "alignment_map": rows,
        "conversation": cfg["conversation"],
        "options": cfg["options"],
        "alignment_paragraph": _alignment_paragraph(subject_label, child),
        "questions": cfg["questions"],
        "next_steps": NEXT_STEPS,
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy": "We value the parenting system by how well it supports the child, not by how friendly the adults appear.",
        "philosophy_note": "You don't have to see everything the same way to begin working toward meeting your child's needs.",
    }


def _agreement_term(key: str, label: str, ra: dict, rb: dict) -> dict:
    common = shared_terms(ra.get(key, ""), rb.get(key, ""))
    status = "Likely aligned" if len(common) >= 2 else ("Close" if len(common) == 1 else "Needs discussion")
    return {"key": key, "label": label, "parent_a": ra.get(key, ""), "parent_b": rb.get(key, ""), "status": status}


def _foundation_entries(doc: dict, pa: str, pb: str) -> list:
    entries = []
    for side, name in (("a", pa), ("b", pb)):
        for s in (doc["responses"].get(side) or {}).get("foundation") or []:
            entries.append({"parent": name, "title": s.get("title", "Foundation Statement"), "content": s.get("content", "")})
    return entries


def generate_agreement(doc: dict) -> dict:
    child = doc.get("child_name") or "the child"
    pa = doc["participants"]["a"].get("name") or "Parent A"
    pb = doc["participants"]["b"].get("name") or "Parent B"
    ra = doc["responses"]["a"]["answers"]
    rb = doc["responses"]["b"]["answers"]

    return {
        "report_title": "Joint Co-Parenting Agreement",
        "child_name": child,
        "parent_a_name": pa,
        "parent_b_name": pb,
        "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "purpose": AGREEMENT_PURPOSE,
        "confidentiality_note": AGREEMENT_CONFIDENTIALITY,
        "terms": [_agreement_term(key, label, ra, rb) for key, label, _question in AGREEMENT_AREAS],
        "foundation_statements": _foundation_entries(doc, pa, pb),
        "next_note": (
            "Areas marked 'Needs discussion' are candidates for parent conversation or mediation "
            "before finalizing. Consider having an appropriate professional review any final agreement."
        ),
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy": "We value the parenting system by how well it supports the child, not by how friendly the adults appear.",
    }


SAMPLE_MEDIATION_PURPOSE = (
    "This sample Mediation Statement shows how SA CoParents Align compares the independently "
    "provided perspectives of both parents before or during mediation. It identifies areas of "
    "alignment, differences in perspective, the child's identified needs, and neutral options "
    "and resources for discussion. It is not designed to determine which parent is right or "
    "wrong. The names and answers in this sample are fictional."
)


def sample_mediation_report() -> dict:
    answers_a = {
        "needs_most": "Avery needs a predictable routine and calm communication between both parents so she feels secure in both homes.",
        "working_well": "School pickup transitions are working well, and we both keep Avery's bedtime routine consistent.",
        "concerns": "Last-minute schedule changes and tense communication at exchanges are affecting Avery.",
        "improve": "I would like a shared calendar and a predictable weekly schedule with consistent bedtime in both homes.",
        "options": "I would consider a single mediation session, a shared calendar, and exchanging written proposals before meeting.",
        "other_parent": "The other parent may be concerned about flexibility for work travel and having enough quality time with Avery.",
    }
    answers_b = {
        "needs_most": "Avery needs predictable routines, calm communication, and flexibility when work travel requires schedule changes.",
        "working_well": "Bedtime routine is consistent in both homes, and school communication from teachers reaches both of us.",
        "concerns": "I worry the rigid weekly plan does not work with my job, and our handoffs have become strained.",
        "improve": "More flexibility around the weekly plan and calmer, more respectful communication during handoffs.",
        "options": "I would consider mediation, written proposals exchanged before the session, and a shared online calendar.",
        "other_parent": "Jordan may be concerned that too much flexibility makes the schedule unpredictable for Avery.",
    }
    doc = {
        "subject": "mediation",
        "subjects": ["mediation"],
        "subject_label": "Mediation Statement",
        "child_name": "Avery",
        "participants": {"a": {"name": "Jordan M."}, "b": {"name": "Casey M."}},
        "responses": {"a": {"answers": answers_a}, "b": {"answers": answers_b}},
    }
    report = generate_joint_report(doc)
    report["report_title"] = "Sample Mediation Statement"
    report["is_sample"] = True
    report["purpose"] = SAMPLE_MEDIATION_PURPOSE
    return report
