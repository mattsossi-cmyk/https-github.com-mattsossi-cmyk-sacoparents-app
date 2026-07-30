"""Educational Deep Dive — rule-based concern & strength detection.

For every section we output:
    { "id", "name", "answered", "is_flagged", "flag_reasons", "is_strength",
      "strength_reasons", "answers_summary" }

Only flagged sections get the full "Concern / Recommendation" treatment in the
report. Strength sections still get a brief "What is going well" note.

Rules are conservative — a section only flags when the parent's own answers
show a meaningful gap. Missing answers never auto-flag.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional

from edu_deep_questions import DEEP_DIVE_SECTIONS, DECISION_TOPICS


LOW = 3   # likert < 3 = weakness signal (1-2 = disagree band)
HIGH = 4  # likert >= 4 = strength signal (4-5 = agree band)


def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and 1 <= v <= 5 else None


def _answers(section: Dict[str, Any], responses: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for iid in section["items"].keys():
        out[iid] = responses.get(f"{section['id']}_{iid}")
    return out


def _likerts(section: Dict[str, Any], responses: Dict[str, Any]) -> List[int]:
    xs = []
    for iid, spec in section["items"].items():
        if spec.get("type") == "likert":
            v = _int(responses.get(f"{section['id']}_{iid}"))
            if v is not None:
                xs.append(v)
    return xs


def _section_state(section: Dict[str, Any], responses: Dict[str, Any],
                   is_texas: bool) -> Dict[str, Any]:
    """Base state for a section including gate/texas visibility."""
    sid = section["id"]
    is_visible = True
    if section.get("texas_only") and not is_texas:
        is_visible = False
    gate = section.get("gate")
    if gate:
        gate_key = f"{sid}_{gate['item']}"
        if responses.get(gate_key) != gate["value"]:
            is_visible = False
    answers = _answers(section, responses)
    answered = any(v not in (None, "", []) for v in answers.values())
    return {
        "id": sid,
        "name": section["name"],
        "number": section["number"],
        "answered": answered,
        "is_visible": is_visible,
        "answers": answers,
    }


def _flag_low_likert_avg(xs: List[int], threshold: float = LOW) -> Optional[str]:
    if not xs:
        return None
    avg = mean(xs)
    return f"Average of {len(xs)} scored responses is {avg:.1f}." if avg < threshold else None


def _strength_high_likert_avg(xs: List[int], threshold: float = HIGH) -> Optional[str]:
    if not xs:
        return None
    avg = mean(xs)
    return f"Average of {len(xs)} scored responses is {avg:.1f}." if avg >= threshold else None


def _score_s1(state: Dict[str, Any], responses: Dict[str, Any]) -> None:
    """Educational Profile flags when many concern areas are checked."""
    concerns = state["answers"].get("concerns") or []
    if not state["is_visible"] or not state["answered"]:
        return
    if isinstance(concerns, list) and len(concerns) >= 5:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"{len(concerns)} educational concern areas selected — a broad concern set."
        )
    if isinstance(concerns, list) and 1 <= len(concerns) <= 2:
        state["is_strength"] = True
        state["strength_reasons"].append("Concerns are targeted rather than diffuse.")


def _score_s2(state, responses):
    xs = state["_likerts"]
    freq_map = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
    combined = list(xs)
    for iid in ("how_often_attend", "both_can_attend"):
        v = state["answers"].get(iid)
        if v in freq_map:
            combined.append(freq_map[v])
    low = _flag_low_likert_avg(combined)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    strong = _strength_high_likert_avg(combined)
    if strong:
        state["is_strength"] = True
        state["strength_reasons"].append("Both parents consistently engage with the teacher.")
    if state["answers"].get("both_receive_updates") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("Only one parent receives school updates.")


def _score_s3(state, responses):
    if not state["is_visible"]:
        return
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    if _int(state["answers"].get("conflict_interferes")) and _int(state["answers"].get("conflict_interferes")) >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append("Parent conflict is interfering with ARD decision making.")
    strong = _strength_high_likert_avg(xs)
    if strong:
        state["is_strength"] = True
        state["strength_reasons"].append("Both parents advocate together during ARD meetings.")


def _score_s4(state, responses):
    if not state["is_visible"]:
        return
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    strong = _strength_high_likert_avg(xs)
    if strong:
        state["is_strength"] = True
        state["strength_reasons"].append("Parents understand and reinforce IEP goals consistently.")


def _score_s5(state, responses):
    if not state["is_visible"]:
        return
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)


def _score_s6(state, responses):
    if not state["is_visible"]:
        return
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)


def _score_s7(state, responses):
    xs = state["_likerts"]
    supports = state["answers"].get("supports_enrolled") or []
    if isinstance(supports, list) and (not supports or supports == ["None"]):
        return  # nothing enrolled — nothing to score
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)


def _score_s8(state, responses):
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    strong = _strength_high_likert_avg(xs)
    if strong:
        state["is_strength"] = True
        state["strength_reasons"].append("Homework and home-learning routines are consistent.")


def _score_s9(state, responses):
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    same = state["answers"].get("same_information")
    if same in ("Rarely", "Never"):
        state["is_flagged"] = True
        state["flag_reasons"].append("Parents rarely receive the same information from the school.")


def _score_s10(state, responses):
    disagreement = 0
    for tid, _label in DECISION_TOPICS:
        v = state["answers"].get(tid)
        if v in ("Rarely Agree", "Never Agree"):
            disagreement += 1
    if disagreement >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append(f"{disagreement} decision areas rarely or never see agreement.")
    strong = sum(1 for tid, _l in DECISION_TOPICS
                 if state["answers"].get(tid) in ("Always Agree", "Usually Agree"))
    if strong >= 6:
        state["is_strength"] = True
        state["strength_reasons"].append(
            f"{strong} decision areas consistently see agreement."
        )


def _score_s11(state, responses):
    xs = state["_likerts"]
    low = _flag_low_likert_avg(xs)
    if low:
        state["is_flagged"] = True
        state["flag_reasons"].append(low)
    strong = _strength_high_likert_avg(xs)
    if strong:
        state["is_strength"] = True
        state["strength_reasons"].append("Parents advocate together with confidence.")


def _score_s12(state, responses):
    """Section 12 is informational only — never a flag."""
    return


_SECTION_SCORERS = {
    "s1": _score_s1, "s2": _score_s2, "s3": _score_s3, "s4": _score_s4,
    "s5": _score_s5, "s6": _score_s6, "s7": _score_s7, "s8": _score_s8,
    "s9": _score_s9, "s10": _score_s10, "s11": _score_s11, "s12": _score_s12,
}


def score_deep_dive(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Return per-section state plus roll-up counts and Texas flag."""
    is_texas = responses.get("s1_school_state") == "TX"
    per_section: List[Dict[str, Any]] = []
    total_answered = 0
    total_flagged = 0
    total_strengths = 0

    for section in DEEP_DIVE_SECTIONS:
        state = _section_state(section, responses, is_texas=is_texas)
        state["is_flagged"] = False
        state["flag_reasons"] = []
        state["is_strength"] = False
        state["strength_reasons"] = []
        # Special handling for s1 — the whole assessment counts as answered
        # whenever the profile is filled, but s1 is not a scored section.
        if state["is_visible"] and state["answered"]:
            state["_likerts"] = _likerts(section, responses)
            _SECTION_SCORERS[section["id"]](state, responses)
            state.pop("_likerts", None)
            total_answered += 1
            if state["is_flagged"]:
                total_flagged += 1
            if state["is_strength"]:
                total_strengths += 1
        per_section.append(state)

    return {
        "sections": per_section,
        "totals": {
            "answered": total_answered,
            "flagged": total_flagged,
            "strengths": total_strengths,
        },
        "is_texas": is_texas,
    }
