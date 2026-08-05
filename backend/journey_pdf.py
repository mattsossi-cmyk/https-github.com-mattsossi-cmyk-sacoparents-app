"""Shared FPDF renderer for the SA CoParents journey format used by all
three deep-dive reports (Educational / Psychological / Medical).

The caller passes the report dict produced by the *_deep_journey builder plus
a `product_name` used in the header/footer.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from edu_deep_report import _PDF as _BasePDF, _safe, _section_break, LOGO_PATH  # noqa: F401
from deep_dive_narrative import render_parts_narrative
import os


_RATING_COLORS = {
    "Strong": (31, 92, 59),
    "Developing": (170, 116, 40),
    "Needs Attention": (176, 42, 42),
    "Not enough info": (110, 100, 130),
}


def _pdf_class(product_name: str, footer_name: str):
    """Build a header/footer-branded subclass for a product."""

    class _JourneyPDF(_BasePDF):
        def header(self):
            from pdf_watermark import stamp_watermark
            stamp_watermark(self)
            self.set_fill_color(245, 240, 232); self.rect(0, 0, self.w, 18, "F")
            if os.path.exists(LOGO_PATH):
                try: self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
                except Exception: pass
            self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
            self.cell(0, 4.4, _safe(f"SA CoParents  ·  {product_name}"), ln=1)
            self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
            self.cell(0, 3.6, _safe("Relational Mediation Prep"), ln=1)
            self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
            self.line(14, 19, self.w - 14, 19)
            self.set_y(22); self.set_text_color(30, 24, 54)

        def footer(self):
            from pdf_watermark import stamp_signature_line
            stamp_signature_line(self)
            self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
            self.cell(0, 4, _safe(f"{footer_name}  ·  Page {self.page_no()} of {{nb}}"), align="C")

    return _JourneyPDF


def build_journey_pdf(*, product_name: str, footer_name: str, headline: str,
                      report: Dict[str, Any],
                      signed_by: Optional[str] = None,
                      signed_at: Optional[str] = None,
                      signed_note: Optional[str] = None) -> bytes:
    pdf = _pdf_class(product_name, footer_name)()
    if signed_by and signed_at:
        pdf._signed_by = signed_by
        pdf._signed_at = signed_at
        if signed_note:
            pdf._signed_note = signed_note
    pdf.add_page()

    cover = report.get("cover") or {}
    overview = report.get("overview") or {}
    support = report.get("support_summary") or {}
    profile = report.get("child_profile") or {}
    involvement = report.get("school_involvement") or {}
    coparenting = report.get("co_parenting_assessment") or {}
    level = report.get("support_level") or {}

    pdf.h1(headline)
    bits = [f"Parent: {cover.get('parent_name') or '-'}",
            f"Child: {cover.get('child_name') or '-'}"]
    if cover.get("grade_level") and cover.get("grade_level") != "-":
        bits.append(f"Grade: {cover['grade_level']}")
    if cover.get("school_state") and cover.get("school_state") != "-":
        bits.append(f"State: {cover['school_state']}")
    if cover.get("assessment_date"):
        bits.append(f"Date: {cover['assessment_date']}")
    pdf.body(" · ".join(bits))

    _section_break(pdf)
    pdf.h2("1. Report overview")
    pdf.h3("Purpose")
    pdf.bullets(overview.get("purpose_bullets") or [])
    pdf.small(report.get("disclaimer") or "")

    _section_break(pdf)
    pdf.h2("2. Your support summary")
    for area in support.get("ratings") or []:
        pdf.set_font("Helvetica", "B", 9.7); pdf.set_text_color(30, 24, 54)
        pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 4.6, _safe(area.get("area") or ""))
        color = _RATING_COLORS.get(area.get("rating") or "", (61, 26, 120))
        pdf.pill(f"Rating: {area.get('rating') or '-'}", color=color)
        if area.get("narrative"): pdf.body(area["narrative"])
        pdf.ln(0.5)
    if support.get("overall_narrative"):
        pdf.h3("Overall"); pdf.body(support["overall_narrative"])

    # Rich per-part storytelling (opening, one card per part, closing).
    render_parts_narrative(pdf, report)

    if report.get("ai_summary"):
        _section_break(pdf)
        pdf.h2("Executive summary")
        pdf.small("AI-generated · neutral · non-diagnostic")
        pdf.body(report["ai_summary"])

    _section_break(pdf)
    pdf.h2("3. Your child's profile")
    pdf.h3("Strengths identified"); pdf.bullets(profile.get("strengths") or [])
    if profile.get("concerns"):
        pdf.h3("Concerns identified"); pdf.bullets(profile["concerns"])
    if profile.get("primary_concern") or profile.get("benefit_from"):
        pdf.h3("Parent's perspective")
        pdf.body(f"Your primary concern is: {profile.get('primary_concern') or '-'}. "
                 f"You believe your child may benefit from: {profile.get('benefit_from') or '-'}.")
    if profile.get("notes"):
        pdf.h3("Additional notes"); pdf.body(profile["notes"])

    _section_break(pdf)
    pdf.h2("4. Professional involvement")
    if involvement.get("roles"):
        pdf.h3("Currently involved"); pdf.bullets(involvement["roles"])
    if involvement.get("meetings"):
        pdf.h3("Upcoming or recommended meetings")
        for m in involvement["meetings"]:
            pdf.body(f"{m.get('name')} — status: {m.get('current_status')}. Suggested: {m.get('next_step')}.")

    _section_break(pdf)
    pdf.h2("5. Co-parenting assessment")
    for label, key in (("Information sharing", "information_sharing"),
                       ("Consistency between homes", "consistency_between_homes"),
                       ("Decision-making", "decision_making")):
        block = coparenting.get(key) or {}
        color = _RATING_COLORS.get(block.get("rating") or "", (61, 26, 120))
        pdf.h3(label)
        pdf.pill(f"Rating: {block.get('rating') or '-'}", color=color)
        items = block.get("shared_items") or block.get("items") or []
        if items: pdf.bullets(items)
        if block.get("gap_items"):
            pdf.small("Possible gaps: " + ", ".join(block["gap_items"]))

    _section_break(pdf)
    pdf.h2("6. Areas of alignment"); pdf.bullets(report.get("alignment_areas") or [])
    _section_break(pdf)
    pdf.h2("7. Areas requiring attention"); pdf.bullets(report.get("attention_areas") or [])
    _section_break(pdf)
    pdf.h2("8. Recommended support level")
    color = _RATING_COLORS.get(
        "Strong" if level.get("level") == 1 else "Developing" if level.get("level") == 2 else "Needs Attention",
        (61, 26, 120))
    pdf.pill(f"Level {level.get('level', '-')} — {level.get('name') or ''}", color=color)
    if level.get("description"): pdf.body(level["description"])
    if level.get("next_steps"):
        pdf.h3("Suggested next steps"); pdf.bullets(level["next_steps"])

    _section_break(pdf)
    pdf.h2("9. Practical options and resources"); pdf.bullets(report.get("practical_options") or [])

    _section_break(pdf)
    pdf.h2("10. Your action plan")
    for row in report.get("action_plan") or []:
        pdf.body(f"Priority {row.get('priority')}: {row.get('action')} — "
                 f"{row.get('detail')} · Owner: {row.get('responsible')} · "
                 f"Due: {row.get('target') or '____'}")

    _section_break(pdf)
    pdf.h2("11. Foundation statement"); pdf.body(report.get("foundation_statement") or "")
    _section_break(pdf)
    pdf.h2("12. Questions for the other parent or professional")
    pdf.bullets(report.get("questions_for_school_or_parent") or [])
    _section_break(pdf)
    pdf.h2("13. Final child-focused summary"); pdf.body(report.get("final_summary") or "")
    _section_break(pdf)
    # "How this report was built" — provenance for the recipient.
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="deepdive")
    _section_break(pdf)
    pdf.small(report.get("disclaimer") or "")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
