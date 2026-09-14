"""Alignment reflection analysis — Iter191.

Given two parents' free-text reflection answers (see
`alignment_reflection_questions.py`), produce the sacoparentsalign
Section 2 / Section 3 / Section 4 material:

  * `both_parents_mentioned` — one bullet per prompt where the two
    answers share meaningful keywords. Example: "Both parents
    mentioned 'consistent' when describing desired improvements."
  * `perspectives_differ` — per prompt, the parent A / parent B
    quotes surfaced verbatim under each parent's name so the reader
    can compare tone.
  * `child_identified_needs` — a deduped keyword extraction from the
    "primary need" and "desired improvements" prompts, in the child's
    voice ("Predictable structure", "Consistent expectations").

Design commitments:
  * Deterministic (no LLM). The overlap set is derived from a
    conservative stopword filter + case-insensitive token comparison
    so tests can lock the exact bullets.
  * Never labels either parent as "correct" or "better".
  * Ignores stopwords, punctuation, and the child's own name if
    passed in — prevents "Both parents mentioned 'maya'" filler.
  * Answers <= 3 words are surfaced VERBATIM (no keyword extraction)
    because short answers ARE the keyword.

Public API:
  * `analyse_reflections(a_answers, b_answers, subject, child_name=...)`
    → returns the three-block dict above.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from alignment_reflection_questions import (
    SUBJECT_CO_PARENTING,
    prompts_for,
    find_prompt,
)


# Stopwords — small, hand-picked list. Kept small on purpose: a
# sprawling stopword list starts scrubbing meaningful words like
# "safe" and "clear". This list catches only the truly generic ones.
_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "in",
    "on", "at", "to", "for", "with", "from", "by", "as", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "not", "no", "our", "we", "us", "you", "your",
    "yours", "i", "me", "my", "mine", "he", "she", "it", "they",
    "them", "their", "this", "that", "these", "those", "here", "there",
    "so", "very", "really", "just", "also", "more", "most", "much",
    "some", "any", "all", "each", "every", "one", "two", "both",
    "either", "neither", "between", "when", "where", "how", "what",
    "why", "which", "who", "whom", "would", "could", "should", "may",
    "might", "will", "shall", "can", "cannot", "cant", "don", "dont",
    "isnt", "arent", "wasnt", "werent", "havent", "hasnt", "hadnt",
    "about", "up", "out", "over", "under", "again", "further", "same",
    "than", "too", "own", "into",
    # Domain fillers common in reflections that add no signal.
    "child", "children", "kid", "kids", "parent", "parents", "coparent",
    "coparents", "coparenting", "other", "home", "homes", "house",
    "way", "ways", "thing", "things", "time", "times", "think",
    "feel", "feels", "felt", "want", "wants", "need", "needs",
    "like", "likes", "make", "makes", "made", "get", "gets", "got",
    "know", "knows", "knew", "see", "sees", "saw", "come", "comes",
    "came", "go", "goes", "went", "gone", "going",
}


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']{1,}")


def _tokenise(text: str) -> List[str]:
    """Lowercase word tokens, alphabetic only, len >= 2."""
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _meaningful_tokens(text: str, child_name: Optional[str] = None) -> Set[str]:
    """Return the deduped meaningful token set for a piece of text.
    Strips stopwords + the child's own name to prevent "Both parents
    mentioned 'maya'" filler bullets."""
    child_lower = (child_name or "").strip().lower()
    return {
        tok
        for tok in _tokenise(text)
        if tok not in _STOPWORDS and tok != child_lower and len(tok) >= 3
    }


def _short_answer_verbatim(text: str) -> Optional[str]:
    """Answers of 3 or fewer words ARE the keyword — return them
    verbatim (lowercased) so the "Both parents mentioned..." bullet
    reads naturally. Longer answers go through keyword extraction."""
    if not text or not text.strip():
        return None
    tokens = _tokenise(text)
    if 1 <= len(tokens) <= 3:
        return " ".join(tokens)
    return None


