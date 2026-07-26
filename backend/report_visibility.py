"""Shared section catalog + visibility helpers for user-controlled selective
sharing across the four report types:

  - summary   (Mediation Summary)
  - agreement (Co-Parenting Agreement Draft)
  - sn_report (Special Needs 6-part care plan)
  - safety    (Family Violence & Communication Safety Assessment)

Each report exposes a fixed list of section keys the user can hide before
downloading a PDF or generating a share link. Section labels/descriptions
below are the human-readable copy shown in the UI.

Design:
  - Section keys are stable slugs — safe to persist in Mongo + JWT tokens.
  - `SAFETY_LOCKED_SECTIONS` cannot be hidden (e.g. Texas hotlines) so that
    a distributed link never accidentally strips a survivor's crisis resources.
  - Filtering is pure: give it a doc + excluded set → get a shallow-copy back.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Set


# ---- Catalog ---------------------------------------------------------------
REPORT_SECTIONS: Dict[str, List[Dict[str, str]]] = {
    "summary": [
        {"key": "readiness",         "label": "Readiness banner",               "description": "Your overall readiness score and the four dimension bars."},
        {"key": "changes_since_last","label": "What's changed since last time", "description": "Coach narrative comparing this run to your previous summary."},
        {"key": "child_goals",       "label": "Child-Centered Goals",           "description": "The goals you named for your child."},
        {"key": "top_concerns",      "label": "Top concerns",                   "description": "The concerns you flagged during prep."},
        {"key": "priority_agenda",   "label": "Priority agenda",                "description": "Your ranked mediation topics."},
        {"key": "flexibility_areas", "label": "Flexibility areas",              "description": "Areas you are open to negotiating."},
        {"key": "communication_goals","label": "Communication goals",           "description": "How you want to communicate during and after mediation."},
        {"key": "notes_for_mediator","label": "Notes for the mediator",         "description": "Free-text context you want the mediator to see."},
    ],
    "agreement": [
        {"key": "changes_since_last","label": "Updates from the previous draft","description": "What changed between this version and the last."},
        {"key": "shared_goals",      "label": "Shared goals for our child",     "description": "Common ground goals."},
        {"key": "communication",     "label": "Communication clauses",          "description": "Proposed communication ground rules."},
        {"key": "child_needs",       "label": "Child needs clauses",            "description": "Proposed care and support arrangements."},
        {"key": "household_rules",   "label": "Household rules clauses",        "description": "Proposed consistency between homes."},
        {"key": "priority_items",    "label": "Priority topics to discuss",     "description": "Ranked topics still open for mediation."},
        {"key": "open_for_discussion","label": "Open for discussion",           "description": "Items intentionally left unresolved for now."},
        {"key": "closing_note",      "label": "Closing note",                   "description": "A short signing-off note."},
    ],
    "sn_report": [
        {"key": "child_profile",     "label": "Child profile",                  "description": "Your child's strengths, what helps, and support needs."},
        {"key": "agreement_areas",   "label": "Areas of parent agreement",      "description": "Coordination areas where you and your co-parent already align."},
        {"key": "coordination_gaps", "label": "Coordination gaps",              "description": "Where information sharing or follow-through is breaking down."},
        {"key": "priorities",        "label": "Priority levels",                "description": "Immediate / within 30 days / longer-term action buckets."},
        {"key": "structure",         "label": "Recommended co-parenting structure","description": "Cooperative / Structured / Parallel narrative."},
        {"key": "action_plan",       "label": "Parenting-plan worksheet",       "description": "The action-table with responsible parent + review dates."},
    ],
    "safety": [
        {"key": "pathway",           "label": "Recommended communication pathway","description": "The pathway (No-direct / Structured written / Assisted / Cooperative) and rationale.", "locked": "true"},
        {"key": "section_1",         "label": "Section 1 answers (safety screen)","description": "Your Yes/No answers to the immediate safety questions."},
        {"key": "section_2",         "label": "Section 2 answers (readiness)",  "description": "Your answers to the communication-readiness questions."},
        {"key": "texas_resources",   "label": "Texas safety resources",         "description": "Crisis hotlines + DV shelter contacts.", "locked": "true"},
    ],
}


SAFETY_LOCKED_SECTIONS: Set[str] = {"pathway", "texas_resources"}


def valid_keys(report_type: str) -> Set[str]:
    return {s["key"] for s in REPORT_SECTIONS.get(report_type, [])}


def clean_excluded(report_type: str, excluded: Iterable[str] | None) -> List[str]:
    """Normalize the excluded list: strip unknown keys, strip locked keys.
    Returns a sorted stable list so the persisted / signed value is
    deterministic (useful for tests + share-token equality)."""
    if not excluded:
        return []
    allowed = valid_keys(report_type)
    locked: Set[str] = SAFETY_LOCKED_SECTIONS if report_type == "safety" else set()
    out = sorted({str(k) for k in excluded if k in allowed and k not in locked})
    return out


def is_excluded(key: str, excluded: Iterable[str] | None) -> bool:
    if not excluded:
        return False
    return key in set(excluded)


# ---- Filters ---------------------------------------------------------------
def _strip(d: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    out = dict(d)
    for k in keys:
        out.pop(k, None)
    return out


def filter_summary(summary: Dict[str, Any], excluded: Iterable[str] | None) -> Dict[str, Any]:
    if not excluded:
        return summary
    excluded = set(excluded)
    out = dict(summary)
    if "changes_since_last" in excluded:
        out["changes_since_last"] = ""
    if "top_concerns" in excluded:
        out["top_concerns"] = []
    if "priority_agenda" in excluded:
        out["priority_agenda"] = []
    if "flexibility_areas" in excluded:
        out["flexibility_areas"] = []
    if "communication_goals" in excluded:
        out["communication_goals"] = []
    if "notes_for_mediator" in excluded:
        out["notes_for_mediator"] = ""
    if "readiness" in excluded:
        # Signal to renderer to skip the readiness banner.
        out["_hide_readiness"] = True
    return out


def filter_agreement(agreement: Dict[str, Any], excluded: Iterable[str] | None) -> Dict[str, Any]:
    if not excluded:
        return agreement
    excluded = set(excluded)
    out = dict(agreement)
    if "changes_since_last" in excluded:
        out["changes_since_last"] = ""
    if "shared_goals" in excluded:
        out["shared_goals"] = []
    if "communication" in excluded:
        out["communication"] = []
    if "child_needs" in excluded:
        out["child_needs"] = []
    if "household_rules" in excluded:
        out["household_rules"] = []
    if "priority_items" in excluded:
        out["priority_items"] = []
    if "open_for_discussion" in excluded:
        out["open_for_discussion"] = []
    if "closing_note" in excluded:
        out["closing_note"] = ""
    return out


def filter_sn_report(report: Dict[str, Any], excluded: Iterable[str] | None) -> Dict[str, Any]:
    if not excluded:
        return report
    excluded = set(excluded)
    out = dict(report)
    if "child_profile" in excluded:
        out["child_profile"] = {}
    if "agreement_areas" in excluded:
        out["agreement_areas"] = []
    if "coordination_gaps" in excluded:
        out["coordination_gaps"] = []
    if "priorities" in excluded:
        out["priorities"] = {}
    if "structure" in excluded:
        out["structure_reasoning"] = ""
    if "action_plan" in excluded:
        out["action_plan"] = []
    return out
