"""Educational Deep Dive co-parent comparison API.

Mounted at /api/edu-deep/compare. See `deep_dive_compare_router_factory.py`
for the shared state machine used by all three deep-dive pathways.
"""
from __future__ import annotations

from deep_dive_compare_router_factory import make_deep_dive_compare_router
from edu_deep_comparison import build_comparison
from edu_deep_comparison_pdf import build_comparison_pdf


router = make_deep_dive_compare_router(
    prefix="/edu-deep/compare",
    tag="edu-deep-compare",
    shares_collection="edu_deep_shares",
    assessments_collection="edu_deep_assessments",
    share_id_prefix="edu_deep_share_",
    product_label="Educational Assessment",
    pdf_filename_stem="Educational_Assessment_Alignment_Report",
    build_comparison=build_comparison,
    build_comparison_pdf=build_comparison_pdf,
    pdf_header_subtitle="Educational Assessment Alignment Report",
    pdf_product_title="Educational Assessment Alignment Report",
)