def _shared_phrase_for_prompt(
    a_text: str, b_text: str, child_name: Optional[str] = None,
) -> Optional[str]:
    """Return the strongest shared phrase between two answers to the
    same prompt, or `None` when there is no overlap.

    Rules:
      1. If either answer is empty → no shared phrase.
      2. If BOTH answers are <=3 words and identical (case-insensitive)
         → return the verbatim short answer.
      3. Otherwise → intersect meaningful token sets. Return up to 3
         shared tokens joined by ", ".
    """
    a_short = _short_answer_verbatim(a_text)
    b_short = _short_answer_verbatim(b_text)
    if a_short and b_short and a_short == b_short:
        return a_short

    a_tokens = _meaningful_tokens(a_text, child_name)
    b_tokens = _meaningful_tokens(b_text, child_name)
    shared = sorted(a_tokens & b_tokens)
    if not shared:
        return None
    return ", ".join(shared[:3])


def _clean_quote(text: str) -> str:
    """Trim + collapse whitespace so short and long answers render
    cleanly in the two-column strip. Never modifies casing or
    punctuation — the parent's voice is preserved verbatim."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def analyse_reflections(
    a_answers: Dict[str, str],
    b_answers: Dict[str, str],
    subject: str = SUBJECT_CO_PARENTING,
    *,
    parent_a_name: str = "Parent A",
    parent_b_name: str = "Parent B",
    child_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Produce the sacoparentsalign SS2 / SS3 / SS4 blocks from two
    parents' free-text reflection answers.

    `a_answers` and `b_answers` are `{prompt_id: str}` dicts. Missing
    or empty answers are handled — the analysis skips them rather
    than emitting empty bullets. Both dicts may be sparse.

    Return shape (matches `alignment_report` extension keys):
      {
        "both_parents_mentioned": [
          {"prompt_id", "prompt_label", "shared_phrase"}, ...
        ],
        "perspectives_differ": [
          {"prompt_id", "prompt_label", "parent_a_quote",
           "parent_b_quote"}, ...
        ],
        "reflection_child_needs": [ str, ... ]  # for SS4 backfill
      }
    """
    prompt_list = prompts_for(subject)
    both: List[Dict[str, str]] = []
    diffs: List[Dict[str, str]] = []

    for p in prompt_list:
        pid = p["id"]
        a_raw = (a_answers or {}).get(pid) or ""
        b_raw = (b_answers or {}).get(pid) or ""
        a_text = _clean_quote(a_raw)
        b_text = _clean_quote(b_raw)

        shared = _shared_phrase_for_prompt(a_text, b_text, child_name)
        if shared:
            both.append({
                "prompt_id":     pid,
                "prompt_label":  p.get("label") or pid,
                "shared_phrase": shared,
            })

        # A difference row exists whenever at least ONE parent
        # answered — surfacing a single-side quote is still useful
        # for the mediator (it's exactly the "one parent flagged this,
        # the other did not" pattern).
        if a_text or b_text:
            diffs.append({
                "prompt_id":      pid,
                "prompt_label":   p.get("label") or pid,
                "parent_a_quote": a_text,
                "parent_b_quote": b_text,
                "parent_a_name":  parent_a_name,
                "parent_b_name":  parent_b_name,
            })

    # SS4 Child's Identified Needs — pull keywords from primary_need
    # + desired_improvements from either parent. Deduped, capped at 8.
    seen: Set[str] = set()
    needs: List[str] = []
    for prompt_id in ("primary_need", "desired_improvements"):
        for src in (a_answers, b_answers):
            text = _clean_quote((src or {}).get(prompt_id) or "")
            if not text:
                continue
            # Short answer? Take verbatim as a bullet.
            short = _short_answer_verbatim(text)
            if short:
                key = short.lower()
                if key not in seen:
                    seen.add(key)
                    # Preserve original casing where possible.
                    needs.append(text)
                continue
            # Longer answer → surface the top meaningful tokens as bullets.
            for tok in sorted(_meaningful_tokens(text, child_name))[:3]:
                if tok not in seen:
                    seen.add(tok)
                    needs.append(tok.capitalize())
            if len(needs) >= 8:
                return {
                    "both_parents_mentioned": both,
                    "perspectives_differ":    diffs,
                    "reflection_child_needs": needs[:8],
                }

    return {
        "both_parents_mentioned": both,
        "perspectives_differ":    diffs,
        "reflection_child_needs": needs[:8],
    }
