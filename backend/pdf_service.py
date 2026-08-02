"""PDF generation for the Mediation Prep Summary using fpdf2."""
import os
from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF
from PIL import Image


SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
SAND = (245, 243, 233)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)

# Org branding shown in every PDF
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"
ORG_ADDRESS = "16607 Blanco #703, San Antonio, Texas 78232"
ORG_PHONE = "210-224-1667"
ORG_EMAIL = "mattsossi@bsossi.com"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")

# Numbered branded posters (public/images/steps/*) that also appear in the intro
# slideshow and every Watch-First card. Reused here as full-page section covers so
# the printed prep summary mirrors the on-screen visual language.
_STEPS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "images", "steps")
)
POSTER_PATHS = {
    "assess":      os.path.join(_STEPS_DIR, "step-safety-assessment.png"),
    "understand":  os.path.join(_STEPS_DIR, "step-comm-style.png"),
    "identify":    os.path.join(_STEPS_DIR, "step-child-goals.png"),
    "foundation":  os.path.join(_STEPS_DIR, "step-foundation.png"),
    "prepare":     os.path.join(_STEPS_DIR, "step-readiness.png"),
    "communicate": os.path.join(_STEPS_DIR, "step-issues.png"),
    "better":      os.path.join(_STEPS_DIR, "step-priority.png"),
}

# Downscaled poster cache — full-res source posters are 1024x1536 (~2MB each);
# for print they only need to be ~720px wide, saving ~85% file size per cover.
_POSTER_CACHE_DIR = os.path.join(os.path.dirname(__file__), "assets", "poster_cache")
_POSTER_CACHE_MAX_W = 720  # px, matches 130mm at ~140 DPI


def _cached_poster(poster_key: str) -> str | None:
    """Return a path to a print-optimised copy of the given poster.
    Regenerates the cache if the source has changed (mtime-based)."""
    src = POSTER_PATHS.get(poster_key)
    if not src or not os.path.exists(src):
        return None
    os.makedirs(_POSTER_CACHE_DIR, exist_ok=True)
    dst = os.path.join(_POSTER_CACHE_DIR, f"{poster_key}.jpg")
    try:
        src_mtime = os.path.getmtime(src)
        if os.path.exists(dst) and os.path.getmtime(dst) >= src_mtime:
            return dst
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > _POSTER_CACHE_MAX_W:
                new_h = int(im.height * _POSTER_CACHE_MAX_W / im.width)
                im = im.resize((_POSTER_CACHE_MAX_W, new_h), Image.LANCZOS)
            im.save(dst, "JPEG", quality=85, optimize=True)
        return dst
    except Exception:
        return src  # Fall back to the raw source if anything goes wrong.


# fpdf2's built-in Helvetica is a latin-1 font and can't encode characters like
# em-dashes, curly quotes, ellipses, or unicode bullets that AI output sometimes
# contains. We replace them with ASCII equivalents before drawing.
_UNICODE_REPLACEMENTS = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201C": '"',   # left double quote
    "\u201D": '"',   # right double quote
    "\u2026": "...", # ellipsis
    "\u2022": "*",   # bullet
    "\u00A0": " ",   # nbsp
}


def _safe(text: Any) -> str:
    """Return a latin-1 safe representation of any text for fpdf2 built-in fonts."""
    if text is None:
        return ""
    s = str(text)
    for ch, repl in _UNICODE_REPLACEMENTS.items():
        s = s.replace(ch, repl)
    # Fallback: strip anything still outside latin-1 so we never crash a PDF render.
    return s.encode("latin-1", "replace").decode("latin-1")


class PrepSummaryPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Flag toggled during poster cover pages so header/footer stay hidden.
        self._chromeless = False

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        if self._chromeless:
            return
        # Subtle diagonal "REVIEW BEFORE SHARING" watermark behind content.
        from pdf_watermark import stamp_watermark
        stamp_watermark(self)
        # Soft sand band
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 38, "F")
        # Logo on the left (24mm square block, vertically centered in the band)
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=7, w=24, h=24)
            except Exception:
                pass
        # Title + tagline (offset right of the logo)
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 17)
        self.set_xy(42, 9)
        self.cell(0, 8, "Mediation Preparation Summary", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MID)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_NAME} - {ORG_TAGLINE}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_ADDRESS}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(44)

    def footer(self):
        if self._chromeless:
            return
        from pdf_watermark import stamp_signature_line
        stamp_signature_line(self)
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Confidential - Prepared for mediation. {ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}",
            align="C",
            ln=1,
        )

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*SAGE)
        self.cell(0, 8, text, ln=1)
        self.set_draw_color(*SAGE)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(15, y, 60, y)
        self.ln(3)
        self.set_text_color(*TEXT_DARK)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet_list(self, items: List[str]):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_DARK)
        for item in items:
            self.set_x(18)
            self.cell(4, 6, chr(149))  # bullet
            self.multi_cell(0, 6, str(item))
            self.ln(0.5)
        self.ln(1)

    def poster_cover(self, poster_key: str) -> None:
        """
        Insert a full-page cover using one of the numbered branded posters
        (see POSTER_PATHS). The poster is 2:3 portrait; A4 is ~1:1.414 so we
        center it horizontally and leave breathing room top and bottom on a
        soft sand background — mirrors the app's Watch-First card aesthetic.
        Header and footer are suppressed on the cover page.
        """
        path = _cached_poster(poster_key)
        if not path or not os.path.exists(path):
            return
        self._chromeless = True
        try:
            self.add_page()
            # Sand background across the full A4 canvas.
            self.set_fill_color(*SAND)
            self.rect(0, 0, 210, 297, "F")
            # 2:3 portrait poster fitted into 130 x 195 mm, centered.
            img_w, img_h = 130, 195
            x = (210 - img_w) / 2
            y = (297 - img_h) / 2 - 6
            try:
                self.image(path, x=x, y=y, w=img_w, h=img_h)
            except Exception:
                pass
        finally:
            self._chromeless = False


