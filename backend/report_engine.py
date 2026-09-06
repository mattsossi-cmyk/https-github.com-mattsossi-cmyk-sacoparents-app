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


def _analyze_topics(cfg, ra, rb):
    results = []
    for t in cfg["topics"]:
        av = ra["answers"].get(t["key"])
        bv = rb["answers"].get(t["key"])
        results.append({
            "key": t["key"],
            "label": t["label"],
            "aligned_text": t["aligned_text"],
            "action_phrase": t["action_phrase"],
            "child_need": t["child_need"],
            "parent_a": av or UNSURE,
            "parent_b": bv or UNSURE,
            "status": compute_status(av, bv),
        })
    buckets = {
        "aligned": [t for t in results if t["status"] == "aligned"],
        "close": [t for t in results if t["status"] == "close"],
        "different": [t for t in results if t["status"] == "different"],
        "info": [t for t in results if t["status"] == "info"],
    }
    buckets["conversation"] = buckets["close"] + buckets["different"]
    return results, buckets


def _priority_statement(cfg, buckets):
    focus_source = buckets["different"][0] if buckets["different"] else (
        buckets["close"][0] if buckets["close"] else (buckets["info"][0] if buckets["info"] else None)
    )
    focus = focus_source["label"].lower() if focus_source else "maintaining the child's current stability"
    return cfg["priority_statement"].replace("{focus}", focus)


def _build_questions(cfg, conversation):
    questions = [
        f"What information would help both parents determine whether {t['action_phrase']} would benefit the child?"
        for t in conversation[:4]
    ]
    if not questions:
        questions.append(cfg["central_question"])
    return questions


def _build_action_plan(buckets):
    return [
        {
            "issue": t["label"],
            "child_need": t["child_need"],
            "already_agree": buckets["aligned"][0]["aligned_text"] if buckets["aligned"] else "",
        }
        for t in (buckets["conversation"] + buckets["info"])[:3]
    ]


def _build_summary(cfg, buckets, priority):
    return {
        "aligned": [t["aligned_text"] for t in buckets["aligned"]][:5],
        "info": [f"Additional information about {t['label'].lower()} may help both parents." for t in buckets["info"]][:4],
        "conversation": [f"Parents view {t['label'].lower()} differently and may benefit from a structured conversation." for t in buckets["conversation"]][:4],
        "options": cfg["options"][:6],
        "priority": priority,
    }


def _build_court_map(case_type, buckets):
    if case_type != "court":
        return None
    return {
        "agreed": [t["label"] for t in buckets["aligned"]],
        "close": [t["label"] for t in buckets["close"]],
        "discussion": [t["label"] for t in buckets["different"]],
        "info": [t["label"] for t in buckets["info"]],
    }


def _perspective_sections(cfg: dict, ra: dict, rb: dict, aligned: list, conversation: list, buckets: dict) -> dict:
    return {
        "shared_goals": ra.get("goals") or rb.get("goals") or [],
        "parent_a_concern": ra.get("primary_concern", ""),
        "parent_b_concern": rb.get("primary_concern", ""),
        "alignments": [{"topic": t["label"], "text": t["aligned_text"]} for t in aligned],
        "alignment_foundation_note": ALIGNMENT_FOUNDATION_NOTE,
        "differences": [{"topic": t["label"], "parent_a": t["parent_a"], "parent_b": t["parent_b"]} for t in conversation],
        "differences_note": DIFFERENCES_NOTE,
        "professional_map": {
            "alignment_count": len(aligned),
            "conversation_count": len(conversation),
            "professional_input_count": len(buckets["info"]),
            "child_needs_count": len(cfg["needs"]),
            "sequence": DISCUSSION_SEQUENCE,
        },
    }


def generate_report(case: dict) -> dict:
    cfg = ASSESSMENT_TYPES[case["type"]]
    ra = case["responses"]["a"]
    rb = case["responses"]["b"]

    topic_results, buckets = _analyze_topics(cfg, ra, rb)
    aligned = buckets["aligned"]
    conversation = buckets["conversation"]

    snapshot = {
        "total": len(topic_results),
        "aligned": len(aligned),
        "different": len(conversation),
        "info": len(buckets["info"]),
    }
    priority = _priority_statement(cfg, buckets)

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
        **_perspective_sections(cfg, ra, rb, aligned, conversation, buckets),
        "central_question": cfg["central_question"],
        "child_needs": cfg["needs"],
        "options": cfg["options"],
        "options_note": "These are not recommendations. They are options for parents to explore.",
        "conversation_questions": _build_questions(cfg, conversation),
        "action_plan": _build_action_plan(buckets),
        "summary": _build_summary(cfg, buckets, priority),
        "court_map": _build_court_map(case["type"], buckets),
        "topic_results": topic_results,
        "philosophy": PHILOSOPHY,
        "philosophy_heading": "Alignment Before Agreement",
        "philosophy_note": "You don't have to see everything the same way to begin working toward meeting your child's needs.",
    }
