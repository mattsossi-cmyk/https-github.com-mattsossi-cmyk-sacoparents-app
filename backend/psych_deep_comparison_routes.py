"""Psychological/Behavioural Deep Dive co-parent comparison API. Mounted at
/api/psych-deep/compare. Shares its state machine with the Educational and
Medical pathways via `deep_dive_compare_router_factory`.
"""
from __future__ import annotations

from deep_dive_compare_router_factory import make_deep_dive_compare_router
from psych_deep_comparison import build_comparison
from edu_deep_comparison_pdf import build_comparison_pdf


router = make_deep_dive_compare_router(
    prefix="/psych-deep/compare",
    tag="psych-deep-compare",
    shares_collection="psych_deep_shares",
    assessments_collection="psych_deep_assessments",
    share_id_prefix="psych_deep_share_",
    product_label="Checkin - Psychological Needs",
    pdf_filename_stem="Checkin_Psychological_Needs_Report",
    build_comparison=build_comparison,
    build_comparison_pdf=build_comparison_pdf,
    pdf_header_subtitle="Checkin - Psychological Needs Report",
    pdf_product_title="Checkin - Psychological Needs Report",
    frontend_hub_path="/special-needs-v2/psychological-deep-dive/compare",
)
