"""Fictional, fully filled-in Legal Lens Review and Report to Court — public sample (no real data)."""
from legal_lens import (CONFLICT_OPTIONS, INDIVIDUAL_RESOURCES, JOINT_OPTIONS, JOINT_RESOURCES, RATING_NOTE, RECEIPT, SAFETY_NOTE, STATUSES, TAGLINE,
                        classify_individual, classify_joint)
from sample_professional_report import SAMPLE_COURT, SAMPLE_PRO

_REPORT = {
    "id": "sample-legal-lens", "case_id": "sample-case", "status": "final", "professional_name": SAMPLE_PRO["name"], "professional_role": SAMPLE_PRO["pro_role"],
    "created_at": "2026-05-04T14:00:00+00:00", "updated_at": "2026-05-29T16:10:00+00:00", "finalized_at": "2026-05-29T16:10:00+00:00", "report_date": "2026-05-29",
    "matter_name": "Co-parenting — Education & School Decisions — M. Carter (age 9)", "court_county": SAMPLE_COURT["court_name"], "cause_number": SAMPLE_COURT["cause_number"],
    "parent_a_name": "Alex Carter", "parent_b_name": "Jamie Carter",
    "fv_a_received": "Received", "fv_b_received": "Received", "joint_process_appropriate": "Yes, with safeguards",
    "safety_notes": "Both individual family violence screenings were received and reviewed. Neither screening disclosed physical violence or protective-order history. Parent B reported "
                    "feeling pressured during in-person exchanges. Safeguard applied: all joint sessions are conducted with the professional present and exchanges of information "
                    "occur in writing through a structured app. No allegation is treated as a verified finding; this section documents receipt and the resulting process safeguards only.",
    "parent_a_rating": 6, "parent_a_strengths": "Responds to school-related messages within 24 hours; attends parent-teacher conferences; keeps homework routine consistent in own household; "
                    "uses child-focused language in written messages.",
    "parent_a_gaps": "Difficulty accepting last-minute schedule changes; occasionally copies extended family on co-parenting messages; expressed frustration when tutoring decisions were made without consultation.",
    "parent_a_notes": "Parent A self-reported a strong preference for written communication and predictable routines. Engagement in the assessment was complete and timely. "
                      "(PARENT-REPORTED INFORMATION summarized by the professional; not a credibility finding.)",
    "parent_a_resources": ["BIFF Communication Method", "SA CoParents AI Conversation Builder", "Kassandra Levay — Education Specialist"],
    "parent_a_provider": {"name": "Kassandra Levay", "specialty": "Education Specialist — IEP / 504 navigation", "contact": "(fictional) education@example.org"},
    "parent_b_rating": 4, "parent_b_strengths": "Attends all scheduled exchanges; strong involvement in extracurricular activities; shares medical appointment outcomes the same day; "
                    "child reports enjoying weekend routines.",
    "parent_b_gaps": "Delayed responses to school-decision messages (often 4–7 days); reactive tone when disagreeing about tutoring costs; has cancelled two joint meetings with less than 24 hours' notice.",
    "parent_b_notes": "Parent B self-reported that lengthy messages feel overwhelming and that shorter, single-topic messages are easier to answer. Parent B completed the assessment after one reminder. "
                      "(PARENT-REPORTED INFORMATION summarized by the professional; not a credibility finding.)",
    "parent_b_resources": ["Foundation Statement", "BIFF Communication Method", "Individual Counseling / Coaching"],
    "parent_b_provider": {"name": "Riverwalk Counseling Group (fictional)", "specialty": "Individual co-parenting coaching", "contact": "(fictional) intake@example.org"},
    "joint_rating": 5, "joint_strengths": "Both parents agree the child should remain at the current elementary school through fifth grade; both attend school events; "
                     "both accept the existing possession schedule; written exchanges about health matters are consistently task-focused.",
    "joint_gaps": "Disagreement about private tutoring (need and cost split); inconsistent homework expectations between households; schedule-change requests trigger reactive replies; "
                  "no shared calendar in use.",
    "joint_notes": "The parents function at a business-like level on routine matters and become reactive on cost-related decisions. Both stated a willingness to try structured, "
                   "single-topic communication. The joint assessment does not evaluate either parent's fitness and makes no custody recommendation.",
    "joint_resources": ["Brad Craig — Children in the Middle", "Kassandra Levay — Education Specialist", "Co-Parenting Agreement", "Child-Centered Mediation"],
    "joint_provider": {"name": "Brad Craig", "specialty": "Children in the Middle — co-parent education", "contact": "(fictional) citm@example.org"},
    "alignment_agreements": "Child remains enrolled at current school through fifth grade.\nBoth parents attend parent-teacher conferences (may attend separately).\n"
                            "Medical and school information is shared in writing within 24 hours.\nExisting possession schedule remains unchanged.",
    "alignment_disagreements": "Whether private tutoring is needed at this time.\nHow tutoring or enrichment costs should be divided.\nHomework expectations and screen-time rules across households.",
    "partial_alignment": "Extracurricular activities: both support one activity per season; disagreement is limited to weekday practice logistics.\n"
                         "Communication method: both agree to written communication; disagreement is about response timelines.",
    "alignment_summary": "The parents share the same core educational goal for the child and differ mainly on cost-sharing and household consistency. These differences are specific, "
                         "bounded, and appear suited to structured, child-centered problem-solving rather than continued litigation. This summary reflects the professional's review of the "
                         "Joint Report and is not a determination of which parent's position is correct.",
    "conflict_management_options": ["Child-Centered Mediation", "Parent Facilitation"],
    "conflict_management_rationale": "A joint rating of 5 (Business-Like / Functional) supports child-centered mediation for the two open decisions (tutoring and cost split), with parent "
                                     "facilitation available if written communication becomes reactive. Both parents agreed to single-topic messages and a 48-hour response window as an "
                                     "interim structure. Safety screening did not indicate the need to restrict joint sessions beyond professional presence.",
    "short_term_goals": "Adopt a shared calendar app for school and activity dates (by day 30).\nBoth parents complete Children in the Middle (by day 60).\n"
                        "Attend two child-centered mediation sessions on tutoring and cost allocation (by day 90).\nUse BIFF-style single-topic messages with 48-hour responses.",
    "long_term_goals": "Written co-parenting agreement covering education decisions and cost-sharing method (6 months).\nHousehold homework and screen-time expectations aligned "
                       "to a written framework (6–9 months).\nReassess joint rating with a target of consistent Business-Like / Functional or better (12 months).",
    "professional_summary": "This report documents the professional's review of two completed individual assessments, two family violence screenings, and the parents' Joint "
                            "Alignment Report in a co-parenting matter concerning education decisions for a nine-year-old child. Individual co-parenting ability was rated 6 "
                            "(Parent A) and 4 (Parent B); joint co-parenting ability was rated 5 (Business-Like / Functional, Emerging Cooperative). The parents are aligned on "
                            "school placement, conference attendance, information sharing, and the possession schedule, and are not aligned on tutoring need and cost division. "
                            "The professional recommends child-centered mediation for the open decisions with parent facilitation as a support structure, and a 90-day roadmap "
                            "followed by a reassessment. This report contains no custody recommendation, no credibility determination, no diagnosis, and no legal conclusion.",
    "next_review_date": "2026-08-28", "signature_name": SAMPLE_PRO["name"], "professional_title": "Licensed Professional Counselor · Parenting Facilitator",
}


