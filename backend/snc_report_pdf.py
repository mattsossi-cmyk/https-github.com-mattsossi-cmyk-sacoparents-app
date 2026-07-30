"""PDF renderer for the Special Needs Co-Parenting Assessment Report.

Consumes the deterministic report produced by
`snc_report_content.build_individual_report()` and writes an FPDF
Individual Parent Report that follows the 17-section blueprint.

Structure:
    Cover · Purpose · At-a-Glance · Category Summary table ·
    Child Profile · Sections 4-13 (5-part pattern each) ·
    Section 12 Safety (or redacted notice) · Action Plan · 30-day steps ·
    Questions for the other parent · Closing summary · Disclaimer

Safety redaction is driven entirely by the `include_safety` flag on the
report payload — shared/comparison views pass `include_safety=False` when
building the report, and this renderer respects that.
"""
from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Dict, Iterable, List

from fpdf import FPDF


# Shared SA CoParents branded logo used by all product PDFs.
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"


_CLASSIFICATION_COLOR = {
    "Established strength":      (31, 92, 59),
    "Generally supported":       (61, 26, 120),
    "Coordination opportunity":  (140, 90, 44),
    "Significant inconsistency": (194, 72, 31),
    "Priority concern":          (176, 42, 42),
    "Not enough data":           (110, 110, 130),
    "Separate review":           (110, 110, 130),
}


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _SNCReportPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 30, 15)
        self.alias_nb_pages()
        # Disable stream compression so test assertions can search the raw
        # PDF bytes for content. Filesize impact is negligible for our tests.
        self.compress = False

    def header(self):
        # Sand band + logo, matching the shared SA CoParents PDF header.
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=4, w=14, h=14)
            except Exception:  # noqa: BLE001
                pass
        self.set_xy(30, 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(61, 26, 120)
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parenting Report"), ln=1)
        self.set_x(30)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(110, 100, 130)
        self.cell(0, 4, _safe(ORG_TAGLINE), ln=1)
        self.set_draw_color(220, 214, 232)
        self.set_line_width(0.3)
        self.line(15, 23, self.w - 15, 23)
        self.set_y(28)
        self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Individual Parent Report  ·  Page {self.page_no()} of {{nb}}"),
                  align="C")

    # --- typographic helpers -------------------------------------------
    def h1(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 9, _safe(text))
        self.ln(1)

    def h2(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 7, _safe(text))
        self.ln(0.5)

    def h3(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 5.5, _safe(text))

    def body(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 5.2, _safe(text))
        self.ln(0.5)

    def bullets(self, items: Iterable[str]):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 24, 54)
        for it in items:
            if not str(it).strip():
                continue
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.2, _safe(f"  -  {it}"))
        self.ln(0.5)

    def pill(self, text: str, rgb):
        self.set_fill_color(*rgb)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        w = self.get_string_width(text) + 6
        self.cell(w, 5, _safe(text), fill=True, ln=1, align="C")
        self.ln(1)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_cover(pdf: _SNCReportPDF, report: Dict[str, Any]) -> None:
    cover = report.get("cover") or {}
    pdf.add_page()
    pdf.ln(4)
    pdf.h1("Special Needs Co-Parenting")
    pdf.h1("Individual Parent Report")
    pdf.ln(2)
    lines = [
        ("Parent completing assessment", cover.get("parent_name") or "-"),
        ("Child",                        cover.get("child_name") or "-"),
        ("Child's age and grade",        cover.get("child_age_grade") or "-"),
        ("Assessment date",              cover.get("assessment_date") or "-"),
        ("Report type",                  cover.get("report_type") or "Individual Parent Report"),
        ("Assessment version",           cover.get("assessment_version") or "-"),
    ]
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 24, 54)
    for label, value in lines:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(label))
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(value))
        pdf.ln(0.5)

    pdf.ln(4)
    pdf.h2("Purpose of this report")
    pdf.body(report.get("purpose") or "")


def _render_at_a_glance(pdf: _SNCReportPDF, ag: Dict[str, Any]) -> None:
    pdf.add_page()
    pdf.h2("1. Report at a Glance")
    for label, items in [
        ("Child's identified strengths",   ag.get("child_strengths")),
        ("Child's primary needs",          ag.get("child_needs")),
        ("Parent's highest priorities",    ag.get("parent_priorities")),
        ("Areas of established strength",  ag.get("established_strengths")),
        ("Areas needing greater coordination", ag.get("coordination_areas")),
        ("Priority concerns",              ag.get("priority_concerns")),
        ("Professional questions requiring clarification", ag.get("professional_questions")),
    ]:
        pdf.h3(label)
        vals = list(items or [])
        if vals:
            pdf.bullets(vals)
        else:
            pdf.body("-")


