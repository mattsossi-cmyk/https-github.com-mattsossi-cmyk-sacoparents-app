"""Medical / Prescription Deep Dive — rule-based flag & strength detection."""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional

from med_deep_questions import (
    DEEP_DIVE_SECTIONS, DISAGREEMENT_TOPICS, PARENT_COMM_TOPICS,
)


LOW = 3
HIGH = 4

FREQ_MAP = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
CONSIST_MAP = {"Always Consistent": 5, "Usually Consistent": 4, "Sometimes Consistent": 3,
               "Rarely Consistent": 2, "Never Consistent": 1}
AGREE_MAP = {"Always Agree": 5, "Usually Agree": 4, "Sometimes Agree": 3,
             "Rarely Agree": 2, "Never Agree": 1}
YPN_MAP = {"Yes": 5, "Partial": 3, "No": 1}


def _int(v):
    return v if isinstance(v, int) and 1 <= v <= 5 else None


def _flag_avg(xs: List[int], threshold: float = LOW) -> Optional[str]:
    if not xs:
        return None
    a = mean(xs)
    return f"Average of {len(xs)} responses is {a:.1f}." if a < threshold else None


def _strength_avg(xs: List[int], threshold: float = HIGH) -> Optional[str]:
    if not xs:
        return None
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
        "risk_signals": [],
    }


def _s1(state, resp):
    a = state["answers"]
    shared = a.get("shared_info") or []
    if isinstance(shared, list) and len(shared) < 5:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"Both parents share only {len(shared)} of 8 core prescription details."
        )
    if a.get("written_med_list") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("No shared written medication list is currently maintained.")
    if a.get("both_receive_new_rx") in ("Rarely", "Never"):
        state["is_flagged"] = True
        state["flag_reasons"].append("New prescriptions are rarely communicated to both parents.")
    if a.get("written_med_list") == "Yes" and isinstance(shared, list) and len(shared) >= 7:
        state["is_strength"] = True
        state["strength_reasons"].append(
            "A current shared medication list is maintained and both parents know the essentials."
        )


