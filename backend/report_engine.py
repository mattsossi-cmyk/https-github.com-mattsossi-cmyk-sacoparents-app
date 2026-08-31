from datetime import datetime, timezone

from assessment_data import (
    ASSESSMENT_TYPES,
    SCALE,
    UNSURE,
    PURPOSE_ITEMS,
    DIFFERENCES_NOTE,
    ALIGNMENT_FOUNDATION_NOTE,
    DISCUSSION_SEQUENCE,
    PHILOSOPHY,
)


def compute_status(a, b):
    if not a or not b or a == UNSURE or b == UNSURE:
        return "info"
    d = abs(SCALE.index(a) - SCALE.index(b))
    if d == 0:
        return "aligned"
    if d == 1:
        return "close"
    return "different"


def generate_report(case):
    cfg = ASSESSMENT_TYPES[case["type"]]
    ra = case["responses"]["a"]
    rb = case["responses"]["b"]

    topic_results = []
    for t in cfg["topics"]:
        av = ra["answers"].get(t["key"])
        bv = rb["answers"].get(t["key"])
        topic_results.append({
            "key": t["key"],
            "label": t["label"],
            "aligned_text": t["aligned_text"],
            "action_phrase": t["action_phrase"],
            "child_need": t["child_need"],
            "parent_a": av or UNSURE,
            "parent_b": bv or UNSURE,
            "status": compute_status(av, bv),
        })

    aligned = [t for t in topic_results if t["status"] == "aligned"]
    close = [t for t in topic_results if t["status"] == "close"]
    different = [t for t in topic_results if t["status"] == "different"]
    info = [t for t in topic_results if t["status"] == "info"]
    conversation = close + different

    snapshot = {
        "total": len(topic_results),
        "aligned": len(aligned),
        "different": len(conversation),
        "info": len(info),
    }

    focus_source = different[0] if different else (close[0] if close else (info[0] if info else None))
    focus = focus_source["label"].lower() if focus_source else "maintaining the child's current stability"
    priority = cfg["priority_statement"].replace("{focus}", focus)

    questions = []
    for t in conversation[:4]:
        questions.append(
            f"What information would help both parents determine whether {t['action_phrase']} would benefit the child?"
        )
    if not questions:
        questions.append(cfg["central_question"])
    if len(questions) < 2:
        questions.append(cfg["central_question"])

    plan_issues = conversation + info
    action_plan = []
    for t in plan_issues[:3]:
        action_plan.append({
            "issue": t["label"],
            "child_need": t["child_need"],
            "already_agree": aligned[0]["aligned_text"] if aligned else "",
        })

    shared_goals = ra.get("goals") or rb.get("goals") or []

    summary = {
        "aligned": [t["aligned_text"] for t in aligned][:5],
        "info": [f"Additional information about {t['label'].lower()} may help both parents." for t in info][:4],
        "conversation": [f"Parents view {t['label'].lower()} differently and may benefit from a structured conversation." for t in conversation][:4],
        "options": cfg["options"][:6],
        "priority": priority,
    }

    is_court = case["type"] == "court"
    court_map = None
    if is_court:
        court_map = {
            "agreed": [t["label"] for t in aligned],
            "close": [t["label"] for t in close],
            "discussion": [t["label"] for t in different],
            "info": [t["label"] for t in info],
        }

    return {
        "assessment_type": case["type"],
        "assessment_title": cfg["title"],
        "report_title": cfg["report_title"],
        "subtitle": f"Assessment: {cfg['subtitle']}",
        "child_name": case.get("child_name", ""),
        "parent_a_name": case.get("parent_a_name", "Parent A"),
        "parent_b_name": case.get("parent_b_name", "Parent B"),
        "parent_a_status": "Assessment completed",
        "parent_b_status": "Assessment completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": case.get("is_demo", False),
        "page_titles": cfg["page_titles"],
        "disclaimer": cfg["disclaimer"],
        "purpose_items": PURPOSE_ITEMS,
        "snapshot": snapshot,
        "snapshot_note": "These numbers are not scores. They are a roadmap for conversation.",
        "shared_goals": shared_goals,
        "parent_a_concern": ra.get("primary_concern", ""),
        "parent_b_concern": rb.get("primary_concern", ""),
        "central_question": cfg["central_question"],
        "alignments": [{"topic": t["label"], "text": t["aligned_text"]} for t in aligned],
        "alignment_foundation_note": ALIGNMENT_FOUNDATION_NOTE,
        "differences": [{"topic": t["label"], "parent_a": t["parent_a"], "parent_b": t["parent_b"]} for t in conversation],
        "differences_note": DIFFERENCES_NOTE,
        "child_needs": cfg["needs"],
        "options": cfg["options"],
        "options_note": "These are not recommendations. They are options for parents to explore.",
        "conversation_questions": questions,
        "professional_map": {
            "alignment_count": len(aligned),
            "conversation_count": len(conversation),
            "professional_input_count": len(info),
            "child_needs_count": len(cfg["needs"]),
            "sequence": DISCUSSION_SEQUENCE,
        },
        "action_plan": action_plan,
        "summary": summary,
        "court_map": court_map,
        "topic_results": topic_results,
        "philosophy": PHILOSOPHY,
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy_note": "You don't have to see everything the same way to begin working toward meeting your child's needs.",
    }
