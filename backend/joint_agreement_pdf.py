"""PDF renderer for the Joint Co-Parenting Agreement Draft.

Layout:
  * Cover page: title, both parents' names, source-agreement IDs, and a
    prominent DRAFT-FOR-DISCUSSION disclaimer.
  * Section pages: each section (shared goals, communication, child needs,
    household rules, priority topics, still open) as three stacked blocks:
      - Both proposed  (green)
      - <Parent A> only (purple)
      - <Parent B> only (teal)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)


PAGE_W = 210
LEFT_M = 15
RIGHT_M = 15
CONTENT_W = PAGE_W - LEFT_M - RIGHT_M


class _JointAgreementPDF(FPDF):
    def __init__(self, *, generated_at: str, share_id: str):
        super().__init__()
        self._generated_at = generated_at
        self._share_id = share_id
        self._is_cover = False

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        if self._is_cover:
            return
        self.set_fill_color(*SAND)
        self.rect(0, 0, PAGE_W, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=3, w=16, h=16)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(32, 5)
        self.cell(0, 5, "Joint Co-Parenting Agreement Draft", ln=1)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_MID)
        self.set_x(32)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(26)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Draft for discussion - Not a signed agreement or court order - "
            f"Generated {self._generated_at} - Share {self._share_id[:10]}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


def _body(pdf: _JointAgreementPDF, text: str, *, size: int = 9, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", size)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.6, text)


# ---------------------------------------------------------------------------
# 5-bucket Parent View renderers — mirrors JointAgreementParentView.jsx so
# the printed PDF matches the on-screen tone. Each bucket gets a coloured
# strip, an intro, and a list of items in the bucket-specific shape.
# ---------------------------------------------------------------------------

# Bucket accent colours (RGB) — kept in the same visual family as the
# on-screen JSX component so parents recognise the mapping.
_BUCKET_ACCENTS: Dict[str, tuple] = {
    "what_you_both_proposed":            (31, 92, 59),   # green
    "where_you_have_different_ideas":    (138, 91, 0),   # amber
    "may_need_refinement":               (176, 42, 42),  # red
    "options_to_consider":               (61, 26, 120),  # purple
    "questions_for_next_conversation":   (15, 111, 111), # teal
}


def _bucket_header(pdf: _JointAgreementPDF, title: str, description: str,
                   count: Any, accent: tuple):
    """Coloured strip + title + description + optional count pill."""
    pdf.ln(2)
    strip_y = pdf.get_y()
    pdf.set_fill_color(*accent)
    pdf.rect(LEFT_M, strip_y, 3, 10, "F")
    pdf.set_xy(LEFT_M + 5, strip_y)
    pdf.set_text_color(*accent)
    pdf.set_font("Helvetica", "B", 12)
    title_text = title
    if isinstance(count, int) and count > 0:
        title_text = f"{title}  ({count})"
    pdf.cell(0, 5, title_text, ln=1)
    pdf.set_x(LEFT_M + 5)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(CONTENT_W - 5, 4.2, description)
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1)


def _bucket_empty(pdf: _JointAgreementPDF, msg: str):
    pdf.set_x(LEFT_M + 5)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(CONTENT_W - 5, 4.2, msg)
    pdf.set_text_color(*TEXT_DARK)


def _render_both_proposed_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "No overlapping clauses yet - as each parent finalises their "
            "draft, the shared clauses will surface here first.",
        )
        return
    pdf.set_font("Helvetica", "", 9)
    for it in items:
        area = (it.get("area") or it.get("section_title") or "").strip()
        text = (it.get("text") or "").strip()
        if area:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(0, 4.2, area, ln=1)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.multi_cell(CONTENT_W - 5, 4.4, "- " + text)
        pdf.ln(0.4)


def _render_different_ideas_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any],
                                   parent_a: str, parent_b: str):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "No divergent clauses - you've both proposed the same things "
            "across every section.",
        )
        return
    col_w = (CONTENT_W - 5 - 4) / 2
    for it in items:
        topic = (it.get("topic") or "").strip()
        a_text = (it.get("parent_a") or "").strip()
        b_text = (it.get("parent_b") or "").strip()
        if topic:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(0, 4.2, topic, ln=1)
            pdf.set_text_color(*TEXT_DARK)
        # Two-column strip.
        y_top = pdf.get_y()
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_xy(LEFT_M + 5, y_top)
        pdf.cell(col_w, 4, parent_a)
        pdf.set_text_color(15, 111, 111)
        pdf.set_xy(LEFT_M + 5 + col_w + 4, y_top)
        pdf.cell(col_w, 4, parent_b)
        pdf.ln(4.3)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 8.7)
        a_y = pdf.get_y()
        pdf.set_xy(LEFT_M + 5, a_y)
        pdf.multi_cell(col_w, 4.3, a_text or "(no clause proposed)")
        end_a = pdf.get_y()
        pdf.set_xy(LEFT_M + 5 + col_w + 4, a_y)
        pdf.multi_cell(col_w, 4.3, b_text or "(no clause proposed)")
        end_b = pdf.get_y()
        pdf.set_y(max(end_a, end_b))
        pdf.ln(1)


def _render_refinement_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "Nothing is currently flagged as unresolved. If a topic feels "
            "unsettled, add it to your Foundation Statement so it "
            "surfaces here.",
        )
        return
    for it in items:
        topic = (it.get("topic") or "Open item").strip()
        detail = (it.get("detail") or "").strip()
        both_flagged = bool(it.get("both_flagged"))
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*TEXT_DARK)
        prefix = topic
        if both_flagged:
            prefix = f"{topic}  [both flagged]"
        pdf.cell(0, 4.4, prefix, ln=1)
        if detail:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "", 8.8)
            pdf.set_text_color(*TEXT_MID)
            pdf.multi_cell(CONTENT_W - 5, 4.3, detail)
            pdf.set_text_color(*TEXT_DARK)
        pdf.ln(0.4)


def _render_options_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    for it in (data.get("items") or []):
        title = (it.get("title") or "").strip()
        detail = (it.get("detail") or "").strip()
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 4.4, title, ln=1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "", 8.8)
        pdf.multi_cell(CONTENT_W - 5, 4.3, detail)
        pdf.ln(0.5)


def _render_questions_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    for idx, it in enumerate((data.get("items") or []), start=1):
        topic = (it.get("topic") or "").strip()
        q = (it.get("question") or "").strip()
        if topic:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(15, 111, 111)
            pdf.cell(0, 4.2, f"{idx}. {topic}", ln=1)
            pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "I", 8.8)
        pdf.multi_cell(CONTENT_W - 5, 4.3, f'"{q}"')
        pdf.ln(0.5)


_BUCKET_RENDERERS = {
    "what_you_both_proposed":         "both",
    "where_you_have_different_ideas": "diff",
    "may_need_refinement":            "refine",
    "options_to_consider":            "options",
    "questions_for_next_conversation": "questions",
}


def _render_parent_view(pdf: _JointAgreementPDF, parent_view: Dict[str, Any],
                        parent_a: str, parent_b: str):
    """Render the 5-bucket parent-friendly view. Order preserved so the
    on-screen and PDF experiences march in lockstep."""
    for key in (
        "what_you_both_proposed",
        "where_you_have_different_ideas",
        "may_need_refinement",
        "options_to_consider",
        "questions_for_next_conversation",
    ):
        data = parent_view.get(key)
        if not data:
            continue
        accent = _BUCKET_ACCENTS.get(key, INFO)
        _bucket_header(
            pdf,
            data.get("title") or key.replace("_", " ").title(),
            data.get("description") or "",
            data.get("count"),
            accent,
        )
        mode = _BUCKET_RENDERERS.get(key)
        if mode == "both":
            _render_both_proposed_bucket(pdf, data)
        elif mode == "diff":
            _render_different_ideas_bucket(pdf, data, parent_a, parent_b)
        elif mode == "refine":
            _render_refinement_bucket(pdf, data)
        elif mode == "options":
            _render_options_bucket(pdf, data)
        elif mode == "questions":
            _render_questions_bucket(pdf, data)
        pdf.ln(1.5)


def _bucket(
    pdf: _JointAgreementPDF, label: str, items: List[Any], colour, *,
    parent_a: str, parent_b: str, mode: str,
):
    """Render one bucket (both_proposed / parent_a_only / parent_b_only)."""
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*colour)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, label.upper(), ln=1)
    pdf.set_draw_color(*colour)
    y = pdf.get_y()
    pdf.line(LEFT_M, y, LEFT_M + 30, y)
    pdf.set_text_color(*TEXT_DARK)

    if not items:
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*TEXT_MID)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.4, "(none)")
        pdf.set_text_color(*TEXT_DARK)
        return

    if mode == "both":
        for item in items:
            area = item.get("area") or ""
            a_text = item.get("parent_a_text") or ""
            b_text = item.get("parent_b_text") or ""
            if area:
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.set_text_color(*TEXT_MID)
                pdf.set_x(LEFT_M)
                pdf.cell(0, 4.2, area, ln=1)
                pdf.set_text_color(*TEXT_DARK)
            # Two-column strip.
            col_w = (CONTENT_W - 4) / 2
            y_top = pdf.get_y()
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*TEXT_MID)
            pdf.set_xy(LEFT_M, y_top)
            pdf.cell(col_w, 4, parent_a)
            pdf.set_xy(LEFT_M + col_w + 4, y_top)
            pdf.cell(col_w, 4, parent_b)
            pdf.ln(4.3)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*TEXT_DARK)
            a_y = pdf.get_y()
            pdf.set_xy(LEFT_M, a_y)
            pdf.multi_cell(col_w, 4.3, a_text)
            end_a = pdf.get_y()
            pdf.set_xy(LEFT_M + col_w + 4, a_y)
            pdf.multi_cell(col_w, 4.3, b_text)
            end_b = pdf.get_y()
            pdf.set_y(max(end_a, end_b))
            pdf.ln(0.5)
    else:  # a_only / b_only
        pdf.set_font("Helvetica", "", 8.7)
        for item in items:
            area = item.get("area") or ""
            text = item.get("text") or ""
            pdf.set_x(LEFT_M)
            if area:
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.set_text_color(*TEXT_MID)
                pdf.cell(0, 4.2, area, ln=1)
                pdf.set_font("Helvetica", "", 8.7)
                pdf.set_text_color(*TEXT_DARK)
            pdf.set_x(LEFT_M)
            pdf.multi_cell(CONTENT_W, 4.4, "- " + text)
            pdf.ln(0.3)


def _cover_page(pdf: _JointAgreementPDF, payload: Dict[str, Any]):
    pdf._is_cover = True
    pdf.add_page()
    pdf.set_fill_color(*SAND)
    pdf.rect(0, 0, PAGE_W, 60, "F")
    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=15, y=14, w=24, h=24)
        except Exception:
            pass
    pdf.set_xy(50, 18)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 6, ORG_NAME, ln=1)
    pdf.set_x(50)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 4, ORG_TAGLINE, ln=1)
    pdf.set_text_color(*TEXT_DARK)

    pdf.set_xy(LEFT_M, 72)
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(CONTENT_W, 8, payload.get("report_title") or "")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, "Draft compiled from both parents' individual drafts", ln=1)
    pdf.set_text_color(*TEXT_DARK)

    # Parents.
    pdf.ln(4)
    for label, value in [
        ("Parent A", payload.get("parent_a_name") or "-"),
        ("Parent B", payload.get("parent_b_name") or "-"),
        ("Generated", pdf._generated_at),
        ("Share ID", payload.get("share_id") or "-"),
    ]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(LEFT_M)
        pdf.cell(35, 5, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, value, ln=1)

    # Draft-for-discussion banner.
    pdf.ln(6)
    pdf.set_fill_color(255, 246, 216)
    pdf.set_draw_color(*WARN)
    pdf.set_line_width(0.5)
    banner_y = pdf.get_y()
    pdf.rect(LEFT_M, banner_y, CONTENT_W, 65, "DF")
    pdf.set_xy(LEFT_M + 4, banner_y + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WARN)
    pdf.cell(0, 5, "This is a draft for discussion.", ln=1)
    pdf.set_xy(LEFT_M + 4, banner_y + 10)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(CONTENT_W - 8, 4.2, payload.get("disclaimer") or "")

    # Neutral-language note.
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.2, payload.get("neutral_language_note") or "")
    pdf.set_text_color(*TEXT_DARK)

    # Convergence at a glance.
    summary = payload.get("summary") or {}
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*OK)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, "AT A GLANCE", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.5,
        f"- {summary.get('both_proposed', 0)} clauses proposed by BOTH parents\n"
        f"- {summary.get('parent_a_only', 0)} clauses proposed by "
        f"{payload.get('parent_a_name') or 'Parent A'} only\n"
        f"- {summary.get('parent_b_only', 0)} clauses proposed by "
        f"{payload.get('parent_b_name') or 'Parent B'} only\n"
        f"- Convergence: {summary.get('converged_pct', 0)}%")

    pdf._is_cover = False


def build_joint_agreement_pdf(payload: Dict[str, Any]) -> bytes:
    """Render the joint agreement PDF and return raw bytes.

    Layout mirrors the on-screen JointAgreement page:
      * Cover page (title, parents, disclaimer, at-a-glance summary)
      * 5-bucket Parent View (matches JointAgreementParentView.jsx)
      * Appendix A - Detailed Item Breakdown (the original section
        row-strip layout, kept for professional review)
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pdf = _JointAgreementPDF(
        generated_at=now,
        share_id=payload.get("share_id") or "-",
    )
    pdf.set_auto_page_break(auto=True, margin=18)

    _cover_page(pdf, payload)

    parent_a = payload.get("parent_a_name") or "Parent A"
    parent_b = payload.get("parent_b_name") or "Parent B"

    # ------------------------------------------------------------------
    # Parent View (5 buckets) - primary body of the PDF from this
    # iteration onwards. Falls back gracefully if the payload predates
    # the parent-view build (older cached payloads).
    # ------------------------------------------------------------------
    parent_view = payload.get("parent_view") or {}
    if parent_view:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 7, "Parent View", ln=1)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*TEXT_MID)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(
            CONTENT_W, 4.5,
            "A parent-friendly walkthrough of your merged draft, grouped "
            "into five buckets. The complete side-by-side layout follows "
            "in Appendix A.",
        )
        pdf.set_text_color(*TEXT_DARK)
        pdf.ln(2)
        _render_parent_view(pdf, parent_view, parent_a, parent_b)

    # ------------------------------------------------------------------
    # Appendix A - Detailed Item Breakdown (the original row-strip).
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 7, "Appendix A - Detailed Item Breakdown", ln=1)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(
        CONTENT_W, 4.5,
        "Every clause shown verbatim under the parent who proposed it, "
        "grouped by section. Intended for attorneys, mediators, and "
        "therapists reviewing the full draft.",
    )
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(2)

    for section in payload.get("sections") or []:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 6, section.get("title") or "", ln=1)
        desc = section.get("description")
        if desc:
            _body(pdf, desc, size=8.5, italic=True)

        _bucket(pdf, "Both proposed", section.get("both_proposed") or [], OK,
                parent_a=parent_a, parent_b=parent_b, mode="both")
        _bucket(pdf, f"{parent_a} only", section.get("parent_a_only") or [], INFO,
                parent_a=parent_a, parent_b=parent_b, mode="a")
        _bucket(pdf, f"{parent_b} only", section.get("parent_b_only") or [], WARN,
                parent_a=parent_a, parent_b=parent_b, mode="b")
        pdf.ln(2)

    # Next-step callout at the very end.
    next_step = payload.get("next_step") or ""
    if next_step:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*INFO)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 5, "SUGGESTED NEXT STEP", ln=1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.5, next_step)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
