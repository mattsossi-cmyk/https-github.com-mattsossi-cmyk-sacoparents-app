"""Fictional, fully written Sample Professional Report (legal) for the public samples page."""
from coparenting_tiers import framework_block, joint_findings, suggested_score
from joint_engine import SAMPLE_SCENARIOS

SAMPLE_PRO = {"name": "Jordan Reyes, LPC", "pro_role": "Parenting Facilitator", "organization": "Alamo Family Solutions (fictional)", "license_number": "TX-LPC-00000", "phone": "", "city": "San Antonio", "state": "TX", "email": "", "credentials_verified": True}
SAMPLE_COURT = {"court_name": "000th Judicial District Court, Bexar County (fictional)", "cause_number": "2026-CI-00000", "judge_name": "[Presiding Judge]", "judge_email": ""}

STATEMENT_TEXT = {
    "role_basis": "Appointed Parenting Facilitator by court referral through SA CoParents Align. My role is to facilitate child-focused alignment between the parents; I make no findings about either parent and no recommendation regarding conservatorship or possession.",
    "process_summary": "Each parent independently completed the Educational Needs assessment through the SA CoParents App. Individual answers were never shared between the parents. The Joint Alignment Report compared both perspectives and was reviewed in one facilitated session (60 minutes, video).",
    "alignment_areas": "Both parents identify Sofia's reading confidence as the priority this school year, agree homework should happen before screen time in both homes, and want a single point of contact with the classroom teacher.",
    "further_attention": "The parents differ on whether to engage a private tutor now or wait for the school's reading-intervention placement, and on how weekday homework time is divided between households.",
    "partial_alignment": "Both parents are open to a shared homework log and to copying each other on teacher emails. With a short structured discussion, a tutoring decision keyed to the school's next progress report appears achievable.",
    "alignment_summary": "Significant alignment on the child's educational goal and daily routine; disagreement is limited to the tutoring decision and homework scheduling. These items relate directly to Sofia's reading progress and are suitable for facilitated resolution rather than adjudication.",
    "resources_considered": "Bexar County DRC co-parenting session; shared homework log; classroom-teacher joint conference; school reading-intervention referral.",
    "safety_considerations": "",
    "current_status": "Both assessments complete; Joint Alignment Report generated; one facilitated session completed. Parents have adopted the shared homework log on a trial basis.",
    "observations": "Both parents engaged respectfully and used child-centered language throughout. Each described the other's homework routine accurately, which supported a productive exchange. Communication is most effective in writing with a 24-hour response window.",
    "next_steps": "1) Parents exchange written tutoring proposals before the next progress report. 2) Second facilitated session within 30 days focused on homework scheduling. 3) Joint teacher conference scheduled by the parents. 4) Progress update to the court after the second session.",
}


def sample_professional_report() -> dict:
    sc = SAMPLE_SCENARIOS["education"]
    doc = {"subject": "education", "subjects": ["education"], "subject_label": sc["label"], "child_name": sc["child"], "kind": "joint_report",
           "participants": {"a": {"name": sc["pa"]}, "b": {"name": sc["pb"]}}, "responses": {"a": {"answers": sc["answers_a"]}, "b": {"answers": sc["answers_b"]}}}
    findings = joint_findings(doc)
    suggestion = suggested_score(doc)
    score = 6
    fw = framework_block(score, {"tools": []}, {"resources": ["Northside ISD Reading Intervention Program (school referral)"]}, findings["subject_options"])
    statement = {**STATEMENT_TEXT, "role": "Parenting Facilitator", "materials_reviewed": ["Parent A Assessment", "Parent B Assessment", "Joint Report", "Educational Assessment"],
                 "dynamic_score": score, "framework": fw, "status": "ready", "version": 2, "level_changed_from": 4,
                 "level_change_note": "Parents completed one facilitated session and adopted written-only scheduling through a shared homework log."}
    history = [{"version": 1, "at": "2026-08-12", "score": 4, "label": "Level 4-6: Moderate Conflict / Low Trust", "color": "#d97706", "superseded": True, "note": "", "changed_from": None},
               {"version": 2, "at": "2026-09-16", "score": 6, "label": fw["label"], "color": fw["color"], "superseded": False, "note": statement["level_change_note"], "changed_from": 4}]
    return {"is_sample": True, "title": "Sample Professional Report (Legal) — fictional data", "professional": SAMPLE_PRO, "court": SAMPLE_COURT, "case_code": "SA-26-EDU-000000",
            "subject_label": sc["label"], "child_name": sc["child"], "statement": statement, "findings": findings, "suggested_score": suggestion, "level_history": history, "date": "2026-09-16",
            "attestation_text": ("I attest that this Professional Report reflects my professional observations of the facilitation process, that it contains no recommendation "
                                 "regarding conservatorship or possession, and that I have authority to submit it to the court."),
            "sections": ["1. Case & Referral", "2. Materials Reviewed", "3. Process Completed by the Parents", "4. Joint Assessment Findings", "5. Co-Parenting Ability Level",
                         "6. Parent Alignment — Based on Joint Report", "7. Conflict Management — Approaches to Conflict", "8. Roadmap", "9. Professional Summary"]}


