"""Medical / Prescription Deep Dive co-parent comparison API. Mounted at
/api/med-deep/compare. Shares its state machine with the Educational and
Psychological pathways via `deep_dive_compare_router_factory`.
"""
from __future__ import annotations

from deep_dive_compare_router_factory import make_deep_dive_compare_router
from med_deep_comparison import build_comparison
from edu_deep_comparison_pdf import build_comparison_pdf


router = make_deep_dive_compare_router(
    prefix="/med-deep/compare",
    tag="med-deep-compare",
    shares_collection="med_deep_shares",
    assessments_collection="med_deep_assessments",
    share_id_prefix="med_deep_share_",
    product_label="Medical Deep Dive",
    pdf_filename_stem="MedDeep_Comparison",
    build_comparison=build_comparison,
    build_comparison_pdf=build_comparison_pdf,
    pdf_header_subtitle="Medical Deep Dive Co-Parent Comparison",
    pdf_product_title="Medical · Prescription Deep Dive Comparison",
    frontend_hub_path="/special-needs-v2/medical-deep-dive/compare",
)
