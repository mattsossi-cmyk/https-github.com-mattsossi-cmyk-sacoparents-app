"""Complete Alignment Report — renders the 10-section unified PDF for
either a single parent (individual variant) or a case with two
parents (joint variant).

The 10-section skeleton is IDENTICAL to sacoparentsalign.com's
universal Co-Parenting Agreement — same brand family, same neutral
guardrails, so a professional trained on Align opens either variant
and knows exactly where to look.

Sections (headings verbatim):
    01. Complete Alignment Overview
    02. Your Child at the Center
    03. Where You Align            (joint) / Your Reflection Summary (individual)
    04. Where Your Perspectives Differ (joint) / Areas You've Explored (individual)
    05. What Might Your Child Need?
    06. Options & Resources
    07. Questions for Parent Conversation
    08. Professional Conversation Guide
    09. Parent Action Plan
    10. Complete Alignment Summary

Clinical guardrails baked in at render-time:
  * "Educational and organizational tool" watermark on every page.
  * No adjudicative language anywhere — no "should", "must", "wrong".
  * Options & Resources content is neutral, non-directive.
  * Copyright footer + sacoparentsalign.com link on every page via
    the shared `render_pdf_copyright` helper.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from pdf_base import _safe, _section_break, render_pdf_copyright


# --- Palette (mirrors the app's dark-purple / warm-ink treatment) -----------
_INK = (26, 19, 48)            # #1A1330 body text
_INK_SOFT = (75, 69, 103)      # #4B4567 muted body
_BRAND = (61, 26, 120)         # #3D1A78 primary purple
_BRAND_SOFT = (239, 233, 249)  # #EFE9F9 tint fill
_BRAND_LINE = (214, 207, 232)  # #D6CFE8 dividers
_ACCENT_GREEN = (30, 106, 66)  # #1E6A42 "shared" / "aligned" markers
_ACCENT_AMBER = (170, 106, 0)  # #AA6A00 "one-side" / "explore" markers
_ACCENT_DIM = (133, 126, 156)  # #857E9C "not yet" markers


def _rgb(pdf: FPDF, target: str, color) -> None:
    if target == "text":
        pdf.set_text_color(*color)
    elif target == "fill":
        pdf.set_fill_color(*color)
    elif target == "draw":
        pdf.set_draw_color(*color)


class _CompletePDF(FPDF):
    """FPDF subclass with the shared brand header / footer.

    A single subclass covers both variants — `variant` is stashed on
    the instance so the header can render the right label (Individual
    vs Joint) without threading state through every render call.
    """

    def __init__(self, *, variant: str, subtitle: str) -> None:
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 24, 18)
        self.set_title("SA CoParents - Complete Alignment Report")
        self.set_author("SA CoParents")
        self._variant_label = "Joint Report" if variant == "joint" else "Individual Report"
        self._subtitle = subtitle

    def header(self) -> None:
        self.set_y(8)
        # Brand mark left, variant chip right.
        self.set_font("Helvetica", "B", 9)
        _rgb(self, "text", _BRAND)
        self.cell(0, 5, _safe("SA CoParents  -  Complete Alignment Report"), align="L", new_x=XPos.LMARGIN, new_y=YPos.TOP)
        self.set_font("Helvetica", "B", 7)
        _rgb(self, "text", _BRAND)
        _rgb(self, "fill", _BRAND_SOFT)
        chip = f"  {self._variant_label.upper()}  "
        w = self.get_string_width(chip) + 2
        self.set_x(self.w - self.r_margin - w)
        self.cell(w, 5, _safe(chip), align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        # Subtitle strip.
        self.set_font("Helvetica", "", 7.5)
        _rgb(self, "text", _ACCENT_DIM)
        self.cell(
            0, 4,
            _safe(
                f"{self._subtitle}    |    Educational and organizational tool  -  not a diagnosis or court submission"
            ),
            align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        # Thin brand rule under the header block.
        _rgb(self, "draw", _BRAND_LINE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(4)
        # Reset text colour so body sections start in ink.
        _rgb(self, "text", _INK)

    def footer(self) -> None:
        # Page number strip.
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        _rgb(self, "text", _ACCENT_DIM)
        self.cell(0, 4, _safe(f"Page {self.page_no()} of {{nb}}"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Shared copyright + click-through link, same as every other report.
        render_pdf_copyright(self)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _h1(pdf: FPDF, number: str, title: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 15)
    _rgb(pdf, "text", _BRAND)
    pdf.cell(0, 8, _safe(f"{number}   {title}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)


def _lead(pdf: FPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    _rgb(pdf, "text", _INK_SOFT)
    pdf.multi_cell(0, 5, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _body(pdf: FPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10.5)
    _rgb(pdf, "text", _INK)
    pdf.multi_cell(0, 5.5, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _bullet(pdf: FPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10.5)
    _rgb(pdf, "text", _INK)
    # Bullet marker at the left margin, then indent 4mm and wrap the
    # body text into the remaining page width. Explicit width avoids
    # fpdf2's `w=0 → w - x` math which can go negative if the cursor
    # ever drifted past the right margin on a previous write.
    pdf.cell(4, 5.5, _safe("-"), new_x=XPos.RIGHT, new_y=YPos.TOP)
    body_w = pdf.w - pdf.l_margin - pdf.r_margin - 4
    pdf.multi_cell(body_w, 5.5, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _status_pill(pdf: FPDF, label: str, colour) -> None:
    pdf.set_font("Helvetica", "B", 7)
    _rgb(pdf, "text", colour)
    _rgb(pdf, "fill", _BRAND_SOFT)
    txt = f"  {label.upper()}  "
    w = pdf.get_string_width(txt) + 2
    pdf.cell(w, 4.5, _safe(txt), align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    _rgb(pdf, "text", _INK)


def _kv_row(pdf: FPDF, key: str, value: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9.5)
    _rgb(pdf, "text", _BRAND)
    pdf.cell(48, 5.5, _safe(key), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 10)
    _rgb(pdf, "text", _INK)
    value_w = pdf.w - pdf.l_margin - pdf.r_margin - 48
    pdf.multi_cell(value_w, 5.5, _safe(value or "-"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(0.5)


# ---------------------------------------------------------------------------
# Section builders — Individual variant
# ---------------------------------------------------------------------------

def _section_1_overview(pdf: FPDF, *, agg: Dict[str, Any], parent_name: str, variant: str) -> None:
    _h1(pdf, "01", "Complete Alignment Overview")
    if variant == "individual":
        _lead(pdf,
            f"This report brings every reflection {parent_name} has completed on SA CoParents "
            f"into one place. It follows the same ten-section structure every SA CoParents "
            f"Align report uses, so a mediator, attorney, or therapist reading it always "
            f"knows where to look."
        )
    else:
        _lead(pdf,
            "This report brings both parents' reflections into one place. Each section "
            "surfaces where the two perspectives already share ground, where they differ, "
            "and where the conversation still has raw material to build."
        )
    pdf.ln(1)
    counts = agg.get("counts") or {}
    if variant == "individual":
        _kv_row(pdf, "Reflections completed:", f"{counts.get('completed', 0)} of {counts.get('total', 0)} lanes")
    else:
        _kv_row(pdf, "Shared lanes:", f"{counts.get('shared', 0)} of {counts.get('total', 0)}")
        _kv_row(pdf, "One-side lanes:", f"{counts.get('one_side', 0)} of {counts.get('total', 0)}")
    generated = _fmt_ts(agg.get("generated_at"))
    _kv_row(pdf, "Report generated:", generated)
    _section_break(pdf)


def _section_2_child(pdf: FPDF, *, agg: Dict[str, Any]) -> None:
    _h1(pdf, "02", "Your Child at the Center")
    _lead(pdf,
        "Every section that follows is written to keep the child - not the dispute - at "
        "the center of the conversation. Neutral, non-diagnostic, and never a judgment "
        "about which parent is right."
    )
    child = agg.get("child_name") or "your child"
    _body(pdf,
        f"Throughout this report the reflections are read through {child}'s eyes: "
        f"what a steady daily rhythm looks like, what feels predictable across both homes, "
        f"and where a small alignment shift would meaningfully lower the stress in {child}'s "
        f"week."
    )
    _section_break(pdf)


def _section_3_individual_summary(pdf: FPDF, *, agg: Dict[str, Any], parent_name: str) -> None:
    _h1(pdf, "03", "Your Reflection Summary")
    _lead(pdf,
        f"A quick recap of what {parent_name} wrote in the Foundation Statement - the "
        f"prompts that anchor every other lane on SA CoParents."
    )
    foundation = _lane_by_id(agg, "foundation")
    prompts = (foundation or {}).get("prompts") or {}
    if not prompts:
        _body(pdf,
            f"{parent_name} has not yet completed the Foundation Statement. Once written, "
            f"the four prompts appear here verbatim so the professional can read the parent's "
            f"own words rather than a paraphrase."
        )
        _section_break(pdf)
        return
    for key, label in (
        ("child_lens", "Through the child's eyes"),
        ("own_part", "The part I own"),
        ("best_outcome", "The best realistic outcome"),
        ("coparent_feedback", "What I want my co-parent to hear"),
    ):
        val = prompts.get(key)
        if val:
            _kv_row(pdf, f"{label}:", val)
    _section_break(pdf)


def _section_4_individual_areas(pdf: FPDF, *, agg: Dict[str, Any]) -> None:
    _h1(pdf, "04", "Areas You've Explored")
    _lead(pdf,
        "Every lane on SA CoParents surfaces a different corner of the co-parenting picture. "
        "Below is where you already have raw material - and where a next reflection would "
        "give the conversation more to work from."
    )
    for lane in agg.get("lanes") or []:
        if lane["id"] == "foundation":
            # Foundation is expanded in section 3 already.
            continue
        completed = bool(lane.get("completed"))
        title = lane.get("title") or lane["id"]
        pdf.set_font("Helvetica", "B", 10.5)
        _rgb(pdf, "text", _BRAND)
        pdf.cell(80, 5.5, _safe(title), new_x=XPos.RIGHT, new_y=YPos.TOP)
        if completed:
            _status_pill(pdf, "Completed", _ACCENT_GREEN)
        else:
            _status_pill(pdf, "Not yet", _ACCENT_DIM)
        _body(pdf, lane.get("blurb") or "")
    _section_break(pdf)


# ---------------------------------------------------------------------------
# Section builders — Joint variant
# ---------------------------------------------------------------------------

def _section_3_joint_align(pdf: FPDF, *, agg: Dict[str, Any], parents: List[str]) -> None:
    _h1(pdf, "03", "Where You Align")
    _lead(pdf,
        f"Lanes where both {parents[0]} and {parents[1]} have completed a reflection. "
        f"Shared ground is the raw material an alignment conversation builds from - "
        f"the point is not that the answers match, but that both perspectives are on "
        f"the table."
    )
    shared = [ln for ln in (agg.get("lanes") or []) if ln.get("status") == "shared"]
    if not shared:
        _body(pdf,
            "Neither parent has completed the same lane yet. The best next step is for "
            "each parent to complete the Foundation Statement so this section can begin "
            "to populate."
        )
    else:
        for lane in shared:
            pdf.set_font("Helvetica", "B", 10.5)
            _rgb(pdf, "text", _BRAND)
            pdf.cell(80, 5.5, _safe(lane.get("title") or lane["id"]), new_x=XPos.RIGHT, new_y=YPos.TOP)
            _status_pill(pdf, "Shared", _ACCENT_GREEN)
            _body(pdf, lane.get("blurb") or "")
    _section_break(pdf)


def _section_4_joint_differ(pdf: FPDF, *, agg: Dict[str, Any], parents: List[str]) -> None:
    _h1(pdf, "04", "Where Your Perspectives Differ")
    _lead(pdf,
        "Lanes only one parent has completed - or lanes neither has reached yet. These "
        "are not disagreements. They are places where the professional can invite the "
        "other perspective before the conversation begins."
    )
    for lane in agg.get("lanes") or []:
        if lane.get("status") == "shared":
            continue
        pdf.set_font("Helvetica", "B", 10.5)
        _rgb(pdf, "text", _BRAND)
        pdf.cell(80, 5.5, _safe(lane.get("title") or lane["id"]), new_x=XPos.RIGHT, new_y=YPos.TOP)
        if lane.get("status") == "one-side":
            only = parents[0] if lane.get("parent_a_completed") else parents[1]
            _status_pill(pdf, f"Only {only}", _ACCENT_AMBER)
        else:
            _status_pill(pdf, "Not yet", _ACCENT_DIM)
        _body(pdf, lane.get("blurb") or "")
    _section_break(pdf)


# ---------------------------------------------------------------------------
# Shared sections (5-10)
# ---------------------------------------------------------------------------

def _section_5_child_needs(pdf: FPDF, *, agg: Dict[str, Any], variant: str) -> None:
    _h1(pdf, "05", "What Might Your Child Need?")
    _lead(pdf,
        "Excerpts from the Child Needs Statement - medical, educational, psychological, "
        "and behavioural signals a professional should hold in mind. Reflections here are "
        "never diagnostic and never predict what a court will decide."
    )
    if variant == "joint":
        # STRICT PRIVACY: per aggregator policy, each parent's Child
        # Needs Statement short-answers are stripped from the joint
        # view (same rule as Foundation Statement prompts). The joint
        # report surfaces alignment STATUS on this lane; each parent
        # opens their OWN Complete Alignment Report for the excerpts.
        a_cn = _lane_by_id(agg.get("parent_a") or {}, "child_needs") or {}
        b_cn = _lane_by_id(agg.get("parent_b") or {}, "child_needs") or {}
        if not a_cn.get("completed") and not b_cn.get("completed"):
            _body(pdf,
                "Neither parent has completed the Child Needs Statement yet. When "
                "completed, each parent's alignment status appears here."
            )
        else:
            statuses = []
            if a_cn.get("completed"):
                statuses.append(f"Parent A has completed the Child Needs Statement.")
            if b_cn.get("completed"):
                statuses.append(f"Parent B has completed the Child Needs Statement.")
            _body(pdf, " ".join(statuses))
            _body(pdf,
                "Each parent's specific answers stay in their own Complete Alignment "
                "Report. The professional can request them alongside this joint report "
                "under explicit dual-consent."
            )
    else:
        notes = _extract_child_needs_highlights(agg)
        if not notes:
            _body(pdf,
                "The Child Needs Statement has not been completed yet. Its excerpts will "
                "appear here once you finish that reflection."
            )
        else:
            for n in notes:
                _bullet(pdf, n)
    _section_break(pdf)


def _section_6_options(pdf: FPDF) -> None:
    _h1(pdf, "06", "Options & Resources")
    _lead(pdf,
        "Neutral, non-directive options a professional may draw from. Nothing on this "
        "page recommends one parent's approach over the other's."
    )
    for opt in (
        "Set a shared weekly cadence for information exchange - a 15-minute Sunday-evening "
        "handover note often lowers weekday friction.",
        "Agree on one written channel (email or a co-parenting app) for scheduling and "
        "keep synchronous calls for time-sensitive decisions only.",
        "If a lane feels stuck, invite the professional to walk through one Foundation "
        "prompt out loud with each parent before returning to the disagreement.",
        "Book a follow-up reflection 4-6 weeks after any change so the plan can be "
        "adjusted before small frictions turn structural.",
    ):
        _bullet(pdf, opt)
    _section_break(pdf)


def _section_7_questions(pdf: FPDF, *, variant: str) -> None:
    _h1(pdf, "07", "Questions for Parent Conversation")
    _lead(pdf,
        "Ask-out-loud questions the parents (with the professional's support) can work "
        "through together. Neutral phrasing - designed to open reflection, not defend a "
        "position."
    )
    prompts = [
        "Which one part of the weekly rhythm, if it were more predictable, would lower our child's stress the most?",
        "When did we last agree on something small? What made that agreement possible?",
        "What do we each need from the other during handovers to keep them calm for our child?",
        "If a professional could hold one thing steady for us across the next six weeks, what would it be?",
    ] if variant == "joint" else [
        "Which reflection surprised me the most - and why?",
        "Where do I feel most confident in what I wrote? Where am I still working it out?",
        "If my co-parent read only one paragraph of this report, which one do I hope they read?",
        "What small step in the next two weeks would move a lane from 'not yet' to 'completed'?",
    ]
    for p in prompts:
        _bullet(pdf, p)
    _section_break(pdf)


def _section_8_pro_guide(pdf: FPDF, *, variant: str) -> None:
    _h1(pdf, "08", "Professional Conversation Guide")
    _lead(pdf,
        "A short guide for the professional. Not clinical advice - a scaffold for the "
        "first (or next) session that keeps the conversation child-focused."
    )
    steps = (
        "Open with the child. Read Section 02 aloud before referencing any parent answer.",
        "Anchor on shared ground. Section 03 is intentionally first among the perspective "
        "sections - start where the parents already agree.",
        "Move to differences without adjudicating. Section 04 is a list of subjects, not a "
        "verdict; use it to schedule what to discuss, not to score.",
        "Close with an action plan. Section 09 gives each parent one commitment for the "
        "next 2-4 weeks that a follow-up can review.",
    ) if variant == "joint" else (
        "Read this report before the first session. Section 03 gives you the parent's "
        "own words - avoid paraphrasing back.",
        "Note which lanes read as 'not yet' in Section 04 and offer the parent a gentle "
        "invitation to explore one before the next session.",
        "Use Section 07 as the structure for the session itself - the questions are "
        "neutral and designed to open, not adjudicate.",
        "Section 09 turns reflection into a follow-up commitment - keep it small and "
        "reviewable.",
    )
    for s in steps:
        _bullet(pdf, s)
    _section_break(pdf)


def _section_9_action_plan(pdf: FPDF, *, variant: str, parents: Optional[List[str]] = None) -> None:
    _h1(pdf, "09", "Parent Action Plan")
    _lead(pdf,
        "One small commitment for the next 2-4 weeks. Keep it specific, keep it "
        "reviewable. The follow-up session will start here."
    )
    if variant == "joint" and parents:
        _kv_row(pdf, f"{parents[0]} will:", "___________________________________________________________")
        _kv_row(pdf, f"{parents[1]} will:", "___________________________________________________________")
    else:
        _kv_row(pdf, "I will:", "___________________________________________________________")
    _kv_row(pdf, "We will review this on:", "________ / ________ / ________")
    _section_break(pdf)


def _section_10_summary(pdf: FPDF, *, agg: Dict[str, Any], variant: str) -> None:
    _h1(pdf, "10", "Complete Alignment Summary")
    counts = agg.get("counts") or {}
    if variant == "joint":
        _body(pdf,
            f"Shared lanes: {counts.get('shared', 0)}     "
            f"One-side lanes: {counts.get('one_side', 0)}     "
            f"Total lanes: {counts.get('total', 0)}."
        )
    else:
        _body(pdf,
            f"Reflections completed: {counts.get('completed', 0)} of {counts.get('total', 0)}."
        )
    _body(pdf,
        "SA CoParents does not decide which parent is right or wrong. This report "
        "organizes reflections into a shared starting point so a mediator, attorney, "
        "or therapist can guide the next conversation with the child at the center."
    )
    _lead(pdf,
        "Not a diagnosis, not a court submission, not legal or medical advice. "
        "Educational and organizational only."
    )


# ---------------------------------------------------------------------------
# Small utility helpers
# ---------------------------------------------------------------------------

def _lane_by_id(agg: Dict[str, Any], lane_id: str) -> Optional[Dict[str, Any]]:
    for ln in (agg.get("lanes") or []):
        if ln.get("id") == lane_id:
            return ln
    return None


def _extract_child_needs_highlights(agg: Optional[Dict[str, Any]]) -> List[str]:
    if not agg:
        return []
    lane = _lane_by_id(agg, "child_needs") or {}
    highlights = lane.get("highlights") or []
    return [h for h in highlights if isinstance(h, str) and h.strip()]


def _fmt_ts(iso: Any) -> str:
    if not isinstance(iso, str):
        return "-"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%d %b %Y")
    except Exception:  # noqa: BLE001
        return "-"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_individual_pdf(agg: Dict[str, Any], *, parent_name: str) -> bytes:
    """Render the individual variant of the Complete Alignment Report.

    Args:
        agg: Output of `aggregate_for_user`.
        parent_name: Human-facing name for the reflecting parent -
                     used in headings and prompts. Defaults handled
                     by the route ('you' when no name available).
    Returns:
        Raw PDF bytes ready for a StreamingResponse.
    """
    subtitle = f"Prepared for {parent_name}" if parent_name else "Prepared for you"
    pdf = _CompletePDF(variant="individual", subtitle=subtitle)
    pdf.alias_nb_pages()
    pdf.add_page()
    _section_1_overview(pdf, agg=agg, parent_name=parent_name or "you", variant="individual")
    _section_2_child(pdf, agg=agg)
    _section_3_individual_summary(pdf, agg=agg, parent_name=parent_name or "You")
    _section_4_individual_areas(pdf, agg=agg)
    _section_5_child_needs(pdf, agg=agg, variant="individual")
    _section_6_options(pdf)
    _section_7_questions(pdf, variant="individual")
    _section_8_pro_guide(pdf, variant="individual")
    _section_9_action_plan(pdf, variant="individual")
    _section_10_summary(pdf, agg=agg, variant="individual")
    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1", errors="replace")


def render_joint_pdf(agg: Dict[str, Any], *, parents: List[str]) -> bytes:
    """Render the joint variant. `parents` is a two-element list of
    human-facing names, `[parent_a_name, parent_b_name]`."""
    if len(parents) != 2:
        raise ValueError("Joint report requires exactly two parent names.")
    subtitle = f"Prepared for {parents[0]} and {parents[1]}"
    pdf = _CompletePDF(variant="joint", subtitle=subtitle)
    pdf.alias_nb_pages()
    pdf.add_page()
    _section_1_overview(pdf, agg=agg, parent_name="", variant="joint")
    _section_2_child(pdf, agg=agg)
    _section_3_joint_align(pdf, agg=agg, parents=parents)
    _section_4_joint_differ(pdf, agg=agg, parents=parents)
    _section_5_child_needs(pdf, agg=agg, variant="joint")
    _section_6_options(pdf)
    _section_7_questions(pdf, variant="joint")
    _section_8_pro_guide(pdf, variant="joint")
    _section_9_action_plan(pdf, variant="joint", parents=parents)
    _section_10_summary(pdf, agg=agg, variant="joint")
    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1", errors="replace")
