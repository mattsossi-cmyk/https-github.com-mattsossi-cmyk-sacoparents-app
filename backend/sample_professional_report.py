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


def sample_legal_report() -> dict:
    """Fictional Professional Legal Report sample (Jordan Taylor, J.D. · SAMPLE-2026-001)."""
    from legal_ai import AI_LABEL
    from legal_common import CERTIFICATION, OPTIONS_LIBRARY, PATHS, PURPOSE, SAFETY_NOTICE
    pa = {"label": "PARENT-REPORTED INFORMATION", "items": [
        {"heading": "Child-focused priorities", "text": "Parent A reports that Child A needs a predictable weekday routine and consistent homework expectations in both homes."},
        {"heading": "Areas the parent believes are working", "text": "Parent A reports that weekend exchanges occur on time and that both parents attend Child A's soccer games."},
        {"heading": "Primary parenting concerns", "text": "Parent A reports difficulty obtaining timely responses concerning school-related decisions and reports uncertainty about who communicates with the teacher."},
        {"heading": "Goals for resolution", "text": "Parent A would like a written protocol for school communication and a shared calendar for activities."},
        {"heading": "Options the parent would consider", "text": "Parent A reports willingness to use a co-parenting app and to attend a co-parenting education class."}]}
    pb = {"label": "PARENT-REPORTED INFORMATION", "items": [
        {"heading": "Child-focused priorities", "text": "Parent B reports that Child A needs more downtime after school and less pressure around grades."},
        {"heading": "Areas the parent believes are working", "text": "Parent B reports that the exchange schedule is stable and that Child A enjoys time in both homes."},
        {"heading": "Primary parenting concerns", "text": "Parent B reports receiving school messages late and reports concern that schedule changes are requested on short notice."},
        {"heading": "Goals for resolution", "text": "Parent B would like a 48-hour notice expectation for schedule changes and both parents copied on teacher emails."},
        {"heading": "Options the parent would consider", "text": "Parent B reports willingness to use written communication through an app and to try child-focused mediation for the tutoring question."}]}
    joint = {"available": True, "alignment": ["Both parents mentioned \"routine, homework\" when describing the child's primary need.", "Both parents mentioned \"soccer, exchanges\" when describing what is working."],
             "differences": ["Parents expressed different perspectives regarding concerns.", "Parents expressed different perspectives regarding desired improvements."],
             "unresolved": ["Concerns remains an open area for discussion.", "Desired Improvements remains an open area for discussion."],
             "shared_priorities": ["A predictable weekday routine across both homes.", "One clear channel for school communication."],
             "potential_agreement": ["Options You Would Consider: the parents share some common ground; further discussion may produce agreement."], "note": ""}
    lens = {"observations": f"{AI_LABEL}. Parent-reported information reflects shared priorities around routine and school communication, with differences limited to notice periods for schedule changes and the pace of academic support. Neither parent's account is verified fact.",
            "further_attention": f"{AI_LABEL}. School-communication protocol (who contacts the teacher, how both parents are copied) and a notice expectation for schedule changes.",
            "alignment_areas": f"{AI_LABEL}. Stable exchange schedule; joint attendance at activities; agreement that homework precedes screen time.",
            "partial_alignment": f"{AI_LABEL}. Both parents state willingness to use written communication through an app and to attend education or mediation; a tutoring decision keyed to the next progress report appears achievable.",
            "procedural_considerations": f"{AI_LABEL}. Records reviewed are listed in Section 3. No court order concerning communication was entered in the case record; no option is stated as legally required.",
            "professional_comments": "Reviewed and edited by the professional. The parents' willingness to use written communication is consistent across both assessments."}
    st = {**lens, "role": "Parent Facilitator", "legal_status": "finalized", "legal_version": 1, "professional_certified": True, "professional_certified_name": "Jordan Taylor, J.D.", "professional_certified_date": "2026-09-16",
          "certification": {"title": "Parent Facilitator", "bar_number": "00000000 (fictional)", "organization": "Taylor Family Resolution (fictional)", "email": "", "phone": ""}, "finalized_at": "2026-09-16T17:00:00Z",
          "options_resources": ["SA CoParents Communication Builder", "BIFF communication principles", "Structured written communication", "OurFamilyWizard", "Co-Parenting Education", "Child-Focused Mediation"], "options_custom": [],
          "conflict_resolution_paths": ["Structured Communication", "Child-Focused Mediation", "Parent Facilitation / Coordination"],
          "conflict_resolution_explanation": "A structured written-communication protocol addresses the school-communication and notice concerns both parents reported; child-focused mediation is suited to the single open tutoring question; facilitation continues to support implementation.",
          "legal_draft": {"parent_a_summary": pa, "parent_b_summary": pb, "joint": joint, "generated_at": "2026-09-15T15:00:00Z", "safety_notice": False,
                          "child_focused_summary": [{"topic": "Parenting schedule", "text": "Exchange schedule reported stable by both parents; notice period for changes is an open item."},
                                                    {"topic": "Education", "text": "Both parents prioritize reading progress; tutoring timing differs."}, {"topic": "Communication concerning the child", "text": "Both parents request one clear teacher-communication channel."},
                                                    {"topic": "Extracurricular activities", "text": "Both parents attend soccer; shared calendar requested."}],
                          "communication_summary": [{"pattern": "Communication methods", "text": "Text messages and occasional calls; both parents report willingness to move to an app."},
                                                    {"pattern": "Communication breakdown", "text": "Both parents report delayed school information; each attributes delay to the other's channel."},
                                                    {"pattern": "Ability to make joint decisions", "text": "2 aligned and 2 differing area(s) reported."}, {"pattern": "Areas where structure may assist", "text": "School communication; notice period for schedule changes."}]}}
    return {"is_sample": True, "status": "finalized", "report": st, "purpose": PURPOSE, "safety_notice_text": "", "certification_text": CERTIFICATION, "options_library": OPTIONS_LIBRARY, "paths": PATHS, "ai_label": AI_LABEL,
            "information_reviewed": ["Parent A Co-Parenting Assessment", "Parent B Co-Parenting Assessment", "Parent A Foundation Statement", "Parent B Foundation Statement", "Joint Co-Parenting Assessment", "Joint Report", "Educational Assessment", "Professional Notes"],
            "availability": [], "versions": [{"version": 1, "finalized_at": "2026-09-16T17:00:00Z", "professional_name": "Jordan Taylor, J.D."}],
            "professional": {"name": "Jordan Taylor, J.D.", "pro_role": "Parent Facilitator", "organization": "Taylor Family Resolution (fictional)", "city": "San Antonio", "state": "TX"},
            "case": {"id": "sample", "case_code": "SAMPLE-2026-001", "child_name": "Child A, age 9", "subject_label": "Educational Needs", "parent_a": "Parent A", "parent_b": "Parent B", "court": {}}, "date": "2026-09-16", "safety_notice_default": SAFETY_NOTICE}


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
