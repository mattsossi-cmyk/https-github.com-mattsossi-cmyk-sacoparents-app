"""Educational Deep Dive — report content + branded Letter-sized PDF."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from edu_deep_questions import DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION, DECISION_TOPICS
from edu_deep_scoring import score_deep_dive


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
    scored = score_deep_dive(responses)
    concerns_selected = responses.get("s1_concerns") or []
    concern_notes = (responses.get("s1_concern_notes") or "").strip()

    # ---- assemble section entries only for visible/answered sections ----
    sections_out: List[Dict[str, Any]] = []
    for state in scored["sections"]:
        if not state["is_visible"] or not state["answered"]:
            continue
        entry: Dict[str, Any] = {
            "id": state["id"],
            "name": state["name"],
            "number": state["number"],
            "is_flagged": state["is_flagged"],
            "flag_reasons": state["flag_reasons"],
            "is_strength": state["is_strength"],
            "strength_reasons": state["strength_reasons"],
        }
        tpl = _SECTION_TEMPLATES.get(state["id"], {})
        if state["is_strength"] and tpl.get("strength"):
            entry["strength_text"] = tpl["strength"]
        if state["is_flagged"] and tpl.get("challenge"):
            entry["challenge_text"] = tpl["challenge"]
            entry["recommendations"] = tpl.get("recommendations") or []
        sections_out.append(entry)

    # ---- summary counters ----
    flagged_names = [s["name"] for s in sections_out if s["is_flagged"]]
    strength_names = [s["name"] for s in sections_out if s["is_strength"]]

    return {
        "generated_at": _now_iso(),
        "deep_dive_version": DEEP_DIVE_VERSION,
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "assessment_date": _now_iso()[:10],
        },
        "profile": {
            "school_setting":  responses.get("s1_school_setting"),
            "grade_level":     responses.get("s1_grade_level"),
            "school_state":    responses.get("s1_school_state"),
            "is_texas":        scored["is_texas"],
            "concerns":        concerns_selected,
            "concern_notes":   concern_notes,
        },
        "summary": {
            "answered_sections":  scored["totals"]["answered"],
            "flagged_sections":   scored["totals"]["flagged"],
            "strength_sections":  scored["totals"]["strengths"],
            "flagged_names":      flagged_names,
            "strength_names":     strength_names,
        },
        "sections": sections_out,
        "disclaimer": (
            "This report reflects one parent's perspective. It does not diagnose, "
            "determine parental fitness, or provide legal advice. Share it with your "
            "mediator, IEP team, or family professional for their input."
        ),
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


def build_deep_dive_pdf(*, report: Dict[str, Any]) -> bytes:
    pdf = _PDF()
    pdf.add_page()

    cover = report.get("cover") or {}
    profile = report.get("profile") or {}
    summary = report.get("summary") or {}

    # ----- Header -----
    pdf.h1("Educational Needs — Deep Dive Report")
    pdf.body(f"For {cover.get('parent_name') or '-'} · About {cover.get('child_name') or '-'} · {cover.get('assessment_date') or ''}")
    pdf.small(report.get("disclaimer") or "")

    # ----- Profile -----
    _section_break(pdf)
    pdf.h2("1. Educational Profile")
    profile_bits = []
    if profile.get("school_setting"): profile_bits.append(f"Setting: {profile['school_setting']}")
    if profile.get("grade_level"): profile_bits.append(f"Grade: {profile['grade_level']}")
    if profile.get("school_state"): profile_bits.append(f"State: {profile['school_state']}")
    if profile_bits:
        pdf.body(" · ".join(profile_bits))
    concerns = profile.get("concerns") or []
    if concerns:
        pdf.h3("Educational concerns")
        pdf.bullets(concerns)
    if profile.get("concern_notes"):
        pdf.h3("Additional notes")
        pdf.body(profile["concern_notes"])

    # ----- At a glance -----
    _section_break(pdf)
    pdf.h2("At a glance")
    pdf.body(
        f"{summary.get('answered_sections', 0)} sections completed. "
        f"{summary.get('flagged_sections', 0)} area(s) flagged for follow-up. "
        f"{summary.get('strength_sections', 0)} area(s) recognised as strengths."
    )
    if summary.get("flagged_names"):
        pdf.h3("Sections flagged for follow-up")
        pdf.bullets(summary["flagged_names"])
    if summary.get("strength_names"):
        pdf.h3("Areas of current strength")
        pdf.bullets(summary["strength_names"])

    # ----- Section-by-section (only if flagged OR a strength) -----
    for s in report.get("sections") or []:
        if not (s.get("is_flagged") or s.get("is_strength")):
            continue
        _section_break(pdf)
        pdf.h2(f"{s['number']}. {s['name']}")
        if s.get("is_strength"):
            pdf.pill("Strength", color=(31, 92, 59))
            pdf.body(s.get("strength_text") or "")
            if s.get("strength_reasons"):
                pdf.small("Signals: " + "; ".join(s["strength_reasons"]))
        if s.get("is_flagged"):
            pdf.pill("Area to develop", color=(176, 42, 42))
            pdf.body(s.get("challenge_text") or "")
            if s.get("flag_reasons"):
                pdf.small("Signals: " + "; ".join(s["flag_reasons"]))
            if s.get("recommendations"):
                pdf.h3("Recommendations")
                pdf.bullets(s["recommendations"])

    # ----- Disclaimer footer -----
    _section_break(pdf)
    pdf.small(report.get("disclaimer") or "")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