def sample_legal_lens() -> dict:
    rep = dict(_REPORT)
    return {"is_sample": True, "title": "Sample Legal Lens Review and Report to Court — fictional data", "report": rep,
            "readiness": [{"key": "assessment_a", "label": "Parent A Assessment Received", "done": True}, {"key": "assessment_b", "label": "Parent B Assessment Received", "done": True},
                          {"key": "joint", "label": "Joint Report Received", "done": True}, {"key": "fv_a", "label": "Parent A Family Violence Assessment Received", "done": True, "na": False},
                          {"key": "fv_b", "label": "Parent B Family Violence Assessment Received", "done": True, "na": False}],
            "classification": {"parent_a": classify_individual(rep["parent_a_rating"]), "parent_b": classify_individual(rep["parent_b_rating"]), "joint": classify_joint(rep["joint_rating"])},
            "library": {"individual_resources": INDIVIDUAL_RESOURCES, "joint_resources": JOINT_RESOURCES, "conflict_options": CONFLICT_OPTIONS, "joint_process_options": JOINT_OPTIONS,
                        "receipt_options": RECEIPT, "statuses": STATUSES},
            "notes": {"safety": SAFETY_NOTE, "rating": RATING_NOTE, "tagline": TAGLINE},
            "case": {"id": "sample-case", "case_code": "SA-26-EDU-000000", "child_name": "M. Carter", "subject_label": "Education & School Decisions"},
            "professional": SAMPLE_PRO, "court": SAMPLE_COURT}
