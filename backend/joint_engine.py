import re
from datetime import datetime, timezone

from joint_data import QUESTIONS, NEXT_STEPS, merged_subject_config, SAFETY_CONFIDENTIALITY, SAFETY_PURPOSE, AGREEMENT_AREAS, AGREEMENT_SECTIONS, AGREEMENT_PURPOSE, AGREEMENT_CONFIDENTIALITY

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


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def _pair_agrees(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return _norm(a) == _norm(b) or len(shared_terms(a, b)) >= 2


def _rule_section(sec: dict, ra: dict, rb: dict) -> dict:
    """Rule-based draft: matching follow-up answers become clauses, differing ones become open issues."""
    specific, open_issues, roles = [], [], {"communication_method": None, "decision_process": None, "review_trigger": None}
    for fk, prompt in sec["follow_ups"]:
        a, b = ra.get(f"{sec['key']}__{fk}", ""), rb.get(f"{sec['key']}__{fk}", "")
        short = prompt.rstrip("?")
        if not a and not b:
            continue
        if _pair_agrees(a, b):
            clause = f"{short}: {a.strip()}"
            specific.append(clause)
            for role, rk in (("communication_method", sec.get("comm")), ("decision_process", sec.get("decision")), ("review_trigger", sec.get("review"))):
                if rk == fk:
                    roles[role] = a.strip()
        elif a and b:
            open_issues.append(f"{short} — the parents' answers differ and need discussion.")
        else:
            open_issues.append(f"{short} — only one parent answered; confirm together.")
    return {"specific": specific, "open_issues": open_issues, **roles}


def _section_status(alignment: list, specific: list, open_issues: list) -> str:
    if open_issues and not specific:
        return "Requires resolution"
    if open_issues:
        return "Partly agreed"
    return "Agreed" if specific or len(alignment) >= 2 else "Aligned in principle"


def _agreement_section(sec: dict, ra: dict, rb: dict, ai: dict) -> dict:
    k = sec["key"]
    common = shared_terms(ra.get(k, ""), rb.get(k, ""))
    rule = _rule_section(sec, ra, rb)
    drafted = ai.get(k) if isinstance(ai.get(k), dict) else None
    merged = {**rule, **{kk: vv for kk, vv in drafted.items() if vv or kk in ("specific", "open_issues")}} if drafted else rule
    if drafted:
        merged["specific"] = [c for c in merged["specific"] if c not in merged["open_issues"]]
    alignment = [f"Both parents' proposals point the same direction — shared themes: {', '.join(common[:5])}."] if common else []
    specific, open_issues = merged.get("specific") or [], merged.get("open_issues") or []
    return {"key": k, "num": sec["num"], "label": sec["label"], "shared_goal": sec["goal"], "current_alignment": alignment, "parent_a": ra.get(k, ""), "parent_b": rb.get(k, ""),
            "specific_agreements": specific, "open_issues": open_issues, "communication_method": merged.get("communication_method"), "decision_process": merged.get("decision_process"),
            "review_trigger": merged.get("review_trigger"), "status": _section_status(alignment, specific, open_issues)}


def _agreement_summary(sections: list) -> dict:
    return {"alignment": [f"{s['label']}: {a}" for s in sections for a in s["current_alignment"]],
            "specific": [f"{s['label']}: {c}" for s in sections for c in s["specific_agreements"]],
            "resolution": [f"{s['label']}: {o}" for s in sections for o in s["open_issues"]]}


def generate_agreement(doc: dict) -> dict:
    child = doc.get("child_name") or "the child"
    pa = doc["participants"]["a"].get("name") or "Parent A"
    pb = doc["participants"]["b"].get("name") or "Parent B"
    ra = doc["responses"]["a"]["answers"]
    rb = doc["responses"]["b"]["answers"]
    ai = (doc.get("agreement_ai") or {}).get("sections") or {}
    sections = [_agreement_section(sec, ra, rb, ai) for sec in AGREEMENT_SECTIONS]
    return {
        "report_title": "SA CoParents Co-Parenting Agreement",
        "child_name": child, "parent_a_name": pa, "parent_b_name": pb,
        "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "purpose": AGREEMENT_PURPOSE, "confidentiality_note": AGREEMENT_CONFIDENTIALITY,
        "ai_drafted": bool(ai),
        "sections": sections,
        "summary": _agreement_summary(sections),
        "terms": [_agreement_term(key, label, ra, rb) for key, label, _q in AGREEMENT_AREAS],
        "foundation_statements": _foundation_entries(doc, pa, pb),
        "next_note": (
            "Items under 'Issues Still Requiring Resolution' are not agreements. They are candidates for parent conversation, "
            "SA CoParents reflection tools, professional consultation, or mediation before this document is finalized. "
            "Consider having an appropriate professional review any final agreement."
        ),
        "method_note": "Reflection → Alignment → Specific Action → Agreement",
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy": "We value the parenting system by how well it supports the child, not by how friendly the adults appear.",
    }


def _foundation_entries(doc: dict, pa: str, pb: str) -> list:
    entries = []
    for side, name in (("a", pa), ("b", pb)):
        for s in (doc["responses"].get(side) or {}).get("foundation") or []:
            entries.append({"parent": name, "title": s.get("title", "Foundation Statement"), "content": s.get("content", "")})
    return entries


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

SAMPLE_PURPOSE = (
    "This sample report shows how SA CoParents Align compares the independently provided "
    "perspectives of both parents. It identifies areas of alignment, differences in "
    "perspective, the child's identified needs, and neutral options for professional-guided "
    "discussion. It is not designed to determine which parent is right or wrong. The names "
    "and answers in this sample are fictional."
)

SAMPLE_SCENARIOS: dict[str, dict] = {
    "co_parenting": {
        "subject": "co_parenting", "label": "General Co-Parenting", "title": "Sample General Co-Parenting Report",
        "description": "Routines, rules, and day-to-day decisions across both homes.",
        "child": "Maya", "pa": "Alex R.", "pb": "Sam R.",
        "answers_a": {
            "needs_most": "Maya needs predictable weekly routines and parents who present united expectations in both homes.",
            "working_well": "Bedtime is consistent and we both follow through on agreements about discipline.",
            "concerns": "Screen-time rules and weekend plans often change without discussion.",
            "improve": "A shared calendar and agreed house rules that stay consistent.",
            "options": "Shared calendar, written house rules both homes follow, and monthly co-parenting check-ins.",
            "other_parent": "Sam may be concerned that strict routines limit spontaneity with Maya.",
        },
        "answers_b": {
            "needs_most": "Maya needs consistent expectations and relaxed, quality time in both homes.",
            "working_well": "We agree on bedtime and school-night expectations, which keeps Maya settled.",
            "concerns": "I find the rigid schedule hard when family events come up on weekends.",
            "improve": "More flexibility on special occasions while keeping core routines consistent.",
            "options": "Core rules plus agreed flexibility for special occasions, shared calendar, monthly check-in call.",
            "other_parent": "Alex may worry that exceptions make the schedule unpredictable for Maya.",
        },
    },
    "communication": {
        "subject": "communication", "label": "Communication", "title": "Sample Communication Report",
        "description": "How parents share information, updates, and everyday messages.",
        "child": "Ethan", "pa": "Robin T.", "pb": "Jamie T.",
        "answers_a": {
            "needs_most": "Ethan needs calm, respectful communication between his parents and timely updates about his day-to-day life.",
            "working_well": "We both respond to school messages and share updates about Ethan's homework.",
            "concerns": "Reply delays and terse text messages create confusion about Ethan's schedule.",
            "improve": "I would like a shared communication app and weekly summary updates.",
            "options": "A co-parenting app, weekly email summaries, or brief scheduled phone calls.",
            "other_parent": "Jamie may worry that frequent messages feel overwhelming.",
        },
        "answers_b": {
            "needs_most": "Ethan needs predictable routines and parents who communicate respectfully about his needs.",
            "working_well": "School updates reach both of us and homework information is shared.",
            "concerns": "Long message threads and delayed replies make planning difficult.",
            "improve": "Shorter, structured weekly updates and a shared calendar.",
            "options": "A shared calendar, weekly summary email, and keeping texts brief and child-focused.",
            "other_parent": "Robin may be concerned about not receiving enough detail about Ethan's week.",
        },
    },
    "education": {
        "subject": "education", "label": "Educational Needs", "title": "Sample Educational Needs Report",
        "description": "School, homework, tutoring, and academic support alignment.",
        "child": "Sofia", "pa": "Pat L.", "pb": "Devon L.",
        "answers_a": {
            "needs_most": "Sofia needs consistent homework routines and support with math tutoring in both homes.",
            "working_well": "Parent-teacher communication reaches both of us and school pickup runs smoothly.",
            "concerns": "Sofia's reading practice is inconsistent between homes and tutoring attendance has slipped.",
            "improve": "A shared homework log and agreement on the tutoring schedule.",
            "options": "Option A: shared homework log. Option B: tutor updates copied to both parents.",
            "other_parent": "Devon may be concerned about the cost and time commitment of tutoring.",
        },
        "answers_b": {
            "needs_most": "Sofia needs steady reading practice and encouragement with homework every school night.",
            "working_well": "We both attend school meetings and teacher updates are shared promptly.",
            "concerns": "I worry homework routines differ between homes, which confuses Sofia.",
            "improve": "Consistent homework expectations and a shared log both homes follow.",
            "options": "A shared homework log, monthly teacher check-ins, and a tutor both homes support.",
            "other_parent": "Pat may worry that too much academic pressure affects Sofia's confidence.",
        },
    },
    "medical": {
        "subject": "medical", "label": "Medical Needs", "title": "Sample Medical Needs Report",
        "description": "Healthcare routines, medication, appointments, and care decisions.",
        "child": "Noah", "pa": "Riley K.", "pb": "Morgan K.",
        "answers_a": {
            "needs_most": "Noah needs his asthma medication routine followed consistently in both homes.",
            "working_well": "Pediatrician appointment summaries are shared and both of us attend key visits.",
            "concerns": "Medication refills and inhaler checks sometimes fall through the cracks during exchanges.",
            "improve": "A shared medication log and a clear handoff checklist at exchanges.",
            "options": "Shared medication log, joint pediatrician portal access, and an exchange-day health checklist.",
            "other_parent": "Morgan may be concerned about over-medicalizing minor symptoms.",
        },
        "answers_b": {
            "needs_most": "Noah needs consistent medication routines and calm responses when his asthma flares.",
            "working_well": "We both keep the pediatrician informed and share appointment outcomes.",
            "concerns": "I worry the inhaler is not always checked before Noah's weekend transitions.",
            "improve": "A simple checklist for medication and inhaler checks at every exchange.",
            "options": "Exchange checklist, shared pharmacy account, and an agreed asthma action plan.",
            "other_parent": "Riley may worry that differing routines confuse Noah about his care.",
        },
    },
    "psychological": {
        "subject": "psychological", "label": "Psychological Needs", "title": "Sample Psychological Needs Report",
        "description": "Emotional wellbeing, counseling, and support strategies.",
        "child": "Liam", "pa": "Avery S.", "pb": "Quinn S.",
        "answers_a": {
            "needs_most": "Liam needs emotional reassurance and consistent responses when he feels anxious about transitions.",
            "working_well": "We both encourage Liam to talk about his feelings and keep his counselor informed.",
            "concerns": "Liam's anxiety seems to spike before exchanges, and our responses differ between homes.",
            "improve": "Aligned calming routines and shared guidance from Liam's counselor.",
            "options": "Joint counselor guidance, an aligned bedtime calming routine, and a feelings journal that travels with Liam.",
            "other_parent": "Quinn may be concerned about labeling Liam's feelings too early.",
        },
        "answers_b": {
            "needs_most": "Liam needs predictable emotional support and adults who respond calmly to his worries.",
            "working_well": "Both homes keep counseling appointments and share the counselor's recommendations.",
            "concerns": "I notice Liam becomes withdrawn after tense handoffs between us.",
            "improve": "Calmer, brief handoffs and a shared approach to reassurance.",
            "options": "A counselor-guided plan, brief positive handoffs, and a shared feelings journal.",
            "other_parent": "Avery may worry that too much focus on anxiety makes Liam more self-conscious.",
        },
    },
    "safety": {
        "subject": "safety", "label": "Safety / Family Violence", "title": "Sample Safety-Focused Self-Assessment Report (Controlled Preview)",
        "description": "Professional-mediated self-assessment: each parent answers privately and only the professional sees both. Not a Joint Assessment — controlled preview of the safety report format.",
        "safety": True,
        "child": "the child", "pa": "Parent A", "pb": "Parent B",
        "answers_a": {
            "needs_most": "The child needs exchanges to happen in a neutral, public location with clear start and end times.",
            "working_well": "The current supervised exchange protocol is being followed and documented by both households.",
            "concerns": "Unplanned contact outside the agreed protocol creates uncertainty about safety arrangements.",
            "improve": "Continued use of the supervised exchange center and written-only communication through the agreed channel.",
            "options": "Supervised exchange center, written-only communication channel, and professional review of the safety plan.",
            "other_parent": "The other parent likely wants predictability and clear boundaries around contact.",
        },
        "answers_b": {
            "needs_most": "The child needs calm, structured exchanges and no exposure to adult disagreements.",
            "working_well": "Written communication through the agreed channel is working and exchanges are documented.",
            "concerns": "I would like the exchange schedule confirmed further in advance to reduce last-minute stress.",
            "improve": "Advance confirmation of exchange times and continued professional oversight.",
            "options": "Supervised exchanges, advance schedule confirmation, and periodic professional review.",
            "other_parent": "The other parent likely shares the goal of keeping exchanges calm and predictable.",
        },
    },
}


def sample_report(key: str) -> dict | None:
    if key == "mediation":
        return sample_mediation_report()
    sc = SAMPLE_SCENARIOS.get(key)
    if sc is None:
        return None
    doc = {
        "subject": sc["subject"],
        "subjects": [sc["subject"]],
        "subject_label": sc["label"],
        "child_name": sc["child"],
        "is_safety": bool(sc.get("safety")),
        "participants": {"a": {"name": sc["pa"]}, "b": {"name": sc["pb"]}},
        "responses": {"a": {"answers": sc["answers_a"]}, "b": {"answers": sc["answers_b"]}},
    }
    report = generate_joint_report(doc)
    report["report_title"] = sc["title"]
    report["is_sample"] = True
    if sc.get("safety"):
        report["purpose"] = f"{report['purpose']} The names and answers in this sample are fictional."
    else:
        report["purpose"] = SAMPLE_PURPOSE
    return report


def sample_list() -> list:
    out = [
        {"key": k, "label": v["label"], "description": v["description"], "is_safety": bool(v.get("safety"))}
        for k, v in SAMPLE_SCENARIOS.items()
    ]
    out.append({
        "key": "mediation", "label": "Mediation Statement",
        "description": "Pre-mediation comparison statement for session preparation.", "is_safety": False,
    })
    return out