def _s2(state, resp):
    a = state["answers"]
    issues = a.get("pickup_issues") or []
    non_null_issues = [i for i in issues if i != "No issues in the last 6 months"]
    if len(non_null_issues) >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"{len(non_null_issues)} pick-up problems reported in the last 6 months."
        )
    if any(x in issues for x in ("Missed pick-up so a dose was skipped",
                                  "Ran out before refill was picked up")):
        state["is_flagged"] = True
        state["risk_signals"].append("A missed pick-up has already caused missed doses.")
    xs = [FREQ_MAP[a[k]] for k in ("clear_assignment", "confirmation")
          if a.get(k) in FREQ_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True
        state["flag_reasons"].append(lo)
    if issues == ["No issues in the last 6 months"] and _strength_avg(xs):
        state["is_strength"] = True
        state["strength_reasons"].append("Pick-ups are assigned clearly and confirmed between parents.")


def _s3(state, resp):
    a = state["answers"]
    xs = [FREQ_MAP[a[k]] for k in ("supply_each_home", "refill_coordination", "expired_check")
          if a.get(k) in FREQ_MAP]
    if a.get("backup_supply") in YPN_MAP:
        xs.append(YPN_MAP[a["backup_supply"]])
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True
        state["flag_reasons"].append(lo)
    if a.get("runs_out_frequency") in ("2-3 times", "More than 3 times"):
        state["is_flagged"] = True
        state["risk_signals"].append(
            "Medication has run out multiple times in the last 6 months — this is a safety concern for daily and controlled medications."
        )
    if a.get("emergency_med_available") == "Only one home":
        state["is_flagged"] = True
        state["risk_signals"].append(
            "Rescue / emergency medication is available in only one home."
        )
    if a.get("emergency_med_available") == "No":
        state["is_flagged"] = True
        state["risk_signals"].append(
            "Rescue / emergency medication is not currently available — confirm with the prescriber whether the child needs one."
        )
    hi = _strength_avg(xs)
    if hi and a.get("emergency_med_available") in ("Yes in both", "Not applicable"):
        state["is_strength"] = True
        state["strength_reasons"].append("Supply is reliable and continuous in both homes.")


def _s4(state, resp):
    a = state["answers"]
    xs = []
    if a.get("same_schedule") in CONSIST_MAP:
        xs.append(CONSIST_MAP[a["same_schedule"]])
    for k in ("missed_doses_freq", "handoff_dose"):
        # missed_doses_freq is worded high=bad; invert
        if a.get(k) in FREQ_MAP:
            v = FREQ_MAP[a[k]]
            if k == "missed_doses_freq":
                v = 6 - v  # Always missed => low score
            xs.append(v)
    if a.get("dose_log") in YPN_MAP:
        xs.append(YPN_MAP[a["dose_log"]])
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True
        state["flag_reasons"].append(lo)
    if a.get("missed_doses_freq") in ("Always", "Usually"):
        state["is_flagged"] = True
        state["risk_signals"].append(
            "Doses are missed frequently — for daily maintenance, controlled, or seizure medications this is a safety issue."
        )
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Administration is consistent between homes with logging and handoff communication.")


def _s5(state, resp):
    a = state["answers"]
    xs = [FREQ_MAP[a[tid]] for (tid, _l) in PARENT_COMM_TOPICS if a.get(tid) in FREQ_MAP]
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True
        state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("Parents talk about most medication topics regularly.")
    # emergency_use rarely communicated is a specific safety flag
    if a.get("emergency_use") in ("Rarely", "Never"):
        state["is_flagged"] = True
        state["risk_signals"].append(
            "Use of rescue / emergency medication is rarely communicated to the other parent."
        )


def _s6(state, resp):
    a = state["answers"]
    xs = []
    m = {"Yes always": 5, "Usually": 4, "Sometimes": 3, "No": 1}
    if a.get("same_pharmacy") in m:
        xs.append(m[a["same_pharmacy"]])
    if a.get("both_authorized") == "Yes":
        xs.append(5)
    elif a.get("both_authorized") == "No":
        xs.append(1)
    if a.get("pharmacy_has_contacts") in YPN_MAP:
        xs.append(YPN_MAP[a["pharmacy_has_contacts"]])
    if a.get("pharmacist_alignment") in FREQ_MAP:
        xs.append(FREQ_MAP[a["pharmacist_alignment"]])
    lo = _flag_avg(xs)
    if lo:
        state["is_flagged"] = True
        state["flag_reasons"].append(lo)
    hi = _strength_avg(xs)
    if hi:
        state["is_strength"] = True
        state["strength_reasons"].append("The pharmacy pathway is coordinated across both homes.")


def _s7(state, resp):
    a = state["answers"]
    issues = a.get("financial_issues") or []
    real = [i for i in issues if i != "No financial barriers currently"]
    if real:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"{len(real)} financial or insurance barrier(s) currently affecting medication."
        )
    if any(x in real for x in ("Insurance denied / requires prior auth",
                                "One parent refuses to pay their share",
                                "Cash-pay cost is unaffordable")):
        state["risk_signals"].append(
            "A financial / insurance issue could interrupt medication continuity."
        )
    if a.get("cost_split_clear") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("The medication cost-split is not documented in writing.")
    if a.get("affordability") in ("Somewhat difficult", "A major barrier"):
        state["is_flagged"] = True
        state["flag_reasons"].append("Overall affordability is difficult.")
    if not real and a.get("cost_split_clear") == "Yes":
        state["is_strength"] = True
        state["strength_reasons"].append("No current financial barriers and the cost-split is documented.")


