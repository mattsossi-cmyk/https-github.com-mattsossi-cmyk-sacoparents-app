"""Psychological Deep Dive — rule-based concern & strength detection."""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional

from psych_deep_questions import (
    COMM_TOPICS, CRISIS_AREAS, DECISION_TOPICS, DEEP_DIVE_SECTIONS,
    SUPPORT_AREAS, HOME_SUPPORT_AREAS,
)


LOW = 3
HIGH = 4

FREQ_MAP = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
CONFIDENCE_MAP = {"Very Confident": 5, "Confident": 4, "Neutral": 3,
                  "Somewhat Confident": 2, "Not Confident": 1}
CONSIST_MAP = {"Always Consistent": 5, "Usually Consistent": 4, "Sometimes Consistent": 3,
               "Rarely Consistent": 2, "Never Consistent": 1}
AGREE_MAP = {"Always Agree": 5, "Usually Agree": 4, "Sometimes Agree": 3,
             "Rarely Agree": 2, "Never Agree": 1}


def _int(v):
    return v if isinstance(v, int) and 1 <= v <= 5 else None


def _map_or_int(v, mapping):
    if v in mapping: return mapping[v]
    return _int(v)


def _flag_avg(xs: List[int], threshold: float = LOW) -> Optional[str]:
    if not xs: return None
    a = mean(xs)
    return f"Average of {len(xs)} responses is {a:.1f}." if a < threshold else None


def _strength_avg(xs: List[int], threshold: float = HIGH) -> Optional[str]:
    if not xs: return None
    a = mean(xs)
    return f"Average of {len(xs)} responses is {a:.1f}." if a >= threshold else None


def _state(section, responses):
    sid = section["id"]
    is_visible = True
    gate = section.get("gate")
    if gate:
        if responses.get(f"{sid}_{gate['item']}") != gate["value"]:
            is_visible = False
    answers = {iid: responses.get(f"{sid}_{iid}") for iid in section["items"].keys()}
    answered = any(v not in (None, "", []) for v in answers.values())
    return {
        "id": sid, "name": section["name"], "number": section["number"],
        "is_visible": is_visible, "answered": answered,
        "answers": answers, "is_flagged": False, "flag_reasons": [],
        "is_strength": False, "strength_reasons": [],
    }


# --- per-section scorers ---
def _s1(state, resp):
    dxs = state["answers"].get("diagnoses") or []
    # any active diagnosis (excluding meta options) is a signal
    active = [d for d in dxs if d not in
              ("No diagnosis", "Diagnosis pending", "Prefer not to answer")]
    if len(active) >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append(f"{len(active)} active diagnoses reported — coordination is important.")


