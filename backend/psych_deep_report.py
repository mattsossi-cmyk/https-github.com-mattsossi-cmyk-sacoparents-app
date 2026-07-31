"""Psychological Deep Dive — report content + branded Letter-sized PDF."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import os as _os
from edu_deep_report import _PDF as _EduPDF, _section_break, _safe, LOGO_PATH as _LOGO
from psych_deep_questions import DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION
from psych_deep_scoring import score_deep_dive


class _PsychPDF(_EduPDF):
    def header(self):
        self.set_fill_color(245, 240, 232); self.rect(0, 0, self.w, 18, "F")
        if _os.path.exists(_LOGO):
            try: self.image(_LOGO, x=11, y=3, w=12, h=12)
            except Exception: pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe("SA CoParents  ·  Psychological Needs Deep Dive"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe("Relational Mediation Prep"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Psychological Deep Dive Report  ·  Page {self.page_no()} of {{nb}}"), align="C")


SECTION_TEMPLATES = {
    "s1": {
        "challenge": "Multiple active diagnoses signal that coordination between homes is essential.",
        "recommendations": [
            "Keep a shared, up-to-date list of diagnoses, providers, and current treatments in both homes.",
            "Review the list together at the start of each school year and after any provider change.",
        ],
    },
    "s2": {
        "strength": "Both parents consistently coordinate around the child's provider.",
        "challenge": "Provider coordination is inconsistent — one parent may be missing updates or appointments.",
        "recommendations": [
            "Ask the provider to release information to both parents in writing.",
            "Agree on a monthly written update between parents about attendance and progress.",
            "Alternate attendance at appointments so both parents hear from the provider directly.",
        ],
    },
    "s3": {
        "strength": "Both parents express confidence in the current provider.",
        "challenge": "One or both parents lack confidence in the provider or treatment plan.",
        "recommendations": [
            "Schedule a joint consultation with the provider to voice concerns.",
            "Ask the provider for the evidence base supporting the current plan.",
            "Consider a neutral second opinion before changing providers.",
        ],
    },
    "s4": {
        "challenge": "Medication is not being managed consistently between homes.",
        "recommendations": [
            "Use a shared medication log (paper or app) in both homes.",
            "Keep a spare labelled dose at each home for handoff days.",
            "Agree in writing on who reports side effects and refill needs to the prescriber.",
        ],
    },
    "s5": {
        "strength": "Non-medication interventions are supported in both homes.",
        "challenge": "Non-medication interventions are inconsistently supported or implemented.",
        "recommendations": [
            "Choose two priority interventions and agree on how they will run in both homes.",
            "Schedule a joint review every 8 weeks to decide whether to continue each one.",
        ],
    },
    "s6": {
        "strength": "Therapy participation and follow-through are strong.",
        "challenge": "Therapy attendance or homework is inconsistent between homes.",
        "recommendations": [
            "Confirm who transports the child on each therapy day two weeks ahead.",
            "Send a short weekly note between homes summarising the last session's homework.",
            "Ask the therapist to send session goals to both parents.",
        ],
    },
    "s7": {
        "strength": "Parenting strategies are consistent across most behavioural and emotional areas.",
        "challenge": "Parenting strategies differ across several behavioural or emotional areas.",
        "recommendations": [
            "Write a one-page shared plan for the two areas that differ most.",
            "Focus first on transitions, meltdowns, and anger — where inconsistency has the biggest impact.",
        ],
    },
    "s8": {
        "strength": "A written crisis plan covers most critical areas.",
        "challenge": "Crisis planning is incomplete — some areas or emergency contacts are not shared.",
        "recommendations": [
            "Post a one-page crisis plan in both homes with emergency numbers and steps.",
            "Confirm both parents know the local 24/7 crisis line and pathway.",
            "Ask the therapist or paediatrician to help write a signed crisis protocol.",
        ],
    },
    "s9": {
        "strength": "Parents talk about most treatment topics regularly.",
        "challenge": "Communication between parents on treatment topics is inconsistent.",
        "recommendations": [
            "Agree on one written weekly check-in that covers appointments, symptoms, and school concerns.",
            "Use a shared parenting app to move logistics out of face-to-face conversations.",
        ],
    },
    "s10": {
        "strength": "Parents consistently agree on major psychological decisions.",
        "challenge": "Several major psychological decisions rarely see agreement.",
        "recommendations": [
            "Bring stuck decisions to a family therapist or mediator specialising in mental-health disputes.",
            "Agree in writing on how tie-breaking decisions will be made.",
        ],
    },
    "s11": {
        "strength": "Both homes provide a consistent emotional foundation for the child.",
        "challenge": "Home support is inconsistent across critical foundational areas.",
        "recommendations": [
            "Focus first on routines and calm environment — the two foundations that stabilise everything else.",
            "Compare bedtime, wake, and homework routines between homes and align 2-3 anchor points.",
        ],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_deep_dive_report(*, parent_name: Optional[str], child_name: Optional[str],
                           responses: Dict[str, Any]) -> Dict[str, Any]:
    scored = score_deep_dive(responses)
    sections_out = []
    for st in scored["sections"]:
        if not st["is_visible"] or not st["answered"]:
            continue
        entry = {k: st[k] for k in ("id", "name", "number", "is_flagged",
                                    "flag_reasons", "is_strength", "strength_reasons")}
        tpl = SECTION_TEMPLATES.get(st["id"], {})
        if st["is_strength"] and tpl.get("strength"):
            entry["strength_text"] = tpl["strength"]
        if st["is_flagged"] and tpl.get("challenge"):
            entry["challenge_text"] = tpl["challenge"]
            entry["recommendations"] = tpl.get("recommendations") or []
        sections_out.append(entry)

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
            "diagnoses": responses.get("s1_diagnoses") or [],
            "provider_types": responses.get("s2_provider_types") or [],
            "has_medication": responses.get("s4_has_medication"),
            "attends_therapy": responses.get("s6_attends_therapy"),
            "notes": (responses.get("s1_profile_notes") or "").strip(),
        },
        "summary": {
            "answered_sections": scored["totals"]["answered"],
            "flagged_sections": scored["totals"]["flagged"],
            "strength_sections": scored["totals"]["strengths"],
            "flagged_names": flagged_names,
            "strength_names": strength_names,
        },
        "sections": sections_out,
        "disclaimer": (
            "This report reflects one parent's perspective. It does not diagnose, "
            "provide clinical advice, or replace a mental health professional. "
            "Share it with your provider, mediator, or family professional for their input."
        ),
    }


def build_deep_dive_pdf(*, report: Dict[str, Any]) -> bytes:
    pdf = _PsychPDF()
    pdf.add_page()
    cover = report.get("cover") or {}
    profile = report.get("profile") or {}
    summary = report.get("summary") or {}

    pdf.h1("Psychological / Behavioural Needs — Deep Dive Report")
    pdf.body(f"For {cover.get('parent_name') or '-'} · About {cover.get('child_name') or '-'} · {cover.get('assessment_date') or ''}")
    pdf.small(report.get("disclaimer") or "")

    _section_break(pdf)
    pdf.h2("1. Psychological Profile")
    if profile.get("diagnoses"):
        pdf.h3("Reported diagnoses")
        pdf.bullets(profile["diagnoses"])
    if profile.get("provider_types"):
        pdf.h3("Current providers")
        pdf.bullets(profile["provider_types"])
    misc = []
    if profile.get("has_medication"): misc.append(f"Medication: {profile['has_medication']}")
    if profile.get("attends_therapy"): misc.append(f"Attends therapy: {profile['attends_therapy']}")
    if misc: pdf.body(" · ".join(misc))
    if profile.get("notes"):
        pdf.h3("Additional notes")
        pdf.body(profile["notes"])

    _section_break(pdf)
    if report.get("ai_summary"):
        pdf.h2("Executive summary")
        pdf.small("AI-generated · neutral · non-diagnostic")
        pdf.body(report["ai_summary"])
        _section_break(pdf)
    pdf.h2("At a glance")
    pdf.body(
        f"{summary.get('answered_sections', 0)} sections completed. "
        f"{summary.get('flagged_sections', 0)} area(s) flagged. "
        f"{summary.get('strength_sections', 0)} area(s) recognised as strengths."
    )
    if summary.get("flagged_names"):
        pdf.h3("Sections flagged for follow-up")
        pdf.bullets(summary["flagged_names"])
    if summary.get("strength_names"):
        pdf.h3("Areas of current strength")
        pdf.bullets(summary["strength_names"])

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

    _section_break(pdf)
    pdf.small(report.get("disclaimer") or "")
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
