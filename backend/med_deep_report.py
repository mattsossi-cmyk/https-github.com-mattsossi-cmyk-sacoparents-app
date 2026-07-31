"""Medical / Prescription Deep Dive — report content + branded Letter-sized PDF."""
from __future__ import annotations

import os as _os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from edu_deep_report import _PDF as _EduPDF, _section_break, _safe, LOGO_PATH as _LOGO
from journey_pdf import build_journey_pdf
from med_deep_journey import build_journey_report as build_med_journey
from med_deep_questions import DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION
from med_deep_scoring import score_deep_dive


class _MedPDF(_EduPDF):
    def header(self):
        self.set_fill_color(245, 240, 232); self.rect(0, 0, self.w, 18, "F")
        if _os.path.exists(_LOGO):
            try:
                self.image(_LOGO, x=11, y=3, w=12, h=12)
            except Exception:
                pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe("SA CoParents  ·  Prescription & Medication Coordination Deep Dive"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe("Medical Needs · Relational Mediation Prep"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Prescription & Medication Coordination Deep Dive  ·  Page {self.page_no()} of {{nb}}"), align="C")


SECTION_TEMPLATES = {
    "s1": {
        "strength": "Both parents share an accurate, current picture of every prescription.",
        "challenge": "Both parents do not consistently share the same accurate prescription details.",
        "recommendations": [
            "Create a one-page shared medication list (name, dose, purpose, schedule, prescriber, pharmacy) and store copies in both homes.",
            "Update the list within 24 hours of any dose or prescription change.",
            "Ask each prescriber to release records / portal access to both parents in writing.",
        ],
    },
    "s2": {
        "strength": "Pick-ups are clearly assigned and confirmed between parents.",
        "challenge": "Prescription pick-ups cause friction, delays, or missed doses.",
        "recommendations": [
            "Decide in writing who picks up each recurring prescription and who is the backup.",
            "Send a short pick-up confirmation to the other parent on the day it is filled.",
            "Enable pharmacy auto-refill or delivery to reduce human error.",
        ],
    },
    "s3": {
        "strength": "The child has continuous, reliable supply — including rescue medication — in both homes.",
        "challenge": "Supply between homes is inconsistent, and the child has risked running out.",
        "recommendations": [
            "Keep a labelled backup supply of daily medication in each home.",
            "Confirm rescue / emergency medication (inhaler, EpiPen, glucagon) is present, unexpired, and accessible in BOTH homes.",
            "Set a shared calendar reminder five days before every refill is due.",
            "Check expiration dates on the first of each month.",
        ],
    },
    "s4": {
        "strength": "Administration is consistent between homes with logging and handoff communication.",
        "challenge": "Administration is inconsistent — missed doses or unclear handoffs are affecting the child.",
        "recommendations": [
            "Use the same daily administration schedule in both homes; when handoff timing conflicts, choose one plan and follow it.",
            "Log every dose in a shared paper log or app so the other home can see the last dose given.",
            "At handoff, state out loud (or in writing): last dose given at [time], next dose due at [time].",
        ],
    },
    "s5": {
        "strength": "Parents talk about most medication topics regularly.",
        "challenge": "Medication communication between parents is inconsistent.",
        "recommendations": [
            "Send a short written note within 24 hours of any missed dose, side effect, or rescue use.",
            "Add a weekly written check-in that covers prescriptions, refills, and any appointments.",
            "Use a shared parenting app for medication messages so history is preserved.",
        ],
    },
    "s6": {
        "strength": "Pharmacy coordination is unified between homes.",
        "challenge": "Pharmacy coordination is fragmented — different pharmacies, missing authorisations, or unclear contacts.",
        "recommendations": [
            "Use one primary pharmacy for the child so refill history is unified.",
            "Add both parents to the pharmacy's authorised pick-up and contact list.",
            "Ask the pharmacist to counsel both parents at every new prescription.",
        ],
    },
    "s7": {
        "strength": "No current financial barriers and the cost split is documented.",
        "challenge": "Financial or insurance issues could interrupt medication.",
        "recommendations": [
            "Document the medication cost-split in the parenting plan or a signed side letter.",
            "Verify insurance formulary coverage before any new prescription.",
            "Ask the prescriber about therapeutic generics or manufacturer discount programs.",
            "For prior authorisations, agree in writing which parent submits and follows up.",
        ],
    },
    "s8": {
        "strength": "Controlled medication has multiple safeguards and tracked handoffs.",
        "challenge": "Controlled-medication accountability needs strengthening.",
        "recommendations": [
            "Store controlled medication in a locked location in both homes.",
            "Track pill / dose count in writing at every handoff and sign it.",
            "Ask the prescriber for a controlled-substance agreement signed by both parents.",
            "Only the parent should administer doses; the child should never have access to the bottle.",
        ],
    },
    "s9": {
        "strength": "School medication is well documented and both parents are informed.",
        "challenge": "School medication process has gaps that could delay a dose.",
        "recommendations": [
            "Ensure both parents are named on the school medication authorisation and emergency plan.",
            "Ask the school nurse to send the Medication Administration Record (MAR) to both parents each month.",
            "Pre-authorise field-trip and off-campus medication once per school year.",
            "Notify the school within 24 hours of any dose change.",
        ],
    },
    "s10": {
        "strength": "Most medication decisions consistently see agreement.",
        "challenge": "Several medication decisions rarely reach agreement.",
        "recommendations": [
            "For stuck decisions, request a joint appointment with the prescriber so both parents hear the same information.",
            "Agree in writing on a tie-breaking pathway (e.g., prescriber recommendation, mediator, or parenting coordinator).",
            "For rescue / emergency medication use, agree that either parent can act without prior discussion when the child is at risk.",
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
                                    "flag_reasons", "is_strength", "strength_reasons",
                                    "risk_signals")}
        tpl = SECTION_TEMPLATES.get(st["id"], {})
        if st["is_strength"] and tpl.get("strength"):
            entry["strength_text"] = tpl["strength"]
        if st["is_flagged"] and tpl.get("challenge"):
            entry["challenge_text"] = tpl["challenge"]
            entry["recommendations"] = tpl.get("recommendations") or []
        sections_out.append(entry)

    flagged_names = [s["name"] for s in sections_out if s["is_flagged"]]
    strength_names = [s["name"] for s in sections_out if s["is_strength"]]
    risk_signals_all = []
    for s in sections_out:
        for sig in s.get("risk_signals") or []:
            risk_signals_all.append(f"{s['name']}: {sig}")

    return {
        "generated_at": _now_iso(),
        "deep_dive_version": DEEP_DIVE_VERSION,
        "cover": {
            **build_med_journey(parent_name=parent_name, child_name=child_name, responses=responses)["cover"],
            "assessment_date": _now_iso()[:10],
        },
        "profile": {
            "med_categories": responses.get("s1_med_categories") or [],
            "prescriber_types": responses.get("s1_prescriber_types") or [],
            "has_controlled": responses.get("s8_has_controlled"),
            "school_meds": responses.get("s9_school_meds"),
            "notes": (responses.get("s1_notes") or "").strip(),
        },
        "summary": {
            "answered_sections": scored["totals"]["answered"],
            "flagged_sections": scored["totals"]["flagged"],
            "strength_sections": scored["totals"]["strengths"],
            "risk_sections": scored["totals"]["risk_sections"],
            "flagged_names": flagged_names,
            "strength_names": strength_names,
            "risk_signals": risk_signals_all,
        },
        "sections": sections_out,
        **{k: v for k, v in build_med_journey(
            parent_name=parent_name, child_name=child_name, responses=responses
        ).items() if k in (
            "overview", "support_summary", "child_profile", "school_involvement",
            "co_parenting_assessment", "alignment_areas", "attention_areas",
            "support_level", "practical_options", "action_plan",
            "foundation_statement", "questions_for_school_or_parent",
            "final_summary", "disclaimer",
        )},
    }


def build_deep_dive_pdf(*, report: Dict[str, Any]) -> bytes:
    return build_journey_pdf(
        product_name="Medical · Prescription & Medication Deep Dive",
        footer_name="Medical Deep Dive Report",
        headline="SA CoParents Medical & Prescription Coordination Report",
        report=report,
    )