def sample_judicial_case() -> dict:
    """Read-only, fictional judicial case page payload (same shape as /court-dashboard/cases/{id}) so courts can preview the portal."""
    r = sample_professional_report()
    f, st = r["findings"], r["statement"]
    steps = ["Court Referral", "Accepted", "Parents Invited", "Assessments Complete", "Joint Report Ready", "Professional Statement Ready", "Submitted to Court"]
    ref = {"id": "sample", "judge_name": "[Presiding Judge]", "court_name": r["court"]["court_name"], "cause_number": r["court"]["cause_number"], "subject": "education", "child_initials": "S.",
           "professional_name": r["professional"]["name"], "status": "submitted", "created_at": "2026-07-30T14:00:00Z", "responded_at": "2026-07-31T09:10:00Z", "hearing_date": "2026-10-15",
           "case_code": r["case_code"], "overdue": False, "requested_reports": [{"key": "education", "label": "Educational Needs", "subjects": ["education"]}]}
    checklist = [{"label": x, "done": True} for x in ("Court referral sent", "Professional accepted", "Parents invited", "Parent A completed assessment", "Parent B completed assessment",
                                                     "Joint Report generated", "Professional Statement ready", "Submitted to court")]
    summary = {"current_status": "Ready for court review", "professional": "Referral accepted; documents submitted (version 2).", "parents": "Both parents completed the ordered assessments.",
               "joint_assessment": "100% complete and professionally reviewed.", "professional_statement": "Submitted (version 2, 2026-09-16).",
               "recent_communication": "Final reports submitted to the court portal on 2026-09-16.", "outstanding": "Court review.", "next_action": "Review the Joint Alignment Report and Professional Report.",
               "stage_label": steps[6], "generated_at": "2026-09-16T16:00:00Z", "signature": "sample",
               "disclaimer": "Procedural status summary generated from authorized case-status records only. It is not a legal conclusion, credibility determination, or judicial recommendation."}
    report = {"key": "education", "label": f["subject_label"], "case_code": r["case_code"], "version": 2, "packet_id": "sample", "alignment": f["alignment"], "differences": f["differences"], "child_focused": f["child_focused"]}
    statement = {**st, "professional_name": r["professional"]["name"], "submitted_at": "2026-09-16T16:00:00Z", "packet_id": "sample"}
    subs = [{"version": h["version"], "packet_id": "sample", "at": h["at"] + "T16:00:00Z", "sha256": "0" * 64, "superseded": h["superseded"]} for h in r["level_history"]]
    return {"is_sample": True, "referral": ref, "case_code": r["case_code"], "stage": {"index": 6, "steps": steps, "court_referred": True, "label": steps[6]}, "checklist": checklist,
            "parents_invited": 2, "parents_participating": 2, "status_summary": summary, "counts": {"alignment_areas": len(f["alignment"]), "discussion_areas": len(f["differences"]), "completion_pct": 100},
            "reports": [report], "statement": statement, "level_history": r["level_history"], "submissions": subs, "communication_summary": None, "disclaimer": summary["disclaimer"]}
