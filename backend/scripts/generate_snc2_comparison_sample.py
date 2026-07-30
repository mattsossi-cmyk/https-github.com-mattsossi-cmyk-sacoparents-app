"""One-shot helper that generates a realistic Co-Parent Comparison sample PDF.

Two synthetic parents (Alex Rivera & Jordan Rivera) both selected the
medical + educational + psychological pathways so the sample showcases the
category filter. Some answers align, some diverge, and step 6/7/8 are
answered so the "5 things you already agree on" highlights section is
populated.

Writes to /app/frontend/public/downloads/snc-sample-comparison-report.pdf so
the file is publicly downloadable at /downloads/snc-sample-comparison-report.pdf.
"""
from __future__ import annotations

import os
import sys

# Make sibling backend modules importable when this script is run standalone.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snc2_comparison import build_comparison
from snc2_comparison_pdf import build_comparison_pdf
from snc2_questions import qid


PATHWAYS = ["medical", "educational", "psychological"]


def _base_alex(pathway: str) -> dict:
    ans = {
        qid("step1", pathway, "current_impact"): 4,
        qid("step1", pathway, "duration"): "1 to 3 years",
        qid("step1", pathway, "urgency"): "Ongoing / stable",
        qid("step3", pathway, "recs_written"): "Yes",
        qid("step3", pathway, "recs_understand"): 5,
        qid("step4", pathway, "same_info"): 4,
        qid("step4", pathway, "attend_appts"): 3,
        qid("step4", pathway, "discuss_openly"): 4,
        qid("step4", pathway, "shared_language"): 3,
        qid("step4", pathway, "believe_understood"): 4,
        qid("step5", pathway, "routines_consistent"): 4,
        qid("step5", pathway, "follow_recs"): 5,
        qid("step5", pathway, "share_updates"): 3,
        qid("step5", pathway, "carry_over_supplies"): 4,
        qid("step5", pathway, "handoffs_reliable"): 4,
        qid("step6", pathway, "biggest_gap"): "Communication style",
        qid("step7", pathway, "practical_other"): "",
        qid("step8", pathway, "next_meeting"): "Within 2 weeks",
        qid("step8", pathway, "concerns_about_plan"): "",
    }
    return ans


def _base_jordan(pathway: str) -> dict:
    ans = {
        qid("step1", pathway, "current_impact"): 3,
        qid("step1", pathway, "duration"): "1 to 3 years",
        qid("step1", pathway, "urgency"): "Ongoing / stable",
        qid("step3", pathway, "recs_written"): "Yes",
        qid("step3", pathway, "recs_understand"): 5,
        qid("step4", pathway, "same_info"): 3,
        qid("step4", pathway, "attend_appts"): 5,
        qid("step4", pathway, "discuss_openly"): 4,
        qid("step4", pathway, "shared_language"): 3,
        qid("step4", pathway, "believe_understood"): 4,
        qid("step5", pathway, "routines_consistent"): 5,
        qid("step5", pathway, "follow_recs"): 5,
        qid("step5", pathway, "share_updates"): 3,
        qid("step5", pathway, "carry_over_supplies"): 4,
        qid("step5", pathway, "handoffs_reliable"): 3,
        qid("step6", pathway, "biggest_gap"): "Different priorities",
        qid("step7", pathway, "practical_other"): "",
        qid("step8", pathway, "next_meeting"): "Within a month",
        qid("step8", pathway, "concerns_about_plan"): "",
    }
    return ans


