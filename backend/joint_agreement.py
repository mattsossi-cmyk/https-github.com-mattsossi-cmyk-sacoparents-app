"""Joint Co-Parenting Agreement Draft — deterministic merger.

Given both parents' latest individual Co-Parenting Agreement drafts (as
stored in the `agreements` Mongo collection), produce a neutral,
side-by-side JOINT draft with three explicit buckets per section:

    Both proposed         — clauses that appear in BOTH parents' drafts
    (Parent A) only       — clauses only in caller's draft
    (Parent B) only       — clauses only in the co-parent's draft

The output is intentionally deterministic (no LLM) so tests can lock the
merge behaviour, and so parents get consistent output every time. It is
a *draft for discussion*, never a final agreement — the disclaimer says
so on every surface.

Design commitments (locked in tests):
  * Never labels either draft as "correct" or "better".
  * Never uses possession/custody/access-schedule language — the source
    drafts already avoid it, and we surface exactly what the parents
    wrote.
  * Both parents' actual wording appears verbatim on both sides of the
    side-by-side; the merger only classifies each clause into a bucket.

Public API:
  * `build_joint_agreement(...)` — pure function.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Disclaimer & neutral-language framing — surfaced in the payload + PDF.
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "This Joint Co-Parenting Agreement Draft is a DRAFT FOR DISCUSSION "
    "compiled from both parents' individual agreement drafts. It is not a "
    "signed agreement, a court order, a legal document, or a custody "
    "recommendation. Both parents remain responsible for reviewing each "
    "clause with their own professionals before adopting anything. The "
    "purpose of this document is to make it easy to see where the parents "
    "already converge, and where a mediator or attorney could help bridge "
    "the remaining gaps. Use of SA CoParents does not by itself create an "
    "attorney-client, therapist-patient, mediator-client, or other "
    "privileged relationship."
)

NEUTRAL_LANGUAGE_NOTE = (
    "The merger below never labels either parent's draft as correct or "
    "better. Where both parents proposed the same clause we say so; where "
    "only one parent proposed it, we surface the clause verbatim under "
    "that parent's column so the other parent can respond in their own "
    "words."
)

# Similarity threshold above which two strings are treated as the "same"
# clause. Kept generous — parents rarely phrase things identically, but
# we do not want to over-merge either.
_SIMILARITY_MATCH = 0.60


# ---------------------------------------------------------------------------
# Text normalisation + similarity helpers.
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace — for matching."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[\.,;:!\?\"'\-()\[\]]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _similar(a: str, b: str) -> float:
    na, nb = _normalise(a), _normalise(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _clause_text(item: Any) -> str:
    """Extract a single clause string from either a bare string, a
    {area, agreement} dict, or a {area, statement} dict."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("agreement", "statement", "clause", "text", "topic", "value"):
            v = item.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _clause_area(item: Any) -> str:
    if isinstance(item, dict):
        a = item.get("area") or item.get("category")
        if isinstance(a, str) and a.strip():
            return a.strip()
    return ""


# ---------------------------------------------------------------------------
# Bucket builder — the heart of the merger.
# ---------------------------------------------------------------------------

