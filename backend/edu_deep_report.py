"""Educational Deep Dive — report content + branded Letter-sized PDF."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from edu_deep_questions import DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION
from edu_deep_scoring import score_deep_dive
from edu_deep_journey import build_journey_report


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")


# ---------------------------------------------------------------------------
# Section templates — strength / challenge / recommendation strings.
# The report only emits Challenge + Recommendation when scoring flags a
# section, and only emits Strength when scoring marks a section as a strength.
# ---------------------------------------------------------------------------
_SECTION_TEMPLATES = {
    "s2": {
        "strength": "Parents consistently attend conferences and share educational information.",
        "challenge": "Only one parent regularly attends teacher meetings, resulting in inconsistent understanding of classroom expectations.",
        "recommendations": [
            "Create a shared meeting summary within 48 hours of every conference.",
            "Identify 2-3 educational goals together before each meeting.",
            "Both parents should be listed on the school contact list.",
        ],
    },
    "s3": {
        "strength": "Parents actively participate and advocate together during ARD meetings.",
        "challenge": "Conflict between parents is reducing the effectiveness of ARD participation.",
        "recommendations": [
            "Develop a shared agenda before every ARD meeting.",
            "Review the school's proposed recommendations together in writing beforehand.",
            "Bring a written list of questions to keep the meeting child-focused.",
        ],
    },
    "s4": {
        "strength": "Parents understand and consistently reinforce IEP goals across both homes.",
        "challenge": "One parent is unfamiliar with the current IEP goals, accommodations, or progress.",
        "recommendations": [
            "Review the IEP together each grading period and identify one shared priority.",
            "Share IEP progress reports between homes within 48 hours.",
            "Attend at least one IEP meeting together per school year.",
        ],
    },
    "s5": {
        "strength": "Both parents apply 504 accommodations consistently.",
        "challenge": "504 accommodations are not being implemented consistently at school or between homes.",
        "recommendations": [
            "Request a written copy of the current 504 Plan and keep it in both homes.",
            "Set a shared annual reminder to review the 504 Plan with the school.",
            "Confirm each teacher is aware of the accommodations at the start of the year.",
        ],
    },
    "s6": {
        "strength": "Parents collaborate with the school counsellor to reinforce coping strategies.",
        "challenge": "Communication with the school counsellor or support staff is inconsistent.",
        "recommendations": [
            "Schedule a periodic check-in with the counsellor each quarter.",
            "Share counsellor updates between households within one week.",
            "Reinforce the counsellor's home strategies in both households.",
        ],
    },
    "s7": {
        "strength": "Both parents are committed to the current academic support services.",
        "challenge": "Attendance, communication, or progress monitoring for academic supports is inconsistent.",
        "recommendations": [
            "Agree on which parent transports and supervises which sessions.",
            "Share progress reports from the tutor or program monthly.",
            "Set a joint review point (e.g. every 8 weeks) to decide whether to continue.",
        ],
    },
    "s8": {
        "strength": "Homework and home learning are supported consistently in both homes.",
        "challenge": "Homework routines vary meaningfully between homes.",
        "recommendations": [
            "Agree on a shared homework routine (time, place, and completion check).",
            "Confirm both homes have a quiet study space with needed supplies.",
            "Communicate about missed or late work in writing.",
        ],
    },
    "s9": {
        "strength": "Communication with school staff is respectful and shared between parents.",
        "challenge": "School information is not reaching both parents consistently.",
        "recommendations": [
            "Add both parents to every school portal, email list, and text alert.",
            "Confirm the school will send duplicate copies of report cards and notices.",
            "Use one shared calendar for all school events.",
        ],
    },
    "s10": {
        "strength": "Parents consistently agree on major educational decisions.",
        "challenge": "Several major educational decisions rarely see agreement, which can delay support for the child.",
        "recommendations": [
            "Bring unresolved decisions to a neutral mediator before the next school year.",
            "Agree on a decision-making framework in writing (which decisions need consensus, which are unilateral).",
            "Focus on the child's stated goals when a decision is stuck.",
        ],
    },
    "s11": {
        "strength": "Parents advocate together with confidence and preparation.",
        "challenge": "Advocacy could be more prepared, informed, or coordinated.",
        "recommendations": [
            "Take a free parent-advocacy orientation from your state's Parent Training and Information (PTI) Center.",
            "Bring a written list of questions to every school meeting.",
            "Ask for copies of every educational report and read them before the next meeting.",
        ],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_deep_dive_report(
    *, parent_name: Optional[str], child_name: Optional[str],
    responses: Dict[str, Any],
) -> Dict[str, Any]:
    """v2 report builder — pulls score-card + score-card-driven sections
    (one per part) into the same top-level shape the frontend and PDF
    renderer already know."""
    scored = score_deep_dive(responses)

    # Per-section entries. In v2 every visible section corresponds to a
    # scored part; we surface it as "flagged" (low) or "strength" (high)
    # so the existing report chrome still lights up.
    sections_out: List[Dict[str, Any]] = []
    for state in scored["sections"]:
        if state["answered"] == 0:
            continue
        is_flag = state["band"] == "low"
        is_strong = state["band"] == "high"
        entry: Dict[str, Any] = {
            "id":               state["id"],
            "name":             state["name"],
            "number":           state["number"],
            "is_flagged":       is_flag,
            "flag_reasons":     [f"Alignment {state['percent']}% - below the moderate band."] if is_flag else [],
            "is_strength":      is_strong,
            "strength_reasons": [f"Alignment {state['percent']}% - both homes are holding this consistently."] if is_strong else [],
            "percent":          state["percent"],
        }
        sections_out.append(entry)

    flagged_names = [s["name"] for s in sections_out if s["is_flagged"]]
    strength_names = [s["name"] for s in sections_out if s["is_strength"]]

    # v2 journey (score-card style)
    journey = build_journey_report(
        parent_name=parent_name,
        child_name=child_name,
        responses=responses,
    )
    journey["cover"] = {
        **journey["cover"],
        "assessment_date": _now_iso()[:10],
    }

    return {
        "generated_at":      _now_iso(),
        "deep_dive_version": DEEP_DIVE_VERSION,
        "cover":             journey["cover"],
        "profile": {
            "school_setting":  "",  # retired in v2 but kept in payload
            "grade_level":     "",
            "school_state":    "",
            "is_texas":        False,
            "concerns":        [],
            "concern_notes":   "",
        },
        "summary": {
            "answered_sections":  scored["totals"]["answered"],
            "flagged_sections":   scored["totals"]["flagged"],
            "strength_sections":  scored["totals"]["strengths"],
            "flagged_names":      flagged_names,
            "strength_names":     strength_names,
        },
        "sections":          sections_out,
        "score_card":        journey["score_card"],
        "overview":          journey["overview"],
        "support_summary":   journey["support_summary"],
        "child_profile":     journey["child_profile"],
        "school_involvement": journey["school_involvement"],
        "co_parenting_assessment": journey["co_parenting_assessment"],
        "alignment_areas":   journey["alignment_areas"],
        "attention_areas":   journey["attention_areas"],
        "support_level":     journey["support_level"],
        "practical_options": journey["practical_options"],
        "action_plan":       journey["action_plan"],
        "foundation_statement": journey["foundation_statement"],
        "questions_for_school_or_parent": journey["questions_for_school_or_parent"],
        "final_summary":     journey["final_summary"],
        "disclaimer":        journey["disclaimer"],
    }


# ---------------------------------------------------------------------------
# PDF rendering — tight Letter layout, matching the SNC v2 brand palette.
# ---------------------------------------------------------------------------

def _safe(t: Any) -> str:
    if t is None:
        return ""
    s = str(t)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _PDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(14, 24, 14)
        self.alias_nb_pages()
        self.compress = False

    def header(self):
        from pdf_watermark import stamp_watermark
        stamp_watermark(self)
        self.set_fill_color(245, 240, 232); self.rect(0, 0, self.w, 18, "F")
        if os.path.exists(LOGO_PATH):
            try: self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
            except Exception: pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe("SA CoParents  ·  Educational Needs Deep Dive"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe("Relational Mediation Prep"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):
        from pdf_watermark import stamp_signature_line
        stamp_signature_line(self)
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Educational Deep Dive Report  ·  Page {self.page_no()} of {{nb}}"), align="C")

    def h1(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 17); self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 7.5, _safe(t)); self.ln(0.5)
    def h2(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 12); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 6, _safe(t)); self.ln(0.2)
    def h3(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 9.5); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 4.8, _safe(t))
    def body(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "", 9.3); self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 4.4, _safe(t)); self.ln(0.2)
    def small(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "I", 8); self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 3.8, _safe(t)); self.ln(0.2)
    def bullets(self, items):
        self.set_font("Helvetica", "", 9.3); self.set_text_color(30, 24, 54)
        for it in items or []:
            s = str(it or "").strip()
            if not s: continue
            self.set_x(self.l_margin); self.multi_cell(self.epw, 4.4, _safe(f"  -  {s}"))
        self.ln(0.2)
    def pill(self, text: str, color=(61, 26, 120)):
        self.set_font("Helvetica", "B", 8.5); self.set_text_color(*color)
        self.set_x(self.l_margin); self.multi_cell(self.epw, 4.4, _safe(text))
        self.set_text_color(30, 24, 54); self.ln(0.2)


def _section_break(pdf: _PDF):
    pdf.ln(1.5)
    pdf.set_draw_color(220, 214, 232); pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1.5)


_RATING_COLORS = {
    "Strong": (31, 92, 59),
    "Developing": (170, 116, 40),
    "Needs Attention": (176, 42, 42),
    "Not enough info": (110, 100, 130),
}


def build_deep_dive_pdf(*, report: Dict[str, Any],
                        signed_by: Optional[str] = None,
                        signed_at: Optional[str] = None,
                        signed_note: Optional[str] = None) -> bytes:
    """Render the SA CoParents journey Educational Deep Dive report as a
    Letter-sized branded PDF matching the shared report style.
    """
    pdf = _PDF()
    if signed_by and signed_at:
        pdf._signed_by = signed_by
        pdf._signed_at = signed_at
        if signed_note:
            pdf._signed_note = signed_note
    pdf.add_page()

    cover = report.get("cover") or {}
    overview = report.get("overview") or {}
    support_summary = report.get("support_summary") or {}
    child_profile = report.get("child_profile") or {}
    involvement = report.get("school_involvement") or {}
    coparenting = report.get("co_parenting_assessment") or {}
    support_level = report.get("support_level") or {}

    # 1. Report Overview
    pdf.h1("SA CoParents Educational Needs Assessment Report")
    header_bits = [f"Parent: {cover.get('parent_name') or '-'}",
                   f"Child: {cover.get('child_name') or '-'}"]
    if cover.get("grade_level"): header_bits.append(f"Grade: {cover['grade_level']}")
    if cover.get("school_state"): header_bits.append(f"State: {cover['school_state']}")
    if cover.get("assessment_date"): header_bits.append(f"Date: {cover['assessment_date']}")
    pdf.body(" · ".join(header_bits))
    _section_break(pdf)
    pdf.h2("1. Report overview")
    pdf.h3("Purpose")
    pdf.bullets(overview.get("purpose_bullets") or [])
    pdf.small(report.get("disclaimer") or "")

    # 2. Educational Support Summary
    _section_break(pdf)
    pdf.h2("2. Your educational support summary")
    for area in support_summary.get("ratings") or []:
        pdf.set_font("Helvetica", "B", 9.7); pdf.set_text_color(30, 24, 54)
        pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 4.6, _safe(area.get("area") or ""))
        color = _RATING_COLORS.get(area.get("rating") or "", (61, 26, 120))
        pdf.pill(f"Rating: {area.get('rating') or '-'}", color=color)
        if area.get("narrative"):
            pdf.body(area["narrative"])
        pdf.ln(0.5)
    if support_summary.get("overall_narrative"):
        pdf.h3("Overall")
        pdf.body(support_summary["overall_narrative"])

    # AI executive summary (if present)
    if report.get("ai_summary"):
        _section_break(pdf)
        pdf.h2("Executive summary")
        pdf.small("AI-generated · neutral · non-diagnostic")
        pdf.body(report["ai_summary"])

    # 3. Child's Educational Profile
    _section_break(pdf)
    pdf.h2("3. Your child's educational profile")
    pdf.h3("Strengths identified")
    pdf.bullets(child_profile.get("strengths") or [])
    if child_profile.get("concerns"):
        pdf.h3("Concerns identified")
        pdf.bullets(child_profile["concerns"])
    if child_profile.get("primary_concern") or child_profile.get("benefit_from"):
        pdf.h3("Parent's perspective")
        pdf.body(
            f"Your primary educational concern is: {child_profile.get('primary_concern') or '-'}. "
            f"You believe your child may benefit from: {child_profile.get('benefit_from') or '-'}."
        )
    if child_profile.get("notes"):
        pdf.h3("Additional notes")
        pdf.body(child_profile["notes"])

    # 4. School and Professional Involvement
    _section_break(pdf)
    pdf.h2("4. School and professional involvement")
    if involvement.get("roles"):
        pdf.h3("Currently involved")
        pdf.bullets(involvement["roles"])
    if involvement.get("meetings"):
        pdf.h3("Upcoming or recommended meetings")
        for m in involvement["meetings"]:
            pdf.body(
                f"{m.get('name')} — status: {m.get('current_status')}. "
                f"Suggested: {m.get('next_step')}."
            )

    # 5. Educational Co-Parenting Assessment
    _section_break(pdf)
    pdf.h2("5. Educational co-parenting assessment")
    for label, key in (
        ("Information sharing", "information_sharing"),
        ("Consistency between homes", "consistency_between_homes"),
        ("Educational decision-making", "decision_making"),
    ):
        block = coparenting.get(key) or {}
        color = _RATING_COLORS.get(block.get("rating") or "", (61, 26, 120))
        pdf.h3(label)
        pdf.pill(f"Rating: {block.get('rating') or '-'}", color=color)
        items = block.get("items") or block.get("shared_items") or []
        if items:
            pdf.bullets(items)
        if block.get("gap_items"):
            pdf.small("Possible gaps: " + ", ".join(block["gap_items"]))

    # 6. Areas of alignment
    _section_break(pdf)
    pdf.h2("6. Areas of alignment")
    pdf.bullets(report.get("alignment_areas") or [])

    # 7. Areas requiring attention
    _section_break(pdf)
    pdf.h2("7. Areas requiring attention")
    pdf.bullets(report.get("attention_areas") or [])

    # 8. Recommended Educational Support Level
    _section_break(pdf)
    pdf.h2(f"8. Recommended educational support level")
    pdf.pill(f"Level {support_level.get('level', '-')} — {support_level.get('name') or ''}",
             color=_RATING_COLORS.get(
                 "Strong" if support_level.get("level") == 1
                 else "Developing" if support_level.get("level") == 2
                 else "Needs Attention",
                 (61, 26, 120)))
    if support_level.get("description"):
        pdf.body(support_level["description"])
    if support_level.get("next_steps"):
        pdf.h3("Suggested next steps")
        pdf.bullets(support_level["next_steps"])

    # 9. Practical Options & Resources
    _section_break(pdf)
    pdf.h2("9. Practical options and resources")
    pdf.bullets(report.get("practical_options") or [])

    # 10. Educational Action Plan
    _section_break(pdf)
    pdf.h2("10. Your educational action plan")
    for row in report.get("action_plan") or []:
        pdf.body(
            f"Priority {row.get('priority')}: {row.get('action')} — "
            f"{row.get('detail')} · Owner: {row.get('responsible')} · Due: {row.get('target') or '____'}"
        )

    # 11. Educational Foundation Statement
    _section_break(pdf)
    pdf.h2("11. Educational foundation statement")
    pdf.body(report.get("foundation_statement") or "")

    # 12. Questions
    _section_break(pdf)
    pdf.h2("12. Questions for the other parent or school")
    pdf.bullets(report.get("questions_for_school_or_parent") or [])

    # 13. Final child-focused summary + disclaimer
    _section_break(pdf)
    pdf.h2("13. Final child-focused summary")
    pdf.body(report.get("final_summary") or "")
    _section_break(pdf)
    # "How this report was built" — provenance for the recipient.
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="deepdive")
    _section_break(pdf)
    pdf.small(report.get("disclaimer") or "")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