def _render_meta(pdf: "PrepSummaryPDF", user_name: str, mediation_date: str | None) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Prepared for: {user_name}", ln=1)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=1)
    if mediation_date:
        pdf.cell(0, 6, f"Mediation date: {mediation_date}", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def _render_readiness_banner(pdf: "PrepSummaryPDF", summary: Dict[str, Any]) -> None:
    pdf.ln(3)
    pdf.set_fill_color(*SAND)
    pdf.set_font("Helvetica", "B", 12)
    label = summary.get("readiness_label", "")
    score = summary.get("readiness_score", 0)
    pdf.cell(0, 10, f"Readiness: {label}  ({score}/100)", ln=1, fill=True)


def _render_priority_agenda(pdf: "PrepSummaryPDF", agenda: list) -> None:
    pdf.section_title("Priority Agenda")
    pdf.set_font("Helvetica", "", 11)
    for it in agenda:
        rank = it.get("rank", "?")
        topic = it.get("topic", "")
        cat = it.get("category", "")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(10, 6, f"{rank}.")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"{topic}  [{cat}]")
    pdf.ln(2)


def _render_child_goals(
    pdf: "PrepSummaryPDF",
    summary: Dict[str, Any],
    child_goals: Dict[str, Any] | None,
) -> None:
    pdf.section_title("Child-Centered Goals")
    pdf.body_text(summary.get("child_goals_summary", ""))
    if child_goals and child_goals.get("selected_goals"):
        pdf.bullet_list(child_goals["selected_goals"])


def build_summary_pdf(
    user_name: str,
    summary: Dict[str, Any],
    child_goals: Dict[str, Any] | None = None,
    mediation_date: str | None = None,
    excluded_sections: set | list | None = None,
    signed_by: str | None = None,
    signed_at: str | None = None,
    signed_note: str | None = None,
) -> bytes:
    ex = set(excluded_sections or [])
    pdf = PrepSummaryPDF(format="A4")
    if signed_by and signed_at:
        pdf._signed_by = signed_by
        pdf._signed_at = signed_at
        if signed_note:
            pdf._signed_note = signed_note
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 44, 15)

    # Opening cover — #4 "Create Your Foundation Statement" poster.
    pdf.poster_cover("foundation")

    pdf.add_page()

    _render_meta(pdf, user_name, mediation_date)
    if "readiness" not in ex:
        _render_readiness_banner(pdf, summary)

    if "changes_since_last" not in ex and summary.get("changes_since_last"):
        pdf.section_title("What's Changed Since Last Time")
        pdf.body_text(summary["changes_since_last"])

    if "child_goals" not in ex:
        # Cover for Child-Centered Goals — #3 poster.
        pdf.poster_cover("identify")
        pdf.add_page()
        _render_child_goals(pdf, summary, child_goals)

    if "top_concerns" not in ex:
        pdf.section_title("Top Concerns")
        pdf.bullet_list(summary.get("top_concerns", []))

    if "priority_agenda" not in ex:
        # Cover for Priority Agenda — #5 "Prepare for Mediation" poster.
        pdf.poster_cover("prepare")
        pdf.add_page()
        _render_priority_agenda(pdf, summary.get("priority_agenda", []))

    if "flexibility_areas" not in ex:
        pdf.section_title("Flexibility Areas")
        pdf.bullet_list(summary.get("flexibility_areas", []))

    if "communication_goals" not in ex:
        # Cover for Communication Goals — #6 "Strengthen Communication" poster.
        pdf.poster_cover("communicate")
        pdf.add_page()
        pdf.section_title("Communication Goals")
        pdf.bullet_list(summary.get("communication_goals", []))

    if "notes_for_mediator" not in ex:
        pdf.section_title("Notes for the Mediator")
        pdf.body_text(summary.get("notes_for_mediator", ""))

    # "How this report was built" — provenance for the recipient.
    pdf.add_page()
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="mediation")

    # Closing cover — #7 "Better Co-Parenting, Better Outcomes" poster.
    pdf.poster_cover("better")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