def _pathway_specifics(pathway: str, parent: str) -> dict:
    """Fill in the pathway-specific text/multi answers."""
    is_alex = parent == "alex"
    if pathway == "medical":
        return {
            qid("step1", pathway, "concern"):
                ("Ari lives with moderate persistent asthma. Uses a daily "
                 "controller inhaler and needs a rescue inhaler on hand.")
                if is_alex else
                ("Ari's asthma is manageable but we have missed a few doses "
                 "during transitions between homes."),
            qid("step2", pathway, "current_needs"):
                (["Chronic medical condition", "Medication schedule",
                  "Regular specialist appointments"]
                 if is_alex else
                 ["Chronic medical condition", "Medication schedule",
                  "Allergies or dietary restrictions"]),
            qid("step2", pathway, "other_needs"):
                ("Air purifier needed at both homes." if is_alex else ""),
            qid("step3", pathway, "professionals_seen"):
                (["Paediatrician", "Specialist doctor"]
                 if is_alex else ["Paediatrician"]),
            qid("step3", pathway, "recommendations_text"):
                ("Two puffs of controller inhaler morning and night, "
                 "rescue inhaler as needed.")
                if is_alex else
                ("Follow the paediatric plan. Track any night-time symptoms."),
            qid("step6", pathway, "agree_areas"):
                "We both agree Ari's daily controller inhaler is non-negotiable."
                if is_alex else
                "Both of us take asthma seriously and follow the paediatrician's plan.",
            qid("step6", pathway, "disagree_areas"):
                "How to handle sleepovers at friends' houses."
                if is_alex else
                "Whether Ari can do overnight sports camps.",
            qid("step7", pathway, "practical_selected"):
                (["Shared calendar for medical appointments",
                  "Medication cross-check at each handoff"]
                 if is_alex else
                 ["Shared calendar for medical appointments",
                  "Written medication list travels with the child"]),
            qid("step8", pathway, "top_priority"):
                "Refill spacer prescription this week."
                if is_alex else
                "Book the annual asthma review together.",
            qid("step8", pathway, "professional_next"):
                "Meet with pulmonologist to update the action plan."
                if is_alex else
                "Confirm with paediatrician that both homes have the correct dose.",
        }
    if pathway == "educational":
        return {
            qid("step1", pathway, "concern"):
                "Ari has an IEP for dyslexia and reads at a lower level than peers."
                if is_alex else
                "Ari is working hard but struggles with reading and homework at home.",
            qid("step2", pathway, "current_needs"):
                (["Special education services (IEP or 504)",
                  "Learning differences",
                  "Homework and study support"]
                 if is_alex else
                 ["Special education services (IEP or 504)",
                  "Homework and study support"]),
            qid("step2", pathway, "other_needs"): "",
            qid("step3", pathway, "professionals_seen"):
                (["Special education teacher", "Reading specialist / tutor"]
                 if is_alex else
                 ["Special education teacher"]),
            qid("step3", pathway, "recommendations_text"):
                "20 minutes of guided reading practice on school nights."
                if is_alex else
                "Consistent homework routine and daily reading time.",
            qid("step6", pathway, "agree_areas"):
                "Both parents attend IEP meetings."
                if is_alex else
                "Both parents value school attendance and support the IEP.",
            qid("step6", pathway, "disagree_areas"):
                "Screen time as a reading reward."
                if is_alex else
                "Whether Ari should be pushed to attend tutoring during summers.",
            qid("step7", pathway, "practical_selected"):
                (["Shared IEP folder or document",
                  "Consistent homework routine across homes"]
                 if is_alex else
                 ["Consistent homework routine across homes"]),
            qid("step8", pathway, "top_priority"):
                "Send the school our shared contact list."
                if is_alex else
                "Set a consistent reading window on school nights.",
            qid("step8", pathway, "professional_next"):
                "Request an IEP progress meeting mid-term."
                if is_alex else
                "Meet with the reading specialist together.",
        }
    # psychological
    return {
        qid("step1", pathway, "concern"):
            "Ari has been experiencing anxiety around transitions and social situations."
            if is_alex else
            "I've noticed Ari is more withdrawn than usual after busy weeks.",
        qid("step2", pathway, "current_needs"):
            (["Diagnosed condition (e.g., anxiety, ADHD, depression)",
              "Emotional regulation support",
              "Ongoing therapy or counseling"]
             if is_alex else
             ["Emotional regulation support",
              "Ongoing therapy or counseling"]),
        qid("step2", pathway, "other_needs"):
            "Additional support during school transitions.",
        qid("step3", pathway, "professionals_seen"):
            (["Child psychologist / therapist", "Paediatrician"]
             if is_alex else
             ["Child psychologist / therapist"]),
        qid("step3", pathway, "recommendations_text"):
            "Weekly therapy plus consistent bedtime routines across both homes."
            if is_alex else
            "Weekly therapy sessions and reduced screen time before bed.",
        qid("step6", pathway, "agree_areas"):
            "We both believe therapy is important."
            if is_alex else
            "We both agree Ari needs consistent emotional support.",
        qid("step6", pathway, "disagree_areas"):
            "How much to talk about therapy content with each other."
            if is_alex else
            "Whether Ari's therapist should join a joint parent meeting.",
        qid("step7", pathway, "practical_selected"):
            (["Consistent bedtime and morning routines",
              "Shared communication plan around therapy days"]
             if is_alex else
             ["Consistent bedtime and morning routines"]),
        qid("step8", pathway, "top_priority"):
            "Confirm this month's therapy schedule with Ari."
            if is_alex else
            "Establish a shared quiet-hour routine at both homes.",
        qid("step8", pathway, "professional_next"):
            "Schedule a joint parent meeting with the therapist."
            if is_alex else
            "Send the therapist an update on how Ari's doing.",
    }


def _all_answers(parent: str) -> dict:
    out: dict = {}
    for p in PATHWAYS:
        out.update(_base_alex(p) if parent == "alex" else _base_jordan(p))
        out.update(_pathway_specifics(p, parent))
    return out


def main() -> None:
    alex = _all_answers("alex")
    jordan = _all_answers("jordan")
    comparison = build_comparison(
        parent_a_name="Alex Rivera",
        parent_b_name="Jordan Rivera",
        a_pathways=PATHWAYS,
        b_pathways=PATHWAYS,
        a_answers=alex,
        b_answers=jordan,
    )
    pdf_bytes = build_comparison_pdf(
        comparison=comparison,
        safety_notice=(
            "Safety notice: this is a synthetic sample. If either parent's "
            "circumstances change, revisit the Family Violence & Communication "
            "Safety Assessment before continuing to share detailed information."
        ),
    )
    # scripts/ is under /app/backend, real public downloads is /app/frontend/public/downloads
    out_dir = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "frontend", "public", "downloads",
    ))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "snc-sample-comparison-report.pdf")
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"Wrote {len(pdf_bytes)} bytes to {out_path}")
    print(f"Highlights included: {len(comparison.get('highlights') or [])}")


if __name__ == "__main__":
    main()
