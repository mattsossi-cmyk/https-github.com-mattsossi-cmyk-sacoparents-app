"""Regenerate the Special Needs dynamic sample PDF using the current renderer."""
import sys, os
sys.path.insert(0, "/app/backend")

from sn_v3_questions import SECTIONS
from sn_v3_scoring import compute_scores
from sn_v3_report_content import build_report
from sn_v3_report_pdf import build_special_needs_pdf

# Curated answer profile: mixed strengths + priorities across the 9 sections.
# Section 6 (Communication) is intentionally kept Fair/Needs Improvement so the
# communication toolkit surfaces.
PROFILE_BY_SECTION = {
    "d1": 3,   # Understanding — Good
    "d2": 3,   # Educational — Good
    "d3": 2,   # Healthcare — Fair
    "d4": 3,   # Daily-Care — Good
    "d5": 2,   # Transitions — Fair
    "d6": 1,   # Communication — Needs Improvement → toolkit
    "d7": 3,   # Decisions — Good
    "d8": 4,   # Events — Excellent
    "d9": 2,   # Resources — Fair
}

INTAKE = {
    "child_age": 8,
    "child_grade": "3rd grade / general-ed with pull-out support",
    "school_setting": "Public elementary",
    "diagnoses": "ADHD, Sensory Processing Disorder",
    "suspected": "-",
    "primary_needs": "Emotional regulation, executive function, sensory calm-down routines",
    "communication_ability": "Verbal, sometimes shuts down under stress",
    "professionals": "Paediatrician, OT, school counsellor",
    "supports": "Non-stimulant ADHD med, weekly OT, sensory kit at school",
    "cultural_notes": "Bilingual English/Spanish household",
    "parenting_schedule": "Alternating weeks; Wed dinner mid-week",
    "other_children": "None",
    "distance": "12 minutes between homes; both near school",
    "decision_making": "Joint (per court order)",
    "court_orders": "Consent decree signed 2023",
    "comm_method": "Text + parenting app for major updates",
    "child_shared": "Prefers to know the schedule a day ahead. Struggles with sudden changes.",
    "child_secure": "Weighted blanket, predictable bedtime, quiet room after school.",
    "child_preferred_comm": "Face-to-face at bedtime; not phone calls.",
    "child_strengths": "Curious, funny, loves dinosaurs and drawing.",
}


def main():
    answers = {}
    for sec in SECTIONS:
        v = PROFILE_BY_SECTION.get(sec["id"], 3)
        for q in sec["questions"]:
            answers[q["id"]] = v

    scores = compute_scores(answers)
    report = build_report(
        scores=scores,
        answers=answers,
        intake=INTAKE,
        parent_name="Alex Sample",
    )
    pdf_bytes = build_special_needs_pdf(user_name="Alex Sample", report=report)

    out_dir = "/app/frontend/public/downloads"
    os.makedirs(out_dir, exist_ok=True)
    for filename in (
        "sacoparents-special-needs-dynamic-sample.pdf",
        "sacoparents-special-needs-report.pdf",
    ):
        with open(os.path.join(out_dir, filename), "wb") as f:
            f.write(pdf_bytes)
        print(f"Wrote {filename} ({len(pdf_bytes)} bytes) — overall={report['overall_rating']}")


if __name__ == "__main__":
    main()