def _s8(state, resp):
    if not state["is_visible"]:
        return
    a = state["answers"]
    protections = a.get("protections") or []
    real = [p for p in protections if p != "No protections currently in place"]
    if len(real) < 3:
        state["is_flagged"] = True
        state["risk_signals"].append(
            f"Only {len(real)} of the controlled-medication safeguards are in place across both homes."
        )
    if a.get("count_tracking") == "No":
        state["is_flagged"] = True
        state["risk_signals"].append("Pill / dose count is not tracked at handoff.")
    if a.get("diversion_concerns") in ("Moderate concerns", "Significant concerns"):
        state["is_flagged"] = True
        state["risk_signals"].append("Concern about diversion or unauthorised access is reported.")
    if a.get("provider_agreement") == "No":
        state["is_flagged"] = True
        state["flag_reasons"].append("No controlled-substance / opioid agreement is on file with the prescriber.")
    if len(real) >= 4 and a.get("count_tracking") == "Yes":
        state["is_strength"] = True
        state["strength_reasons"].append("Controlled medication has multiple safeguards and tracked handoffs.")


def _s9(state, resp):
    if not state["is_visible"]:
        return
    a = state["answers"]
    items = a.get("school_items") or []
    real = [i for i in items if i != "None of the above"]
    if len(real) < 4:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"Only {len(real)} of the school medication elements are in place."
        )
    if a.get("both_on_paperwork") == "No":
        state["is_flagged"] = True
        state["risk_signals"].append("Only one parent is on the school medication paperwork.")
    if a.get("field_trip_ready") == "No":
        state["is_flagged"] = True
        state["risk_signals"].append("Medication is not authorised or packed for field trips.")
    if a.get("school_updates") in ("Rarely", "Never"):
        state["is_flagged"] = True
        state["flag_reasons"].append("School rarely reports administration to both parents.")
    if len(real) >= 6 and a.get("both_on_paperwork") == "Yes":
        state["is_strength"] = True
        state["strength_reasons"].append("School medication process is well documented and shared.")


def _s10(state, resp):
    a = state["answers"]
    disagree = sum(1 for (tid, _l) in DISAGREEMENT_TOPICS
                   if a.get(tid) in ("Rarely Agree", "Never Agree"))
    if disagree >= 3:
        state["is_flagged"] = True
        state["flag_reasons"].append(
            f"{disagree} medication decision areas rarely or never see agreement."
        )
    # Specific high-stakes disagreement
    for critical in ("whether_to_use", "dosing", "stopping_med", "controlled_use"):
        if a.get(critical) in ("Never Agree",):
            state["risk_signals"].append(
                "A high-stakes medication decision has no current agreement — plan a neutral pathway before the next refill."
            )
            break
    strong = sum(1 for (tid, _l) in DISAGREEMENT_TOPICS
                 if a.get(tid) in ("Always Agree", "Usually Agree"))
    if strong >= 5:
        state["is_strength"] = True
        state["strength_reasons"].append(
            f"{strong} of {len(DISAGREEMENT_TOPICS)} medication decision areas consistently see agreement."
        )


SCORERS = {
    "s1": _s1, "s2": _s2, "s3": _s3, "s4": _s4, "s5": _s5,
    "s6": _s6, "s7": _s7, "s8": _s8, "s9": _s9, "s10": _s10,
}


def score_deep_dive(responses: Dict[str, Any]) -> Dict[str, Any]:
    per_section = []
    a = f = s = risk = 0
    for section in DEEP_DIVE_SECTIONS:
        st = _state(section, responses)
        if st["is_visible"] and st["answered"]:
            SCORERS[section["id"]](st, responses)
            a += 1
            if st["is_flagged"]:
                f += 1
            if st["is_strength"]:
                s += 1
            if st["risk_signals"]:
                risk += 1
        per_section.append(st)
    return {
        "sections": per_section,
        "totals": {"answered": a, "flagged": f, "strengths": s, "risk_sections": risk},
    }