def _merge_lists(
    list_a: List[Any], list_b: List[Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (both, a_only, b_only) buckets from two clause lists.

    Both entries carry `{area, parent_a_text, parent_b_text}` so the UI
    can show them in a two-column strip. Solo entries carry
    `{area, text}` — the other parent's column is intentionally empty
    on the frontend/PDF.
    """
    matched_b: set = set()
    both: List[Dict[str, Any]] = []
    a_only: List[Dict[str, Any]] = []

    for a_item in list_a or []:
        a_text = _clause_text(a_item)
        if not a_text:
            continue
        best_j = -1
        best_score = 0.0
        for j, b_item in enumerate(list_b or []):
            if j in matched_b:
                continue
            b_text = _clause_text(b_item)
            score = _similar(a_text, b_text)
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= _SIMILARITY_MATCH:
            matched_b.add(best_j)
            b_item = list_b[best_j]
            both.append({
                "area": _clause_area(a_item) or _clause_area(b_item) or "",
                "parent_a_text": a_text,
                "parent_b_text": _clause_text(b_item),
                "similarity": round(best_score, 2),
            })
        else:
            a_only.append({
                "area": _clause_area(a_item),
                "text": a_text,
            })

    b_only: List[Dict[str, Any]] = []
    for j, b_item in enumerate(list_b or []):
        if j in matched_b:
            continue
        b_text = _clause_text(b_item)
        if not b_text:
            continue
        b_only.append({
            "area": _clause_area(b_item),
            "text": b_text,
        })

    return both, a_only, b_only


def _merge_section(
    a: Dict[str, Any], b: Dict[str, Any], key: str, title: str, description: str,
) -> Dict[str, Any]:
    """Merge one field-name across both agreements into a section block."""
    both, a_only, b_only = _merge_lists(a.get(key) or [], b.get(key) or [])
    return {
        "key": key,
        "title": title,
        "description": description,
        "both_proposed": both,
        "parent_a_only": a_only,
        "parent_b_only": b_only,
        "counts": {
            "both_proposed": len(both),
            "parent_a_only": len(a_only),
            "parent_b_only": len(b_only),
        },
    }


# ---------------------------------------------------------------------------
# Overall convergence summary — a single "here's where you already agree"
# headline the frontend can lead with.
# ---------------------------------------------------------------------------

def _convergence_summary(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_both = sum(s["counts"]["both_proposed"] for s in sections)
    total_a = sum(s["counts"]["parent_a_only"] for s in sections)
    total_b = sum(s["counts"]["parent_b_only"] for s in sections)
    total = max(1, total_both + total_a + total_b)
    return {
        "total_clauses":      total_both + total_a + total_b,
        "both_proposed":      total_both,
        "parent_a_only":      total_a,
        "parent_b_only":      total_b,
        "converged_pct":      round(total_both / total * 100),
    }


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

# ---------- parent-friendly 5-bucket view ----------
# Mirrors the Joint Report's parent_view treatment but mapped to the
# agreement domain (proposed clauses instead of assessment perceptions).


_AGREEMENT_SECTION_LABELS = {
    "shared_goals":         "Child-centered goals",
    "communication":        "Communication",
    "child_needs":          "Child's needs",
    "household_rules":      "Household rhythms",
    "priority_items":       "Priority topics",
    "open_for_discussion":  "Still open for discussion",
}


def _clause_short_text(row: Dict[str, Any], side: str) -> str:
    """Pull the shortest useful text from a merged row (`both_proposed`
    rows have both parents' texts; single-side rows only have one).
    `side` in {'a', 'b', 'either'}."""
    if side == "a":
        return (row.get("parent_a_text") or row.get("text") or "").strip()
    if side == "b":
        return (row.get("parent_b_text") or row.get("text") or "").strip()
    return (
        row.get("parent_a_text")
        or row.get("parent_b_text")
        or row.get("text")
        or ""
    ).strip()


def _both_proposed_items(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sec in sections:
        for row in (sec.get("both_proposed") or []):
            text = _clause_short_text(row, "either")
            if not text:
                continue
            out.append({
                "text": text,
                "area": row.get("area") or "",
                "section": sec.get("key") or "",
                "section_title": sec.get("title") or "",
            })
    return out


def _different_ideas_items(
    sections: List[Dict[str, Any]],
    parent_a_name: str,
    parent_b_name: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sec in sections:
        for row in (sec.get("parent_a_only") or []):
            out.append({
                "topic": row.get("area") or sec.get("title") or "",
                "parent_a": _clause_short_text(row, "a"),
                "parent_b": "",
                "who": parent_a_name,
                "section": sec.get("key") or "",
                "section_title": sec.get("title") or "",
            })
        for row in (sec.get("parent_b_only") or []):
            out.append({
                "topic": row.get("area") or sec.get("title") or "",
                "parent_a": "",
                "parent_b": _clause_short_text(row, "b"),
                "who": parent_b_name,
                "section": sec.get("key") or "",
                "section_title": sec.get("title") or "",
            })
    return out


def _needs_refinement_items(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Items either parent explicitly flagged as still-open. These are
    the topics most likely to need a mediator's help — not because
    someone is wrong, but because both parents agree it's unresolved."""
    out: List[Dict[str, Any]] = []
    for sec in sections:
        if sec.get("key") != "open_for_discussion":
            continue
        for row in (sec.get("both_proposed") or []):
            text = _clause_short_text(row, "either")
            if text:
                out.append({
                    "topic": row.get("area") or "",
                    "detail": text,
                    "both_flagged": True,
                })
        for row in (sec.get("parent_a_only") or []) + (sec.get("parent_b_only") or []):
            text = _clause_short_text(row, "either")
            if text:
                out.append({
                    "topic": row.get("area") or "",
                    "detail": text,
                    "both_flagged": False,
                })
    return out


def _blending_options(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic "consider" options derived from the shape of the
    divergence — never prescriptive, always framed as parents' choice."""
    options: List[Dict[str, Any]] = []
    section_map = {s.get("key"): s for s in sections}

    if (section_map.get("communication") or {}).get("both_proposed"):
        options.append({
            "title": "Anchor to what you both already wrote",
            "detail": (
                "You both proposed the same communication clause. Adopt "
                "it verbatim in the joint draft and use that shared "
                "language as the reference point for anything else "
                "you're still working out."
            ),
        })

    single_side_total = sum(
        len((section_map.get(k, {}) or {}).get("parent_a_only") or []) +
        len((section_map.get(k, {}) or {}).get("parent_b_only") or [])
        for k in ("communication", "child_needs", "household_rules")
    )
    if single_side_total >= 2:
        options.append({
            "title": "Blend rather than pick",
            "detail": (
                "Where each of you proposed something different, try "
                "writing one merged clause that keeps the best of both. "
                "Neither parent has to \"lose\" a clause — most can be "
                "rephrased to hold both intents."
            ),
        })

    if (section_map.get("open_for_discussion") or {}).get("row_count", 0) > 0:
        options.append({
            "title": "Bring the open items to a mediator",
            "detail": (
                "The clauses in \"May Need Refinement\" are explicitly "
                "flagged as unresolved. A short mediated conversation "
                "focused on those two or three items is usually more "
                "productive than trying to resolve them directly."
            ),
        })

    if (section_map.get("priority_items") or {}).get("both_proposed"):
        options.append({
            "title": "Use your shared priorities as tiebreakers",
            "detail": (
                "When you disagree on a specific clause, check whether "
                "one option aligns better with the priority topics you "
                "both ranked as most important. Shared priorities are "
                "the best tiebreakers you have."
            ),
        })

    # Always-safe closer.
    options.append({
        "title": "Bring this joint draft to your professional",
        "detail": (
            "The Detailed Comparison below is written for attorneys, "
            "mediators, and therapists. Share this draft with whoever "
            "is helping you so they can start with the full picture."
        ),
    })
    return options


def _next_conversation_questions(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Turn divergent clauses into child-focused questions the parents
    can carry into a conversation or mediation session."""
    questions: List[Dict[str, Any]] = []
    seen_topics: set = set()
    for sec in sections:
        for bucket_key in ("parent_a_only", "parent_b_only"):
            for row in (sec.get(bucket_key) or [])[:2]:
                topic = (row.get("area") or sec.get("title") or "").strip()
                if not topic or topic.lower() in seen_topics:
                    continue
                seen_topics.add(topic.lower())
                questions.append({
                    "topic": topic,
                    "question": (
                        f"On {topic.lower()}, what does our child seem "
                        "to need most right now — and what would make "
                        "it easier for both of us to give them that?"
                    ),
                })
                if len(questions) >= 6:
                    break
            if len(questions) >= 6:
                break
        if len(questions) >= 6:
            break

    # Always include a shared-ground closer + a mediator closer so this
    # bucket never leaves parents empty-handed.
    questions.append({
        "topic": "Shared ground",
        "question": (
            "What is one clause from the 'What You've Both Proposed' "
            "list that we could adopt as-is this week to start "
            "building momentum?"
        ),
    })
    questions.append({
        "topic": "Next step",
        "question": (
            "What is one question we could ask a mediator that would "
            "help us both make better decisions for our child?"
        ),
    })
    return questions


def _build_agreement_parent_view(
    sections: List[Dict[str, Any]],
    parent_a_name: str,
    parent_b_name: str,
) -> Dict[str, Any]:
    """5-bucket parent-friendly view over the merged agreement sections."""
    both = _both_proposed_items(sections)
    diffs = _different_ideas_items(sections, parent_a_name, parent_b_name)
    refine = _needs_refinement_items(sections)
    return {
        "what_you_both_proposed": {
            "title": "What You've Both Proposed",
            "description": (
                "Clauses that appear in both parents' drafts. Adopt "
                "these first — they're already agreed in principle."
            ),
            "items": both,
            "count": len(both),
        },
        "where_you_have_different_ideas": {
            "title": "Where Each of You Has Different Ideas",
            "description": (
                "Clauses only one of you proposed. This is where a "
                "conversation — with each other or with a mediator — "
                "will do the most good."
            ),
            "items": diffs,
            "count": len(diffs),
        },
        "may_need_refinement": {
            "title": "Clauses That May Need Refinement",
            "description": (
                "Items either of you explicitly flagged as still open. "
                "Not disagreements yet — just unresolved."
            ),
            "items": refine,
            "count": len(refine),
        },
        "options_to_consider": {
            "title": "Options for Blending Your Ideas",
            "description": (
                "Possible approaches to work through the differences. "
                "None are prescriptions — pick the ones that fit."
            ),
            "items": _blending_options(sections),
            "count": None,
        },
        "questions_for_next_conversation": {
            "title": "Questions for Your Next Conversation",
            "description": (
                "Child-focused questions the two of you can discuss "
                "yourselves or take to mediation."
            ),
            "items": _next_conversation_questions(sections),
            "count": None,
        },
    }


# ---------- assembly ----------

def build_joint_agreement(
    *,
    share_id: str,
    parent_a_name: str,
    parent_b_name: str,
    agreement_a: Dict[str, Any],
    agreement_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge two individual agreement drafts into a joint draft.

    Sections merged (matches the fields the mediation_routes agreement
    generator persists today):
      * shared_goals            — child-centered goals both parents named
      * communication           — communication clauses
      * child_needs             — child-needs clauses
      * household_rules         — household-rules clauses
      * priority_items          — ranked priority topics
      * open_for_discussion     — topics each parent explicitly flagged
                                  as still-open. Rendered as PROPOSED
                                  topics rather than agreed clauses.
    """
    sections: List[Dict[str, Any]] = [
        _merge_section(
            agreement_a, agreement_b, "shared_goals",
            "Shared child-centered goals",
            "Goals for the child that appear in both parents' drafts vs. "
            "one only.",
        ),
        _merge_section(
            agreement_a, agreement_b, "communication",
            "Communication",
            "Clauses about how the parents plan to communicate about the "
            "child.",
        ),
        _merge_section(
            agreement_a, agreement_b, "child_needs",
            "Child's needs",
            "Clauses about the child's day-to-day needs and coordination "
            "between homes.",
        ),
        _merge_section(
            agreement_a, agreement_b, "household_rules",
            "Household rhythms & rules",
            "Clauses about household routines the parents want to keep "
            "aligned.",
        ),
        _merge_section(
            agreement_a, agreement_b, "priority_items",
            "Priority topics",
            "Topics each parent ranked as most important for the next "
            "conversation.",
        ),
        _merge_section(
            agreement_a, agreement_b, "open_for_discussion",
            "Still open for discussion",
            "Items each parent explicitly flagged as unresolved. Kept "
            "here so nothing is quietly dropped from the joint draft.",
        ),
    ]

    return {
        "report_type":         "joint_coparenting_agreement_draft",
        "report_title":        "Joint Co-Parenting Agreement Draft",
        "share_id":            share_id,
        "parent_a_name":       parent_a_name,
        "parent_b_name":       parent_b_name,
        "disclaimer":          DISCLAIMER,
        "neutral_language_note": NEUTRAL_LANGUAGE_NOTE,
        "not_a_final_agreement": True,
        "source_agreements": {
            "parent_a_agreement_id": agreement_a.get("agreement_id"),
            "parent_a_generated_at": agreement_a.get("generated_at"),
            "parent_b_agreement_id": agreement_b.get("agreement_id"),
            "parent_b_generated_at": agreement_b.get("generated_at"),
        },
        "sections":            sections,
        "parent_view":         _build_agreement_parent_view(
            sections, parent_a_name, parent_b_name,
        ),
        "summary":             _convergence_summary(sections),
        "closing_notes": {
            "parent_a": str(agreement_a.get("closing_note") or "").strip(),
            "parent_b": str(agreement_b.get("closing_note") or "").strip(),
        },
        "next_step": (
            "Bring this joint draft to your next mediation session. The "
            "'both proposed' clauses can be adopted quickly; the 'only "
            "one parent proposed' clauses are where the mediator's time "
            "will pay off most."
        ),
    }



# ---------------------------------------------------------------------------
# Regenerator — refresh the caller's individual agreement draft using the
# joint's `both_proposed` clauses as anchors.
#
# Pure function. Given the caller's own agreement + the caller's own view
# of the joint (the caller is always Parent A in the joint payload — we
# guarantee this by generating the joint from their perspective), we
# produce a NEW individual agreement doc where each section's clauses
# are re-ordered so the ones both parents already proposed appear first
# and carry an `anchored=True` flag.
#
# Deliberately deterministic (no LLM) — the parent's voice is preserved
# verbatim; we do not rewrite their clauses. The regenerator's job is
# to _highlight_ shared ground inside their own draft.
# ---------------------------------------------------------------------------

# Fields we regenerate — same list the merger uses. Every section that
# carries dict-shaped clauses gets the anchor promotion + `anchored`
# flag. `shared_goals` / `open_for_discussion` are bare-string lists so
# they get the same promotion but no flag mutation.
_REGEN_SECTIONS = (
    "shared_goals",
    "communication",
    "child_needs",
    "household_rules",
    "priority_items",
    "open_for_discussion",
)


def _clause_matches_joint_both(
    caller_text: str, joint_both_rows: List[Dict[str, Any]],
) -> bool:
    """True when the caller's own clause matched into the joint's
    `both_proposed` bucket (i.e., the co-parent proposed a similar
    clause). We compare against `parent_a_text` because the joint is
    generated from the caller's perspective (they are Parent A)."""
    if not caller_text:
        return False
    for row in joint_both_rows or []:
        if _similar(caller_text, row.get("parent_a_text") or "") >= _SIMILARITY_MATCH:
            return True
    return False


def _promote_and_flag(
    original_items: List[Any], joint_both_rows: List[Dict[str, Any]],
) -> Tuple[List[Any], int]:
    """Sort the caller's clauses so anchors come first, and add an
    `anchored` boolean to dict-shaped clauses (bare strings stay strings).

    Returns (new_list, anchor_count).
    """
    anchors: List[Any] = []
    rest: List[Any] = []
    for item in original_items or []:
        text = _clause_text(item)
        matched = _clause_matches_joint_both(text, joint_both_rows)
        if isinstance(item, dict):
            new_item = dict(item)
            new_item["anchored"] = bool(matched)
            (anchors if matched else rest).append(new_item)
        elif isinstance(item, str):
            (anchors if matched else rest).append(item)
        else:
            rest.append(item)
    return (anchors + rest), len(anchors)


def regenerate_individual_from_joint(
    *,
    caller_agreement: Dict[str, Any],
    joint_payload: Dict[str, Any],
    now_iso: str,
    co_parent_name: str,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Return (new_agreement_doc, anchor_counts_per_section).

    The new doc is a shallow copy of `caller_agreement` with:
      * each `_REGEN_SECTIONS` list re-ordered + flagged.
      * fresh `agreement_id` and `generated_at`.
      * a `regenerated_from_joint` audit stanza pointing to the joint
        share + prior agreement id.
      * a refreshed `overview` line that names the co-parent.

    `overview`, `closing_note`, and any other fields not in
    `_REGEN_SECTIONS` are preserved as-is.
    """
    # Build a joint-section lookup keyed by section name.
    joint_by_key: Dict[str, List[Dict[str, Any]]] = {}
    for section in joint_payload.get("sections") or []:
        joint_by_key[section.get("key")] = section.get("both_proposed") or []

    new_doc = dict(caller_agreement)
    anchor_counts: Dict[str, int] = {}
    for key in _REGEN_SECTIONS:
        both = joint_by_key.get(key) or []
        promoted, count = _promote_and_flag(new_doc.get(key) or [], both)
        new_doc[key] = promoted
        anchor_counts[key] = count

    prior_agreement_id = caller_agreement.get("agreement_id")
    new_doc["agreement_id"]           = f"agr_regen_{now_iso.replace(':', '').replace('-', '').replace('.', '')[:20]}"
    new_doc["generated_at"]           = now_iso
    new_doc["regenerated_from_joint"] = {
        "share_id":              joint_payload.get("share_id"),
        "co_parent_name":        co_parent_name,
        "prior_agreement_id":    prior_agreement_id,
        "regenerated_at":        now_iso,
        "anchor_counts":         anchor_counts,
        "total_anchors":         sum(anchor_counts.values()),
    }

    total_anchors = sum(anchor_counts.values())
    if total_anchors:
        first = co_parent_name.split(" ")[0] if co_parent_name else "your co-parent"
        new_doc["overview"] = (
            f"Refreshed draft — anchored around the {total_anchors} clause"
            f"{'s' if total_anchors != 1 else ''} that {first} and I have "
            f"both proposed. Those clauses appear at the top of each "
            f"section and are marked as anchored."
        )
    return new_doc, anchor_counts
