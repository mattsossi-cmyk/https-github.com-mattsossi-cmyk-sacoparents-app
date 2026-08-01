"""Medical / Prescription Deep Dive — thin wrapper around the shared
deep-dive comparison core."""
from __future__ import annotations

from typing import Any, Dict

from med_deep_questions import DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION
from deep_dive_comparison_core import (
    ALIGNMENT_LABELS as _CORE_ALIGNMENT_LABELS,
    build_comparison_from_spec,
)


ALIGNMENT_LABELS = _CORE_ALIGNMENT_LABELS


def build_comparison(*, parent_a_name: str, parent_b_name: str,
                     a_answers: Dict[str, Any], b_answers: Dict[str, Any]) -> Dict[str, Any]:
    return build_comparison_from_spec(
        sections_spec=DEEP_DIVE_SECTIONS,
        assessment_version=DEEP_DIVE_VERSION,
        product_name="Medical · Prescription & Medication Coordination Deep Dive",
        parent_a_name=parent_a_name,
        parent_b_name=parent_b_name,
        a_answers=a_answers,
        b_answers=b_answers,
    )