def _render_category_summary(pdf: _SNCReportPDF, rows: List[Dict[str, Any]]) -> None:
    pdf.h2("2. Category Summary")
    for r in rows:
        clsn = r.get("classification") or "-"
        score = r.get("score")
        if score is None:
            score_txt = "-"
        elif isinstance(score, (int, float)):
            score_txt = f"{score:.2f}"
        else:
            score_txt = str(score)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 19, 48)
        pdf.multi_cell(pdf.epw, 5.5, _safe(r["category"]))
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9)
        rgb = _CLASSIFICATION_COLOR.get(clsn, (110, 110, 130))
        pdf.set_text_color(*rgb)
        pdf.multi_cell(pdf.epw, 5, _safe(f"Score: {score_txt}   ·   {clsn}"))
        pdf.set_text_color(30, 24, 54)
        finding = r.get("primary_finding") or ""
        if finding:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5, _safe(finding))
        pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4.5, _safe(
        "Scores reflect the reporting parent's answers and are not findings of fact."
    ))
    pdf.set_text_color(30, 24, 54)
    pdf.ln(1)


def _render_child_profile(pdf: _SNCReportPDF, cp: Dict[str, Any]) -> None:
    pdf.h2("3. Child Profile")
    for label, value in [
        ("Age and grade",       cp.get("age_grade")),
        ("Diagnosis status",    cp.get("diagnosis_status")),
    ]:
        pdf.h3(label)
        pdf.body(str(value or "-"))
    if cp.get("identified_needs"):
        pdf.h3("Identified areas of need")
        pdf.bullets(cp["identified_needs"])
    if cp.get("strengths"):
        pdf.h3("Strengths")
        pdf.body(str(cp["strengths"]))
    if cp.get("interests"):
        pdf.h3("Interests and sources of enjoyment")
        pdf.body(str(cp["interests"]))
    if cp.get("narrative"):
        pdf.h3("Parent's narrative")
        pdf.body(str(cp["narrative"]))
    if cp.get("summary"):
        pdf.h3("Report summary")
        pdf.body(cp["summary"])


def _render_five_part(pdf: _SNCReportPDF, number: int, title: str, block: Dict[str, Any]) -> None:
    pdf.h2(f"{number}. {title}")
    clsn = block.get("classification")
    score = block.get("score")
    if clsn:
        rgb = _CLASSIFICATION_COLOR.get(clsn, (110, 110, 130))
        score_txt = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
        pdf.pill(f"{clsn}  ·  Score {score_txt}", rgb)
    for label, key in [
        ("Finding",       "finding"),
        ("Child impact",  "child_impact"),
        ("Suggested option", "suggested"),
        ("First action step", "action_step"),
    ]:
        val = block.get(key)
        if val:
            pdf.h3(label)
            pdf.body(val)
    extras = block.get("extras") or {}
    if extras:
        pdf.h3("Additional detail from this parent")
        for k, v in extras.items():
            if not v:
                continue
            if isinstance(v, list):
                if not v:
                    continue
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(61, 26, 120)
                pdf.multi_cell(pdf.epw, 5, _safe(k.replace("_", " ").capitalize() + ":"))
                pdf.set_text_color(30, 24, 54)
                if k == "routine_grid":
                    for row in v:
                        pdf.set_font("Helvetica", "", 9)
                        pdf.cell(60, 5, _safe(row.get("routine", "")))
                        pdf.multi_cell(pdf.epw, 5, _safe(row.get("reported_consistency", "")))
                else:
                    pdf.bullets([str(x) for x in v])
            else:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(61, 26, 120)
                pdf.multi_cell(pdf.epw, 5, _safe(k.replace("_", " ").capitalize() + ":"))
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(30, 24, 54)
                pdf.multi_cell(pdf.epw, 5, _safe(str(v)))
                pdf.ln(0.5)


def _render_safety(pdf: _SNCReportPDF, safety: Dict[str, Any]) -> None:
    pdf.h2("12. Family Violence and Communication Safety")
    if safety.get("redacted"):
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(110, 100, 130)
        pdf.multi_cell(pdf.epw, 5.5, _safe(
            safety.get("note")
            or "Safety content is intentionally omitted from this shared / comparison view."
        ))
        pdf.set_text_color(30, 24, 54)
        return
    pdf.h3("Safety-screen result")
    pdf.body(safety.get("screen_result") or "-")
    if safety.get("selected_flags"):
        pdf.h3("Reported items")
        pdf.bullets(safety["selected_flags"])
    if safety.get("selected_safeguards"):
        pdf.h3("Selected safeguards")
        pdf.bullets(safety["selected_safeguards"])
    if safety.get("recommend_full_family_violence_assessment"):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(176, 42, 42)
        pdf.multi_cell(pdf.epw, 5.5, _safe(
            "Recommendation: complete the full Family Violence & Communication Safety Assessment."
        ))
        pdf.set_text_color(30, 24, 54)
    if safety.get("note"):
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(110, 100, 130)
        pdf.ln(1)
        pdf.multi_cell(pdf.epw, 4.5, _safe(safety["note"]))
        pdf.set_text_color(30, 24, 54)