def _s2(state, resp):
    freq_ids = ("both_know_provider", "attend_appointments", "both_receive_updates",
                "communicate_recs", "follow_recs_consistent")
    xs = [FREQ_MAP[state["answers"][k]] for k in freq_ids
          if state["answers"].get(k) in FREQ_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Both parents consistently coordinate around the provider.")


def _s3(state, resp):
    conf_ids = ("provider_understands", "confidence_plan", "trust_recommendations", "both_confident")
    xs = [CONFIDENCE_MAP[state["answers"][k]] for k in conf_ids
          if state["answers"].get(k) in CONFIDENCE_MAP]
    if state["answers"].get("discuss_respectfully") is not None:
        v = _int(state["answers"]["discuss_respectfully"])
        if v is not None:
            xs.append(v)
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Both parents express confidence in the provider.")


def _s4(state, resp):
    if not state["is_visible"]:
        return
    xs = [_int(state["answers"][k]) for k in
          ("administered_consistent", "communicate_changes", "refills_coordinated",
           "side_effects_discussed", "concerns_reported")
          if _int(state["answers"].get(k)) is not None]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    ua = state["answers"].get("understand_areas") or []
    if isinstance(ua, list) and len(ua) < 3:
        state["is_flagged"] = True
        state["flag_reasons"].append("Both parents understand fewer than 3 medication essentials.")


def _s5(state, resp):
    xs = [_int(state["answers"][k]) for k in
          ("both_support", "implemented_consistently", "child_participates", "outcomes_reviewed")
          if _int(state["answers"].get(k)) is not None]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Non-medication interventions are supported in both homes.")


def _s6(state, resp):
    if not state["is_visible"]:
        return
    xs = [_int(state["answers"][k]) for k in ("homework_completed", "strategies_reinforced")
          if _int(state["answers"].get(k)) is not None]
    if state["answers"].get("attendance_consistency") in FREQ_MAP:
        xs.append(FREQ_MAP[state["answers"]["attendance_consistency"]])
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Therapy participation and follow-through are strong.")


def _s7(state, resp):
    xs = [CONSIST_MAP[state["answers"][k]] for k in SUPPORT_AREAS_IDS()
          if state["answers"].get(k) in CONSIST_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Parenting strategies are consistent across most behavioural areas.")


def SUPPORT_AREAS_IDS():
    return ["anxiety", "emotional_regulation", "meltdowns", "anger", "transitions",
            "social_interactions", "school_stress", "peer_relationships", "self_esteem"]


def _s8(state, resp):
    planned = state["answers"].get("planned_areas") or []
    if isinstance(planned, list) and len(planned) < 3:
        state["is_flagged"] = True
        state["flag_reasons"].append("Fewer than 3 crisis areas have a shared plan.")
    if state["answers"].get("know_emergency_contacts") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("At least one parent does not know the emergency contacts.")
    if state["answers"].get("know_crisis_procedures") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("At least one parent does not know the crisis procedures.")
    if state["answers"].get("plan_in_writing") == "Yes" and len(planned) >= 5:
        state["is_strength"] = True
        state["strength_reasons"].append("A written crisis plan covers most critical areas.")


def _s9(state, resp):
    xs = [FREQ_MAP[state["answers"][tid]] for (tid, _l) in COMM_TOPICS
          if state["answers"].get(tid) in FREQ_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Parents talk about most treatment topics regularly.")


def _s10(state, resp):
    disagree = sum(1 for (tid, _l) in DECISION_TOPICS
                   if state["answers"].get(tid) in ("Rarely Agree", "Never Agree"))
    if disagree >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append(f"{disagree} decision areas rarely or never see agreement.")
    strong = sum(1 for (tid, _l) in DECISION_TOPICS
                 if state["answers"].get(tid) in ("Always Agree", "Usually Agree"))
    if strong >= 6:
        state["is_strength"] = True
        state["strength_reasons"].append(f"{strong} decision areas consistently see agreement.")


def _s11(state, resp):
    xs = [CONSIST_MAP[state["answers"][k]] for k in HOME_SUPPORT_AREA_IDS()
          if state["answers"].get(k) in CONSIST_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True; state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Both homes provide a consistent emotional foundation.")


def HOME_SUPPORT_AREA_IDS():
    return ["routines", "emotional_support", "positive_reinforcement", "calm_environment",
            "safe_expression", "consistent_expectations", "healthy_coping", "stress_reduction"]


SCORERS = {
    "s1": _s1, "s2": _s2, "s3": _s3, "s4": _s4, "s5": _s5,
    "s6": _s6, "s7": _s7, "s8": _s8, "s9": _s9, "s10": _s10, "s11": _s11,
}


def score_deep_dive(responses: Dict[str, Any]) -> Dict[str, Any]:
    per_section = []
    a = f = s = 0
    for section in DEEP_DIVE_SECTIONS:
        st = _state(section, responses)
        if st["is_visible"] and st["answered"]:
            SCORERS[section["id"]](st, responses)
            a += 1
            if st["is_flagged"]: f += 1
            if st["is_strength"]: s += 1
        per_section.append(st)
    return {
        "sections": per_section,
        "totals": {"answered": a, "flagged": f, "strengths": s},
    }
