"""Joint Co-Parenting Summary for Professional Review.

Pure aggregator (no DB, no HTTP). Given both parents' data + share id,
produces a neutral, section-by-section summary intended for handoff to
attorneys, mediators, and other professionals involved in the case.

Design commitments (intentional, enforced):
  * Never labels either parent as "correct", "wrong", or "uncooperative".
  * Never uses possession/access/custody language or makes recommendations
    to a court. Phrasing is always "the parents' responses indicate ..."
    or "the parents' responses align on ...".
  * Only Finding 3 (Parenting-Plan Implications) of the Trauma-Informed
    Safety and Functioning Lens is ever included; Findings 1 & 2 remain
    private to the survivor per the existing app-wide privacy stance.
  * The report is prep-material, not evaluation-material. This is stated
    on every surface and in the payload's `disclaimer` field.

Public API:
  * `build_joint_report(...)` — returns a dict with the shape documented
    in the JOINT REPORT SECTIONS block below. The route layer wraps a
    consent gate + Mongo reads around this function.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from snc2_comparison import ALIGNMENT_LABELS
from snc2_questions import PATHWAYS


# ---------------------------------------------------------------------------
# Disclaimer text — must appear at the top of the JSON payload AND on every
# rendered surface (HTML/PDF). Locked here to keep language identical.
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "This Joint Co-Parenting Summary is a preparation and communication "
    "resource compiled from both parents' self-reported answers. It is NOT "
    "a custody evaluation, forensic assessment, clinical diagnosis, expert "
    "opinion, or recommendation to any court. It does not evaluate either "
    "parent's fitness, credibility, or entitlement to any parenting time. "
    "Its purpose is to help attorneys, mediators, and other professionals "
    "understand where the parents' perceptions of their child's needs "
    "align, where they differ, and which topics may benefit from further "
    "professional discussion. Use of SA CoParents does not by itself "
    "create an attorney-client, therapist-patient, mediator-client, or "
    "other privileged relationship."
)

NEUTRAL_LANGUAGE_NOTE = (
    "Findings are phrased in neutral, non-adjudicative language. Where "
    "parents' responses differ, this report describes the difference "
    "without attributing blame or correctness to either parent."
)


# ---------------------------------------------------------------------------
# JOINT REPORT SECTIONS
# ---------------------------------------------------------------------------
#
# The report always returns the same 9 sections in the same order, even
# when a section is empty. Empty sections carry an `empty_reason` string
# so the UI can render a placeholder rather than hiding the section.
#
#   1. shared_priorities              — child-centered priorities both parents named
#   2. medical                        — medical needs (from SNC2 medical pathway)
#   3. educational                    — educational / IEP / 504 needs
#   4. psychological                  — psychological & emotional needs
#   5. household_consistency          — consistency between homes (Step 5 across all pathways)
#   6. communication_concerns         — communication & decision-making concerns
#   7. areas_of_agreement             — top items both parents endorsed
#   8. areas_where_perceptions_differ — largest divergences across all inputs
#   9. issues_for_professional_discussion — items likely to benefit from
#                                          mediation / professional support
#
# Each row inside a section is a NEUTRAL_ROW:
#   {
#       "topic":            "Consistency of medical routines between homes",
#       "parent_a":         {"summary": "...", "raw": ...},
#       "parent_b":         {"summary": "...", "raw": ...},
#       "alignment":        "aligned" | "close" | "divergent" | "one_only" | "insufficient" | "both_responded",
#       "alignment_label":  "Different views",
#       "childs_need":      "Predictable medication routines",
#       "issue_for_discussion": "The parents' responses indicate different perceptions ...",
#   }
# ---------------------------------------------------------------------------


# ---------- helpers ----------

_PATHWAY_NAME = {p["id"]: p["name"] for p in PATHWAYS}


def _pathway_label(pid: str) -> str:
    return _PATHWAY_NAME.get(pid, pid.title())


def _round(v: Any) -> Optional[float]:
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


def _summary_from_alignment(item: Dict[str, Any]) -> Dict[str, str]:
    """Turn an SNC2 comparison row into short neutral summaries for each parent."""
    t = item.get("type")
    a = item.get("parent_a") or {}
    b = item.get("parent_b") or {}
    if t == "likert":
        return {
            "parent_a": (a.get("label") or "No response"),
            "parent_b": (b.get("label") or "No response"),
        }
    if t == "single":
        return {
            "parent_a": (a.get("value") or "No response"),
            "parent_b": (b.get("value") or "No response"),
        }
    if t == "multi":
        return {
            "parent_a": ", ".join(a.get("value") or []) or "No selections",
            "parent_b": ", ".join(b.get("value") or []) or "No selections",
        }
    # text / textarea
    return {
        "parent_a": (a.get("value") or "").strip() or "No response",
        "parent_b": (b.get("value") or "").strip() or "No response",
    }


def _issue_phrase(topic: str, alignment: str, pathway: str) -> str:
    """Compose the neutral 'Issue for professional discussion' sentence.

    Deliberately worded to describe the difference (or agreement) without
    attributing correctness to either parent.
    """
    pw = _pathway_label(pathway).lower() if pathway else "this area"
    if alignment == "divergent":
        return (
            f"The parents' responses indicate a significant difference in "
            f"their perceptions regarding {topic.lower()} ({pw}). This "
            f"topic may benefit from professional discussion."
        )
    if alignment == "close":
        return (
            f"The parents' responses show a modest gap regarding "
            f"{topic.lower()} ({pw}). A short conversation with a "
            f"professional could align expectations."
        )
    if alignment == "one_only":
        return (
            f"Only one parent provided a response on {topic.lower()} "
            f"({pw}). A professional may wish to solicit the other "
            f"parent's perspective before drawing conclusions."
        )
    if alignment == "insufficient":
        return (
            f"Neither parent's response is complete enough to draw a "
            f"conclusion on {topic.lower()} ({pw})."
        )
    # aligned / both_responded
    return (
        f"The parents' responses align on {topic.lower()} ({pw}). "
        f"This is an area of established shared understanding."
    )


def _childs_need_for_item(pathway: str, item_id: str, prompt: str) -> str:
    """Map an SNC2 item to a short 'child's need' label.

    Uses the item's prompt trimmed to a short need-statement. Deliberately
    generic — the goal is to orient professionals, not diagnose.
    """
    # A few high-value mappings; anything else falls back to the prompt.
    mapping = {
        "current_impact": "Reduce disruption of daily life",
        "routines_consistent": "Predictable routines across both homes",
        "follow_recs": "Consistent follow-through on professional recommendations",
        "share_updates": "Timely exchange of health / school updates",
        "handoffs_reliable": "Reliable, low-friction handoffs",
        "carry_over_supplies": "Continuity of supplies / medication between homes",
        "same_info": "Both parents working from the same information",
        "shared_language": "Shared vocabulary for the child's needs",
        "believe_understood": "Both parents feel heard and understood",
        "discuss_openly": "Ability to discuss concerns openly",
        "attend_appts": "Coordinated attendance at appointments",
    }
    if item_id in mapping:
        return mapping[item_id]
    return prompt[:80] + ("..." if len(prompt) > 80 else "")


def _row_from_snc2_item(
    pathway: str, item: Dict[str, Any],
) -> Dict[str, Any]:
    """Turn a single SNC2 comparison item into a neutral report row."""
    summaries = _summary_from_alignment(item)
    alignment = item.get("alignment") or "insufficient"
    prompt = item.get("prompt") or ""
    topic = prompt.split(":")[0][:60] if prompt else item.get("id", "")
    return {
        "topic": topic,
        "prompt": prompt,
        "pathway": pathway,
        "pathway_label": _pathway_label(pathway),
        "parent_a": {"summary": summaries["parent_a"]},
        "parent_b": {"summary": summaries["parent_b"]},
        "alignment": alignment,
        "alignment_label": ALIGNMENT_LABELS.get(alignment, alignment),
        "childs_need": _childs_need_for_item(pathway, item.get("id", ""), prompt),
        "issue_for_discussion": _issue_phrase(topic, alignment, pathway),
        "gap": item.get("gap"),
    }


def _step_items(comparison: Dict[str, Any], step_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Flatten (pathway_id, item) pairs for one SNC2 step across all shared pathways."""
    out: List[Tuple[str, Dict[str, Any]]] = []
    for step in comparison.get("steps") or []:
        if step.get("id") != step_id:
            continue
        for path in step.get("pathways") or []:
            pid = path.get("id")
            for item in path.get("items") or []:
                out.append((pid, item))
    return out