def _render_action_plan(pdf: _SNCReportPDF, plan: List[Dict[str, str]], thirty: List[str]) -> None:
    pdf.h2("15. Recommended Child-Focused Action Plan")
    if not plan:
        pdf.body("No action items generated — complete more of the assessment to see priorities.")
    else:
        for row in plan:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 5.5, _safe(f"Priority {row.get('priority', '')}"))
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 24, 54)
            pdf.multi_cell(pdf.epw, 5, _safe(f"Action: {row.get('recommended_action', '')}"))
            pdf.multi_cell(pdf.epw, 5, _safe(f"Responsible: {row.get('responsible', '')}"))
            if row.get("professional"):
                pdf.multi_cell(pdf.epw, 5, _safe(f"Professional support: {row['professional']}"))
            if row.get("target_date"):
                pdf.multi_cell(pdf.epw, 5, _safe(f"Target: {row['target_date']}"))
            pdf.ln(1)
    if thirty:
        pdf.ln(1)
        pdf.h3("Recommended 30-day steps")
        pdf.bullets(thirty)


def _render_questions(pdf: _SNCReportPDF, qs: List[str]) -> None:
    pdf.h2("16. Questions for the Other Parent or a Professional")
    if not qs:
        pdf.body("-")
    else:
        pdf.bullets(qs)


def _render_closing(pdf: _SNCReportPDF, closing: Dict[str, Any]) -> None:
    pdf.h2("17. Closing Summary")
    pdf.body(closing.get("summary_paragraph") or "")
    pdf.ln(1)
    pdf.h3("Parent reflection")
    for label, key in [
        ("One thing I can do now",                    "one_thing_now"),
        ("One issue that requires cooperation",       "one_issue_needing_cooperation"),
        ("One question that requires professional guidance", "one_question_for_professional"),
    ]:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 5, _safe(label + ":"))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 24, 54)
        pdf.multi_cell(pdf.epw, 5, _safe(closing.get(key) or "-"))
        pdf.ln(0.5)


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def build_snc_pdf(*, report: Dict[str, Any]) -> bytes:
    """Render the Individual Parent Report to PDF bytes.

    Args:
        report: dict produced by `snc_report_content.build_individual_report()`.
                Safety redaction is controlled by that builder's
                `include_safety` flag and is respected here.
    """
    pdf = _SNCReportPDF()

    # Cover + purpose (page 1)
    _render_cover(pdf, report)

    # §1 & §2 (usually starts a new page)
    _render_at_a_glance(pdf, report.get("at_a_glance") or {})
    _render_category_summary(pdf, report.get("category_summary") or [])

    # §3
    _render_child_profile(pdf, report.get("child_profile") or {})

    # §4-§13 — 5-part blocks
    section_map = [
        (4,  "Understanding and Acceptance",             "understanding_acceptance"),
        (5,  "Medical and Mental Healthcare",            "medical_mental"),
        (6,  "Kindergarten and Elementary School",       "school"),
        (7,  "Transitions, Pickup, and Drop-Off",        "transitions"),
        (8,  "Daily Routines Across Homes",              "daily_routines"),
        (9,  "Communication and Information Sharing",    "communication"),
        (10, "School Events",                            None),                 # composite (10a/10b)
        (11, "Decision-Making and Professional Guidance","decision_making"),
    ]
    for number, title, key in section_map:
        if number == 10:
            events = (report.get("events_and_extracurricular") or {})
            _render_five_part(pdf, 10, "School Events",       events.get("school_events") or {})
            _render_five_part(pdf, 10, "Extracurricular Activities", events.get("extracurricular") or {})
            continue
        block = report.get(key) or {}
        _render_five_part(pdf, number, title, block)

    # §12 Safety (redacted or full)
    _render_safety(pdf, report.get("safety") or {})

    # §13 Parent capacity
    _render_five_part(pdf, 13, "Parent Capacity and Support", report.get("parent_capacity") or {})

    # §14 Goals, concerns, priorities
    goals = report.get("goals_concerns") or {}
    pdf.h2("14. Parent's Goals, Concerns, and Priorities")
    if goals.get("goals"):
        pdf.h3("Three primary goals")
        pdf.bullets(goals["goals"])
    if goals.get("concerns"):
        pdf.h3("Three primary concerns")
        pdf.bullets(goals["concerns"])
    for label, key in [
        ("What the child needs from this parent",                    "from_this_parent"),
        ("What the child needs from the other parent (this parent's perspective)", "from_other_parent"),
        ("What the child needs from both parents",                   "from_both_parents"),
        ("Which issue should be addressed first",                    "first_issue"),
        ("Professional information still needed",                    "info_needed"),
        ("30-day agreement worth trying",                            "thirty_day_agreement"),
    ]:
        v = goals.get(key)
        if v:
            pdf.h3(label)
            pdf.body(str(v))

    # §15 Action Plan + §16 Questions + §17 Closing
    _render_action_plan(pdf, report.get("action_plan") or [], report.get("thirty_day_steps") or [])
    _render_questions(pdf, report.get("questions_for_other_parent") or [])
    _render_closing(pdf, report.get("closing") or {})

    # Disclaimer
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4.5, _safe(report.get("disclaimer") or ""))

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