# ============ Co-Parenting Agreement PDF ============
class AgreementPDF(FPDF):
    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        # Subtle diagonal "REVIEW BEFORE SHARING" watermark behind content.
        from pdf_watermark import stamp_watermark
        stamp_watermark(self)
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 38, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=7, w=24, h=24)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 17)
        self.set_xy(42, 9)
        self.cell(0, 8, "Co-Parenting Agreement - Draft", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MID)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_NAME} - A starting point for discussion", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_ADDRESS}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(44)

    def footer(self):
        from pdf_watermark import stamp_signature_line
        stamp_signature_line(self)
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Draft only - not a legal document. {ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}",
            align="C",
            ln=1,
        )

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*SAGE)
        self.cell(0, 8, text, ln=1)
        self.set_draw_color(*SAGE)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(15, y, 60, y)
        self.ln(3)
        self.set_text_color(*TEXT_DARK)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def clause_list(self, items: list) -> None:
        """Render a list of {area, agreement} dicts as labelled clauses."""
        self.set_font("Helvetica", "", 11)
        for it in items:
            area = it.get("area", "")
            clause = it.get("agreement", "")
            self.set_x(18)
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 6, area, ln=1)
            self.set_x(22)
            self.set_font("Helvetica", "", 11)
            self.multi_cell(0, 6, clause)
            self.ln(0.5)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 11)
        for item in items:
            self.set_x(18)
            self.cell(4, 6, chr(149))
            self.multi_cell(0, 6, str(item))
            self.ln(0.5)
        self.ln(1)


def _agreement_section(pdf: AgreementPDF, title: str, items: list) -> None:
    if not items:
        return
    pdf.section_title(title)
    pdf.clause_list(items)


def _agreement_meta(
    pdf: AgreementPDF, user_name: str, mediation_date: str | None
) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Drafted by: {user_name}", ln=1)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=1)
    if mediation_date:
        pdf.cell(0, 6, f"Mediation date: {mediation_date}", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def _agreement_overview(pdf: AgreementPDF, overview: str | None) -> None:
    if not overview:
        return
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(0, 6, overview)
    pdf.set_text_color(*TEXT_DARK)


def _agreement_priority_items(pdf: AgreementPDF, priorities: list) -> None:
    if not priorities:
        return
    pdf.section_title("Priority Topics to Discuss")
    pdf.set_font("Helvetica", "", 11)
    for it in priorities:
        rank = it.get("rank", "?")
        topic = it.get("topic", "")
        cat = it.get("category", "")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(10, 6, f"{rank}.")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"{topic}  [{cat}]")
    pdf.ln(2)


def _agreement_signature_lines(pdf: AgreementPDF) -> None:
    pdf.ln(8)
    pdf.set_draw_color(*TEXT_MID)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.line(120, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_xy(20, pdf.get_y() + 1)
    pdf.cell(70, 5, "Parent A signature / date")
    pdf.set_xy(120, pdf.get_y())
    pdf.cell(70, 5, "Parent B signature / date")


def build_agreement_pdf(
    user_name: str,
    agreement: Dict[str, Any],
    mediation_date: str | None = None,
    excluded_sections: set | list | None = None,
    signed_by: str | None = None,
    signed_at: str | None = None,
    signed_note: str | None = None,
) -> bytes:
    ex = set(excluded_sections or [])
    pdf = AgreementPDF(format="A4")
    if signed_by and signed_at:
        pdf._signed_by = signed_by
        pdf._signed_at = signed_at
        if signed_note:
            pdf._signed_note = signed_note
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 44, 15)
    pdf.add_page()

    _agreement_meta(pdf, user_name, mediation_date)
    _agreement_overview(pdf, agreement.get("overview"))

    if "changes_since_last" not in ex and agreement.get("changes_since_last"):
        pdf.section_title("Updates from the Previous Draft")
        pdf.body_text(agreement["changes_since_last"])

    if "shared_goals" not in ex and agreement.get("shared_goals"):
        pdf.section_title("Shared Goals for Our Child")
        pdf.bullet_list(agreement["shared_goals"])

    if "communication" not in ex:
        _agreement_section(pdf, "Communication", agreement.get("communication", []))
    if "child_needs" not in ex:
        _agreement_section(pdf, "Child Needs", agreement.get("child_needs", []))
    if "household_rules" not in ex:
        _agreement_section(pdf, "Household Rules", agreement.get("household_rules", []))
    if "priority_items" not in ex:
        _agreement_priority_items(pdf, agreement.get("priority_items", []))

    if "open_for_discussion" not in ex and agreement.get("open_for_discussion"):
        pdf.section_title("Open for Discussion")
        pdf.bullet_list(agreement["open_for_discussion"])

    if "closing_note" not in ex and agreement.get("closing_note"):
        pdf.section_title("A Note from the Draft")
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, agreement["closing_note"])

    _agreement_signature_lines(pdf)

    # "How this report was built" — provenance for the recipient.
    pdf.add_page()
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="mediation")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