def _pathway_items(comparison: Dict[str, Any], pathway_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Flatten (step_id, item) pairs for one pathway across all steps."""
    out: List[Tuple[str, Dict[str, Any]]] = []
    for step in comparison.get("steps") or []:
        for path in step.get("pathways") or []:
            if path.get("id") != pathway_id:
                continue
            for item in path.get("items") or []:
                out.append((step.get("id"), item))
    return out


# ---------- section builders ----------

def _extract_goals(prep: Dict[str, Any]) -> List[str]:
    """Pull the human-readable goals out of the mediation prep_data blob.

    `child_goals` in Mongo is a dict of the shape:
        {"selected_goals": [...], "consistency_text": "...", "feel_text": "...",
         "strength_text": "...", "priority_order": [...]}
    We want the actual free-text + selected chips as short strings.
    """
    cg = prep.get("child_goals") or {}
    if isinstance(cg, list):  # legacy shape
        return [str(x).strip() for x in cg if str(x).strip()]
    if not isinstance(cg, dict):
        return []
    out: List[str] = []
    for chip in (cg.get("selected_goals") or []):
        s = str(chip).strip()
        if s:
            out.append(s)
    for text_key in ("consistency_text", "feel_text", "strength_text"):
        s = str(cg.get(text_key) or "").strip()
        if s:
            out.append(s)
    for chip in (cg.get("priority_order") or []):
        s = str(chip).strip()
        if s and s not in out:
            out.append(s)
    return out


def _extract_priority(prep: Dict[str, Any]) -> str:
    """Human-readable summary of the mediation priority ranking."""
    prio = prep.get("priority") or {}
    if not isinstance(prio, dict):
        return str(prio or "").strip()
    # Preferred shape — an explicit summary.
    summary = str(prio.get("summary") or "").strip()
    if summary:
        return summary
    # Fall back to the ranked `items` list if that's all we have.
    items = prio.get("items") or []
    if isinstance(items, list) and items:
        labels = [str(it.get("topic") or it.get("label") or "").strip() for it in items[:5] if isinstance(it, dict)]
        labels = [x for x in labels if x]
        if labels:
            return "; ".join(labels)
    return ""


def _section_shared_priorities(
    prep_a: Dict[str, Any], prep_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Both parents' child-centered goals + top priority."""
    rows: List[Dict[str, Any]] = []

    goals_a = _extract_goals(prep_a)
    goals_b = _extract_goals(prep_b)
    if goals_a or goals_b:
        overlap = _text_overlap(goals_a, goals_b)
        rows.append({
            "topic": "Child-centered goals",
            "parent_a": {"summary": " • ".join(goals_a) or "No response"},
            "parent_b": {"summary": " • ".join(goals_b) or "No response"},
            "alignment": "aligned" if overlap else ("one_only" if bool(goals_a) ^ bool(goals_b) else "divergent"),
            "alignment_label": "Aligned" if overlap else ("One parent responded" if bool(goals_a) ^ bool(goals_b) else "Different focus"),
            "childs_need": "A clear, child-focused north star both parents can work from",
            "issue_for_discussion": (
                "The parents named overlapping child-centered goals; anchor future "
                "plans to those shared aims." if overlap
                else "The parents named different child-centered goals. A short "
                "facilitated conversation can help identify the shared aim underneath."
            ),
        })

    prio_a = _extract_priority(prep_a)
    prio_b = _extract_priority(prep_b)
    if prio_a or prio_b:
        rows.append({
            "topic": "Top priority for mediation",
            "parent_a": {"summary": prio_a or "No response"},
            "parent_b": {"summary": prio_b or "No response"},
            "alignment": "both_responded" if (prio_a and prio_b) else "one_only",
            "alignment_label": "Both responded" if (prio_a and prio_b) else "One parent responded",
            "childs_need": "Focused agenda for the next mediation session",
            "issue_for_discussion": (
                "Both parents named a top priority. Compare the two to build a "
                "combined agenda." if (prio_a and prio_b)
                else "Only one parent has named a top priority. A professional may "
                "wish to elicit the other parent's before the next session."
            ),
        })

    return _wrap_section(
        title="Shared child-centered priorities",
        description=(
            "The child-focused goals and priorities each parent named. "
            "Overlap is treated as an anchor for future discussion; "
            "differences are noted without attributing correctness."
        ),
        rows=rows,
    )


def _text_overlap(a: List[str], b: List[str]) -> bool:
    """Rough token overlap between two short-goal lists — Jaccard >= 0.2."""
    if not a or not b:
        return False
    ta = {w.lower() for goal in a for w in goal.split() if len(w) > 3}
    tb = {w.lower() for goal in b for w in goal.split() if len(w) > 3}
    if not ta or not tb:
        return False
    return (len(ta & tb) / max(1, len(ta | tb))) >= 0.2


def _section_pathway(
    comparison: Dict[str, Any], pathway_id: str, label: str, description: str,
) -> Dict[str, Any]:
    """Build a pathway-specific section (medical / educational / psychological)."""
    if pathway_id not in (comparison.get("shared_pathways") or []):
        return _wrap_section(
            title=label,
            description=description,
            rows=[],
            empty_reason=(
                f"Neither parent selected the {label.lower()} pathway in the "
                "Special Needs Co-Parenting assessment, so no comparison items "
                "are available in this section."
            ),
        )
    pairs = _pathway_items(comparison, pathway_id)
    # Priority items: Step 1 concern + urgency, Step 3 recommendation understanding,
    # Step 5 coordination, Step 6 agreement, Step 8 next steps.
    priority_ids = {
        "concern", "urgency", "current_impact",
        "recs_understand", "recs_written",
        "routines_consistent", "follow_recs", "handoffs_reliable", "share_updates",
        "agree_areas", "disagree_areas",
        "top_priority", "professional_next",
    }
    rows: List[Dict[str, Any]] = []
    for step_id, item in pairs:
        if item.get("id") not in priority_ids:
            continue
        rows.append(_row_from_snc2_item(pathway_id, item))
    # Sort divergent items to the top so the professional sees them first.
    rows.sort(key=lambda r: {"divergent": 0, "close": 1, "one_only": 2,
                             "insufficient": 3, "both_responded": 4, "aligned": 5}.get(r["alignment"], 6))
    return _wrap_section(title=label, description=description, rows=rows[:12])


def _section_household_consistency(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Step 5 across all shared pathways — the coordination-between-homes lens."""
    pairs = _step_items(comparison, "step5")
    rows = [_row_from_snc2_item(pid, item) for pid, item in pairs]
    rows.sort(key=lambda r: {"divergent": 0, "close": 1, "one_only": 2,
                             "insufficient": 3, "both_responded": 4, "aligned": 5}.get(r["alignment"], 6))
    return _wrap_section(
        title="Consistency between households",
        description=(
            "How each parent perceives coordination between homes — routines, "
            "follow-through, updates, handoffs, and supplies."
        ),
        rows=rows[:10],
    )


def _section_communication(
    comparison: Dict[str, Any],
    dim_a: Optional[Dict[str, Any]], dim_b: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Step 4 items (each parent's understanding) + Dimension Companion tiers."""
    rows: List[Dict[str, Any]] = []
    for pid, item in _step_items(comparison, "step4"):
        rows.append(_row_from_snc2_item(pid, item))

    # Dimension Companion — communication + emotional regulation tiers.
    if dim_a or dim_b:
        rows.extend(_dimension_rows(dim_a, dim_b))
    rows.sort(key=lambda r: {"divergent": 0, "close": 1, "one_only": 2,
                             "insufficient": 3, "both_responded": 4, "aligned": 5}.get(r["alignment"], 6))
    return _wrap_section(
        title="Communication and decision-making concerns",
        description=(
            "Where each parent stands on communicating about the child's needs, "
            "including how well each feels the other understands them."
        ),
        rows=rows[:12],
    )


def _dimension_rows(
    dim_a: Optional[Dict[str, Any]], dim_b: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Rows for the Dimension Companion communication + emotional-reg tiers."""
    def _tier(d: Optional[Dict[str, Any]], key: str) -> Optional[str]:
        if not d:
            return None
        return (((d.get("scoring") or {}).get("dimensions") or {}).get(key) or {}).get("tier")

    out: List[Dict[str, Any]] = []
    for dim_key, label, need in [
        ("communication", "Communication tier",
         "Common language for talking about the child's needs"),
        ("emotional_regulation", "Emotional-regulation tier",
         "Ability to have a calm conversation about difficult topics"),
    ]:
        a_tier = _tier(dim_a, dim_key)
        b_tier = _tier(dim_b, dim_key)
        if not a_tier and not b_tier:
            continue
        aligned = (a_tier == b_tier and a_tier is not None)
        alignment = "aligned" if aligned else (
            "one_only" if bool(a_tier) ^ bool(b_tier) else "divergent"
        )
        out.append({
            "topic": label,
            "parent_a": {"summary": (a_tier or "No response").title()},
            "parent_b": {"summary": (b_tier or "No response").title()},
            "alignment": alignment,
            "alignment_label": ALIGNMENT_LABELS.get(alignment, alignment),
            "childs_need": need,
            "issue_for_discussion": (
                f"Both parents' {label.lower()} placed them on the same tier — "
                "conversations at this level can move forward without additional "
                "scaffolding." if aligned
                else f"The parents' {label.lower()} placed them on different "
                "tiers. A professional may wish to calibrate expectations before "
                "unstructured conversations."
            ),
        })
    return out


def _section_agreements_and_differences(comparison: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Top agreements and top divergences across the whole SNC2 comparison."""
    agree_rows: List[Dict[str, Any]] = []
    diff_rows: List[Dict[str, Any]] = []
    for step in comparison.get("steps") or []:
        for path in step.get("pathways") or []:
            pid = path.get("id")
            for item in path.get("items") or []:
                alignment = item.get("alignment")
                if alignment == "aligned" or alignment == "both_responded":
                    agree_rows.append(_row_from_snc2_item(pid, item))
                elif alignment == "divergent":
                    diff_rows.append(_row_from_snc2_item(pid, item))

    # Rank agreements by "strong shared confidence" — likert 4-5 with tight gap.
    def _agree_score(r: Dict[str, Any]) -> float:
        gap = r.get("gap")
        return -(gap if isinstance(gap, (int, float)) else 5.0)
    agree_rows.sort(key=_agree_score)
    diff_rows.sort(key=lambda r: -(r.get("gap") or 0))

    return (
        _wrap_section(
            title="Areas of parental agreement",
            description=(
                "Items where both parents' responses aligned. These are the "
                "anchors any joint plan can build from."
            ),
            rows=agree_rows[:8],
        ),
        _wrap_section(
            title="Areas where parental perceptions differ",
            description=(
                "Items with the largest gaps between the two parents' responses. "
                "A difference here is not a judgement of either parent — it is a "
                "signal that additional discussion may be useful."
            ),
            rows=diff_rows[:8],
        ),
    )


def _section_issues_for_professional_discussion(
    diff_section: Dict[str, Any], comm_section: Dict[str, Any],
    lens_finding3: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Top items likely to benefit from mediation / professional support."""
    rows: List[Dict[str, Any]] = []

    # Start with the largest divergences and communication concerns.
    seen: set = set()
    for src in (diff_section.get("rows") or [])[:5] + (comm_section.get("rows") or [])[:3]:
        key = (src.get("pathway"), src.get("topic"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "topic": src.get("topic"),
            "pathway": src.get("pathway"),
            "pathway_label": src.get("pathway_label"),
            "childs_need": src.get("childs_need"),
            "issue_for_discussion": src.get("issue_for_discussion"),
            "alignment": src.get("alignment"),
            "alignment_label": src.get("alignment_label"),
        })

    # Finding 3 (Parenting-Plan Implications) — the ONE finding safe to share.
    if lens_finding3:
        head = str(lens_finding3.get("headline") or "").strip()
        tier = lens_finding3.get("feasibility_tier") or {}
        if head:
            rows.append({
                "topic": "Recommended parenting-plan structure spectrum",
                "childs_need": "A parenting-plan structure appropriate for the family's current context",
                "issue_for_discussion": (
                    f"One parent's trauma-informed safety screen surfaced the "
                    f"following parenting-plan framing (Finding 3 only — the "
                    f"underlying findings are private to that parent): "
                    f"\"{head}\""
                    + (
                        f" The screen suggested tier: {tier.get('label')} "
                        f"(review point ~{tier.get('review_point_days')} days)."
                        if tier else ""
                    )
                ),
                "alignment": "insufficient",
                "alignment_label": "Individual screen output",
            })

    return _wrap_section(
        title="Issues that may benefit from mediation or professional discussion",
        description=(
            "The topics most likely to benefit from focused professional "
            "attention. Ordering reflects the size of the perception gap, "
            "not any judgement of parental fitness."
        ),
        rows=rows,
    )


# ---------- output wrapper ----------

def _wrap_section(
    *, title: str, description: str, rows: List[Dict[str, Any]],
    empty_reason: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "title": title,
        "description": description,
        "row_count": len(rows),
        "rows": rows,
    }
    if not rows:
        out["empty_reason"] = empty_reason or (
            "No data available for this section. Ensure both parents have "
            "completed the relevant assessments before regenerating."
        )
    return out


# ---------- public API ----------

def build_joint_report(
    *,
    parent_a_name: str,
    parent_b_name: str,
    share_id: str,
    comparison: Dict[str, Any],
    prep_a: Dict[str, Any],
    prep_b: Dict[str, Any],
    dim_a: Optional[Dict[str, Any]] = None,
    dim_b: Optional[Dict[str, Any]] = None,
    lens_finding3_a: Optional[Dict[str, Any]] = None,
    lens_finding3_b: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the neutral joint report.

    `lens_finding3_a` / `lens_finding3_b` — Finding 3 ONLY of each parent's
    Trauma-Informed Safety and Functioning Lens. The caller is responsible
    for redacting Findings 1 & 2 before passing them in. Passing None
    means the parent did not complete the safety screen.
    """
    shared_pri = _section_shared_priorities(prep_a, prep_b)
    medical = _section_pathway(
        comparison, "medical", "Child's identified medical needs",
        "Medical concerns, recommendations, and coordination the parents identified.",
    )
    educational = _section_pathway(
        comparison, "educational", "Educational, IEP, and 504 needs",
        "Learning supports, evaluations, and school-communication needs both parents named.",
    )
    psychological = _section_pathway(
        comparison, "psychological", "Psychological and emotional needs",
        "Therapy, behavioural regulation, and mental-health coordination the parents identified.",
    )
    household = _section_household_consistency(comparison)
    communication = _section_communication(comparison, dim_a, dim_b)
    agreements, differences = _section_agreements_and_differences(comparison)

    # Combine the two parents' Finding 3 statements (each parent's screen
    # is individual — this section carries whichever findings exist).
    combined_f3: Optional[Dict[str, Any]] = None
    for f3 in (lens_finding3_a, lens_finding3_b):
        if f3 and not combined_f3:
            combined_f3 = f3
            break

    issues = _section_issues_for_professional_discussion(
        differences, communication, combined_f3,
    )

    return {
        "report_type": "joint_professional_summary",
        "report_title": "Joint Co-Parenting Summary for Professional Review",
        "share_id": share_id,
        "parent_a_name": parent_a_name,
        "parent_b_name": parent_b_name,
        "disclaimer": DISCLAIMER,
        "neutral_language_note": NEUTRAL_LANGUAGE_NOTE,
        "not_a_custody_evaluation": True,
        "safety_privacy_note": (
            "Only Finding 3 (Parenting-Plan Implications) of the Trauma-"
            "Informed Safety and Functioning Lens is included in this "
            "report. Findings 1 (Family-Violence Pattern) and 2 (Trauma "
            "Impact) remain private to the parent who completed the "
            "screen and are not shown to the co-parent."
        ),
        "shared_pathways": comparison.get("shared_pathways") or [],
        "sections": {
            "shared_priorities": shared_pri,
            "medical": medical,
            "educational": educational,
            "psychological": psychological,
            "household_consistency": household,
            "communication_concerns": communication,
            "areas_of_agreement": agreements,
            "areas_where_perceptions_differ": differences,
            "issues_for_professional_discussion": issues,
        },
        "summary_counts": {
            "shared_priorities": shared_pri["row_count"],
            "medical": medical["row_count"],
            "educational": educational["row_count"],
            "psychological": psychological["row_count"],
            "household_consistency": household["row_count"],
            "communication_concerns": communication["row_count"],
            "areas_of_agreement": agreements["row_count"],
            "areas_where_perceptions_differ": differences["row_count"],
            "issues_for_professional_discussion": issues["row_count"],
        },
    }
