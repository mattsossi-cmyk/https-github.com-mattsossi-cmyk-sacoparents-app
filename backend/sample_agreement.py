"""Fictional, fully answered Co-Parenting Agreement used for the public sample (web + PDF)."""
from joint_engine import generate_agreement

_APP = "SA CoParents Align app"

_GENERAL = {
    "foundation": ("M. needs calm, predictable routines in both homes and parents who do not argue in front of her.", "M. needs both of us to stay calm at exchanges and keep her routines steady in both homes."),
    "transitions": ("Exchanges at school on school days, neutral public location otherwise, with brief and polite greetings.", "Exchanges at school when possible, otherwise a neutral public location; keep greetings brief and polite."),
    "communication": ("All routine communication through the app, brief and factual, within 24 hours.", "Use the app for all routine communication; keep it brief, factual, and answer within 24 hours."),
    "education": ("Both parents have portal access and attend school meetings; homework routine is the same in both homes.", "Both parents keep portal access, attend school meetings, and follow the same homework routine."),
    "medical": ("Parent A schedules routine appointments; medication and records shared in the app the same day.", "Parent A schedules routine appointments and shares medication and records through the app the same day."),
    "psychological": ("M. keeps her current counselor; both parents follow the counselor's recommendations and protect her privacy.", "Keep the current counselor, follow the counselor's recommendations, and protect M.'s privacy."),
    "activities": ("One sport per season agreed in advance; costs split equally; both parents may attend events.", "One sport per season agreed in advance, costs split equally, and both parents may attend events."),
    "wellness_tech": ("Same bedtime and screen rules in both homes; no smartphone until age 13; no social media accounts yet; devices charge outside the bedroom.", "Same bedtime and screen rules in both homes, no smartphone before 13, no social media accounts yet, and devices charge outside her bedroom."),
    "decisions": ("Major decisions raised in the app with 14 days' notice and full information before deciding.", "Raise major decisions in the app with 14 days' notice and share full information before deciding."),
    "differences": ("Try a written proposal first, then the Communication Coach, then mediation before court.", "Written proposal first, then the Communication Coach, then mediation before any court filing."),
    "review": ("Review the agreement every six months and after any major change.", "Review every six months and after any major change."),
}

_FOLLOW_UPS = {
    "foundation": {"needs": ("Predictable routines, calm exchanges, and both parents at her events.", "Steady routines, calm exchanges, and seeing both parents at her events."), "concern": ("M. overhears adult disagreements at exchanges.", "M. is exposed to tension when we hand off in person."), "priority": ("M.'s school success and emotional security.", "Her school success and feeling secure in both homes.")},
    "transitions": {"where": ("At school on school days; otherwise the library parking lot at 6:00 pm.", "At school on school days; otherwise the library parking lot at 6:00 pm."), "late": ("Text 15 minutes ahead if running late; 10-minute grace period.", "Just phone me when delayed; I think a longer 20-minute window is fair."), "changes": (f"Request changes at least 48 hours ahead through the {_APP}.", f"Request changes at least 48 hours ahead through the {_APP}."), "belongings": ("A shared backpack travels with M.; medication and school items are checked at each exchange.", "A shared backpack travels with M.; medication and school items are checked at each exchange."), "contact": ("One video call at 7:30 pm on non-custodial evenings.", "One video call at 7:30 pm on non-custodial evenings.")},
    "communication": {"method": (f"The {_APP} for all routine matters.", f"The {_APP} for all routine matters."), "response": ("24 hours for routine messages; 2 hours for urgent ones.", "24 hours for routine messages; 2 hours for urgent ones."), "emergency": ("Injury, illness requiring care, or safety concern — phone call first, then a note in the app.", "Injury, illness requiring care, or safety concern — phone call first, then a note in the app."), "tone": ("Brief, informative, friendly, and firm.", "Brief, informative, friendly, and firm."), "boundaries": ("No messages about the past relationship; child-related topics only.", "Only child-related topics; nothing about the past relationship.")},
    "education": {"records": ("Both parents have their own portal logins; Parent B sets up his by the end of the month.", "Both parents have their own portal logins; I will set mine up by the end of the month."), "share": ("Within 2 days, through the app.", "Within 2 days, through the app."), "meetings": ("Both may attend all conferences and ARD/IEP meetings; the school schedules them.", "Both may attend all conferences and ARD/IEP meetings; the school schedules them."), "homework": ("Homework before screens, same rule in both homes.", "Homework before screens in both homes."), "disagree": ("Ask the teacher or counselor first.", "Ask the teacher or counselor first.")},
    "medical": {"schedule": ("Parent A schedules routine visits and posts them in the app calendar.", "Parent A schedules routine visits and posts them in the app calendar."), "medication": ("Medication travels in the shared backpack with a written log.", "Medication travels in the shared backpack with a written log."), "insurance": ("Parent B carries insurance; uncovered costs are split 50/50 within 30 days.", "I carry insurance; uncovered costs are split 50/50 within 30 days."), "records": ("Same day, through the app.", "Same day, through the app."), "emergency": ("Call 911 if needed, then the other parent within one hour.", "Call 911 if needed, then the other parent within one hour.")},
    "psychological": {"counseling": ("Keep the current counselor; any change requires both parents' agreement.", "Keep the current counselor; any change requires both parents' agreement."), "appointments": ("The custodial parent takes M.; a short update is posted in the app afterward.", "The custodial parent takes M.; a short update is posted in the app afterward."), "recommendations": ("Both parents follow the counselor's written recommendations.", "Both parents follow the counselor's written recommendations."), "privacy": ("Neither parent asks M. about the other home or her sessions.", "Neither parent questions M. about the other home or her sessions."), "continuity": ("Same bedtime routine (8:30 pm) and calm-down steps in both homes.", "Bedtime at 8:30 pm and the same calm-down steps in both homes.")},
    "activities": {"enroll": ("One sport per season, agreed in the app before enrolling.", "One sport per season, agreed in the app before enrolling."), "transport": ("The custodial parent transports.", "The custodial parent transports."), "expenses": ("Split 50/50; receipts posted in the app.", "Split 50/50; receipts posted in the app."), "attendance": ("Both parents may attend all games and performances.", "Both parents may attend all games and performances."), "conflicts": ("If an activity conflicts with parenting time, the custodial parent decides and offers make-up time.", "The custodial parent decides, but I would like make-up time discussed first.")},
    "wellness_tech": {"anchors": ("Bedtime 8:30 pm, breakfast before school, one hour outdoors most days, and quiet time before bed in both homes.", "Bedtime 8:30 pm, breakfast before school, one hour outdoors most days, and quiet time before bed in both homes."), "phone": ("No smartphone until age 13; a basic call-and-text phone before then if needed; costs split 50/50.", "No smartphone until 13; a basic call-and-text phone if needed before then, with costs split 50/50."), "social": ("No social media accounts until 13; approved games only, with parental controls set the same way in both homes.", "No social media until 13 and parental controls set the same in both homes; I would like to review the approved games list together."), "screens": ("One hour on school days after homework, two hours on weekends; devices charge in the kitchen overnight.", "One hour on school days after homework, two hours on weekends; devices charge in the kitchen overnight."), "concerns": ("Same day, through the app, with a brief description of what was seen or said.", "Same day, through the app, with a brief description of what was seen or said.")},
    "decisions": {"raise": ("In the app, with at least 14 days' notice.", "In the app, with at least 14 days' notice."), "information": ("Share all relevant documents before either parent decides.", "Share all relevant documents before either parent decides."), "options": ("Each parent lists the options they can accept.", "Each parent lists the options they can accept."), "professional": ("Consult the relevant professional (teacher, doctor, counselor) before deciding.", "Consult the relevant professional (teacher, doctor, counselor) before deciding.")},
    "differences": {"first": ("A written proposal in the app.", "A written proposal in the app."), "tools": ("The SA CoParents Communication Coach and reflection tools.", "The SA CoParents Communication Coach and reflection tools."), "professional": ("Our parent facilitator, Kelly Bernstein.", "Our parent facilitator, Kelly Bernstein."), "mediation": ("Mediation before any court filing, except in an emergency.", "Mediation before any court filing, except in an emergency.")},
    "review": {"schedule": ("Every six months, in January and July.", "Every six months, in January and July."), "triggers": ("A school change, a move, a new partner in the home, or a health diagnosis.", "A school change, a move, a new partner in the home, or a health diagnosis."), "notworking": ("Either parent raises it in the app with a specific example.", "Either parent raises it in the app with a specific example.")},
}


def _answers(side: int) -> dict:
    out = {k: v[side] for k, v in _GENERAL.items()}
    for sec, fus in _FOLLOW_UPS.items():
        for fk, pair in fus.items():
            out[f"{sec}__{fk}"] = pair[side]
    return out


def sample_agreement_doc() -> dict:
    from sample_foundation import sample_foundation_statement
    fs = sample_foundation_statement()
    structured = {k: fs[k] for k in ("child_name", "shared_purpose", "vision", "priorities", "strengths", "needs", "concerns", "wellness_tech", "child_may_need", "commitments", "goals", "future", "parent_commitment")}
    entry = {"title": "Child-Focused Foundation Statement", "content": fs["parent_commitment"], "structured": structured, "source": "align"}
    return {"kind": "agreement", "child_name": "M.", "subject": "Co-Parenting Agreement", "is_demo": True, "case_code": "SA-26-AGR-SAMPLE",
            "participants": {"a": {"name": "Parent A"}, "b": {"name": "Parent B"}},
            "responses": {"a": {"answers": _answers(0), "foundation": [entry]}, "b": {"answers": _answers(1), "foundation": [dict(entry)]}}}


def sample_agreement() -> dict:
    doc = sample_agreement_doc()
    rep = generate_agreement(doc)
    rep["is_sample"] = True
    rep["date"] = "May 29, 2026"
    return rep
