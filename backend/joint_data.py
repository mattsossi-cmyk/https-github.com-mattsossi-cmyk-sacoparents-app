CONFIDENTIALITY_NOTICE = (
    "Your information is private by default. SA CoParents does not share your assessment or reports "
    "with your co-parent or a professional unless you choose to share them, except where disclosure "
    "is required by law. Completing an SA CoParents assessment does not automatically provide your "
    "answers to your co-parent. Unless a particular feature clearly tells you otherwise before you "
    "submit information: your individual responses remain associated with your account and are not "
    "automatically disclosed to the other parent; when SA CoParents generates a report, Foundation "
    "Statement, Mediation Statement, or similar output, the resulting document may contain selected "
    "information derived from your responses. You should review any report before sharing it."
)

QUESTIONS = [
    ("needs_most", "Child's Primary Need", "What do you believe your child needs most right now regarding this subject?"),
    ("working_well", "What Is Working", "What is working well?"),
    ("concerns", "Concerns", "What concerns you?"),
    ("improve", "Desired Improvements", "What would you like to improve?"),
    ("options", "Options You Would Consider", "What options would you be willing to consider?"),
    ("other_parent", "The Other Parent's Likely Concerns", "What do you believe the other parent may be concerned about?"),
]

NEXT_STEPS = [
    "Continue Parent Discussion",
    "Discuss With Mediator",
    "Consult Teacher / School Counselor",
    "Consult Child's Professional",
    "Develop Written Parenting Protocol",
    "Create Another Joint Report",
]


def S(needs, conversation, options, questions):
    return {"needs": needs, "conversation": conversation, "options": options, "questions": questions}


SUBJECTS = {
    "communication": {
        "label": "Communication",
        **S(
            ["Reliable exchange of child-related information", "Predictable response expectations", "Respectful, child-focused tone", "Clear emergency communication", "Boundaries around times and channels"],
            ["What information must always be shared between households?", "What response time is reasonable for routine versus urgent matters?", "Which channel should be used for which topics?", "How will schedule changes be communicated?", "What communication is appropriate in front of the child?"],
            ["Option A: A shared co-parenting communication app.", "Option B: Email-only communication for non-urgent matters.", "Option C: A weekly structured update plus an emergency communication protocol."],
            ["Could the parents agree on outcomes without identical communication styles?", "What information requires immediate communication?", "Would a written communication protocol help?", "Would professional-assisted communication be useful?"],
        ),
    },
    "schedule": {
        "label": "Parenting Schedule",
        **S(
            ["A predictable parenting schedule", "Reliable pickup and drop-off times", "Advance notice of changes", "Consistency for the child", "A process for resolving scheduling conflicts"],
            ["What weekly schedule best serves the child's routine?", "How far in advance should changes be requested?", "How will holidays and school breaks rotate?", "What happens when a parent runs late?", "How are scheduling disagreements resolved?"],
            ["Option A: A fixed weekly schedule with set exchange times.", "Option B: A rotating schedule coordinated through a shared online calendar.", "Option C: Keep the current schedule with a formal change-request process."],
            ["Could the parents agree on the schedule's purpose without identical households?", "What schedule information should always be shared?", "Would a shared calendar reduce conflict?", "Would a mediator help finalize the schedule?"],
        ),
    },
    "education": {
        "label": "School / Education",
        **S(
            ["Consistency between homes", "Academic support", "Predictable expectations", "Communication between homes", "Communication with the school"],
            ["When should homework ordinarily be completed?", "Should tutoring be considered?", "How will school information be exchanged?", "Should both parents attend conferences?", "What information requires immediate communication?"],
            ["Option A: Homework immediately after school.", "Option B: A 30-minute transition period followed by homework.", "Option C: A completion deadline while allowing each household flexibility regarding timing."],
            ["Could the parents agree on the outcome without requiring identical household routines?", "What information should always be shared between households?", "Are there school professionals who could provide additional information?", "Would a teacher conference help resolve the remaining differences?"],
        ),
    },
    "medical": {
        "label": "Medical Care",
        **S(
            ["Consistent implementation of treatment plans", "Both parents receiving the same medical information", "Clear medication responsibilities", "Shared emergency plan", "Timely scheduling of appointments"],
            ["How will medical information be shared after appointments?", "Who schedules and attends appointments?", "How are medications managed between households?", "How will emergency decisions be made?", "When is a second opinion appropriate?"],
            ["Option A: A joint pediatrician meeting to align on the treatment plan.", "Option B: Shared patient portal access plus a written medication protocol.", "Option C: Each parent receives information directly from providers, with a shared medical log."],
            ["Could the parents agree on the treatment goal without identical home routines?", "What medical information should always be shared immediately?", "Would a provider meeting answer the remaining questions?", "Is a specialist consultation warranted?"],
        ),
    },
    "psychological": {
        "label": "Psychological / Emotional Needs",
        **S(
            ["Emotional security in both homes", "Consistent, calming routines", "Observation without diagnosis", "Access to appropriate professional support", "Both parents receiving the same provider information"],
            ["What changes have each parent observed, and when?", "What routines help the child feel settled?", "Should a professional evaluation be considered?", "How will provider information be shared?", "How can transitions be made easier emotionally?"],
            ["Option A: A pediatrician or child-specialist consultation.", "Option B: Consistent calming routines agreed for both households.", "Option C: A follow-up assessment by an appropriate professional before deciding on treatment."],
            ["Could the parents agree on support without agreeing on the cause?", "What observations should always be shared?", "Which professional could provide clarity?", "Would a parent consultation with a child specialist help?"],
        ),
    },
    "activities": {
        "label": "Extracurricular Activities",
        **S(
            ["Continuity in activities the child enjoys", "Clear cost and transportation responsibilities", "Schedule coordination", "Both parents able to attend events", "Age-appropriate commitments"],
            ["Which activities continue this year?", "How are costs divided?", "Who handles transportation on which days?", "Can both parents attend games and recitals?", "How many activities are appropriate?"],
            ["Option A: Keep current activities with a shared activity calendar.", "Option B: Each parent chooses activities for their own parenting time.", "Option C: Agree on a set number of activities per season with shared costs."],
            ["Could the parents agree on the child's participation without identical schedules?", "What activity information should always be shared?", "Would a shared calendar solve the logistics?", "What does the child want to continue?"],
        ),
    },
    "transitions": {
        "label": "Exchanges / Transitions",
        **S(
            ["Calm, predictable exchanges", "Punctuality and reliability", "Neutral locations when needed", "The child shielded from adult tension", "Clear backup plans"],
            ["Where and when should exchanges occur?", "How is lateness communicated?", "Should exchanges happen at school or neutral locations?", "What should never happen during an exchange?", "What is the backup plan when an exchange fails?"],
            ["Option A: School-based exchanges to minimize direct contact.", "Option B: A neutral public exchange location with set times.", "Option C: Curbside exchanges with a written punctuality protocol."],
            ["Could the parents agree on exchange rules without other agreements?", "What makes exchanges stressful for the child?", "Would a third-party exchange help?", "Should exchange terms be written into the parenting plan?"],
        ),
    },
    "decision_making": {
        "label": "Decision-Making",
        **S(
            ["A clear process for major decisions", "Timely decisions about the child's needs", "Defined areas of joint versus individual authority", "Reliable information sharing before decisions", "A fallback process when parents disagree"],
            ["Which decisions require both parents?", "What information must be shared before a decision?", "What is a reasonable response window?", "What happens when the parents cannot agree?", "Which day-to-day decisions belong to each household?"],
            ["Option A: Joint decisions on defined major issues with a 72-hour response window.", "Option B: Divided decision authority by category.", "Option C: Mediation as the required step before any court filing on disputes."],
            ["Could the parents agree on a process before agreeing on outcomes?", "What decisions are truly urgent versus routine?", "Would a parenting coordinator help with deadlocks?", "Should the decision process be written down?"],
        ),
    },
    "holidays": {
        "label": "Holidays",
        **S(
            ["Predictable holiday arrangements", "Fair rotation of special days", "Advance planning", "The child's traditions preserved in both homes", "Clear travel rules during holidays"],
            ["How should major holidays rotate?", "How are school breaks divided?", "How much advance notice is needed for holiday travel?", "Which traditions matter most to the child?", "How are birthdays and Mother's/Father's Day handled?"],
            ["Option A: Alternate major holidays annually.", "Option B: Split each holiday by time of day.", "Option C: A fixed holiday schedule written a year in advance."],
            ["Could the parents agree on a rotation without agreeing on every detail?", "What holiday information should always be shared?", "Would planning a full year ahead reduce conflict?", "Are there traditions both parents want to preserve?"],
        ),
    },
    "technology": {
        "label": "Technology",
        **S(
            ["Consistent screen-time expectations", "Age-appropriate content rules", "Reliable parent-child contact during the other parent's time", "Shared expectations about devices", "Online safety"],
            ["What screen-time limits apply in each home?", "When can the child call or message the other parent?", "Which apps, games, or sites are acceptable?", "Who monitors the child's online activity?", "At what age should the child have a phone?"],
            ["Option A: A shared screen-time agreement for both households.", "Option B: Each household sets its own rules with agreed safety minimums.", "Option C: A scheduled daily call window with the other parent."],
            ["Could the parents agree on safety minimums without identical rules?", "What online activity should always be shared?", "Would the child's school or pediatrician offer guidance?", "Should device rules be written into a protocol?"],
        ),
    },
    "routine": {
        "label": "Child's Routine",
        **S(
            ["Predictable daily structure", "Consistent sleep and meal routines", "Smooth weekday/weekend rhythm", "Age-appropriate responsibilities", "Flexibility when life requires it"],
            ["What bedtime and morning routines does the child need?", "How similar should homework and meal times be?", "Which routines are non-negotiable for the child?", "How are changes to routine communicated?", "What responsibilities should the child have in each home?"],
            ["Option A: A shared core routine (sleep, meals, homework) in both homes.", "Option B: Each home keeps its routine with agreed anchors like bedtime.", "Option C: A written routine the child can see and rely on."],
            ["Could the parents agree on anchor points without identical routines?", "Which routines most affect the child's wellbeing?", "Would a visible routine chart help the child?", "Should routines be revisited as the child grows?"],
        ),
    },
    "mediation": {
        "label": "Mediation Statement",
        **S(
            ["A structured setting for the conversation", "Both perspectives fully heard", "Focus on the child's needs", "Options generated before decisions", "Clear documentation of any agreement"],
            ["What outcome would each parent consider acceptable?", "What information is missing before deciding?", "What options have not yet been considered?", "What can each parent offer the other?", "What should be documented afterward?"],
            ["Option A: Resolve the issue in a single focused mediation session.", "Option B: Exchange written proposals before meeting.", "Option C: Bring in a subject-matter professional before the session."],
            ["Could the parents agree on the goal before the details?", "What would each parent need to feel resolved?", "Is additional professional input needed?", "What happens if mediation does not resolve it?"],
        ),
    },
    "co_parenting": {
        "label": "Co-Parenting",
        **S(
            ["Predictable co-parenting structure", "Consistent expectations between homes", "Reliable information sharing", "Clear parenting roles", "Reduced child exposure to disagreement"],
            ["What co-parenting structure best supports the child?", "How are responsibilities divided day to day?", "What information must always be shared?", "How will disagreements be handled?", "What is already working well?"],
            ["Option A: A written co-parenting protocol covering routines and communication.", "Option B: A shared calendar plus scheduled monthly check-ins.", "Option C: Parenting coordination sessions to design the structure together."],
            ["Could the parents agree on outcomes without identical approaches?", "What does the child most need from the co-parenting system?", "Would a parenting coordinator help?", "What can the parents agree to try first?"],
        ),
    },
    "child_needs": {
        "label": "Child's Needs",
        **S(
            ["The child's stated needs heard by both parents", "Age-appropriate consideration of the child's views", "Consistency around the child's top needs", "Professional input when needs are unclear", "Regular reassessment as the child grows"],
            ["What does the child say they need?", "What does each parent observe day to day?", "Which needs are urgent versus ongoing?", "Who can provide an outside perspective?", "How will the parents revisit this as the child grows?"],
            ["Option A: A child-specialist consultation to clarify needs.", "Option B: Each parent documents observations for two weeks, then compares.", "Option C: An age-appropriate conversation with the child, guided by a counselor."],
            ["Could the parents agree on the child's top need?", "What observations should be shared?", "Would a child specialist help?", "What can be tried first?"],
        ),
    },
    "special_needs": {
        "label": "Special Needs",
        **S(
            ["Consistent implementation of support plans", "Shared understanding of the child's diagnosis or needs", "Coordinated therapies and appointments", "School accommodations aligned across homes", "Respite and support for both households"],
            ["How is the support plan implemented in each home?", "What therapies or services are current or needed?", "How are school accommodations (IEP/ARD/504) coordinated?", "How are equipment and supplies handled between homes?", "What training would help each parent?"],
            ["Option A: A joint meeting with the child's specialist or care coordinator.", "Option B: A written care protocol duplicated for both households.", "Option C: Coordinated ARD/IEP advocacy with shared school communication."],
            ["Could the parents align on the support plan's priorities?", "What information from providers would help?", "Should both parents attend the next planning meeting?", "What consistency matters most to the child?"],
        ),
    },
    "safety": {
        "label": "Safety",
        **S(
            ["Physical and emotional safety first", "Structures that limit unsafe contact", "Clear emergency protocols", "Professional guidance experienced with family violence", "Detailed, unambiguous arrangements"],
            ["What arrangements keep the child and the safe parent protected?", "Are current orders or protections clear to both parents?", "What communication is safe and necessary?", "What warning signs require immediate action?", "Who should be involved professionally?"],
            ["Option A: Neutral or supervised exchange locations.", "Option B: Communication through an app or professionals only.", "Option C: Detailed parenting orders with emergency protocols."],
            ["Is any direct communication currently safe?", "What professional guidance is in place?", "Are emergency contacts and protocols documented?", "What structure reduces risk while meeting the child's needs?"],
        ),
    },
    "risk": {
        "label": "Risk Factors",
        **S(
            ["Accurate identification of risk patterns", "Documentation through appropriate channels", "Power imbalances addressed in any process", "Safety planning before problem-solving", "Ongoing professional monitoring"],
            ["What patterns of concern has each parent observed?", "Are there power imbalances affecting discussions?", "What documentation exists or should exist?", "What immediate safeguards are needed?", "Which professionals should assess the situation?"],
            ["Option A: A professional risk assessment before any joint process.", "Option B: Separate (shuttle) mediation rather than face-to-face.", "Option C: Attorney-assisted communication only."],
            ["Is joint discussion appropriate at all right now?", "What would a professional need to know?", "What protections exist today?", "What is the safest next step?"],
        ),
    },
    "safety_communication": {
        "label": "Safe Communication",
        **S(
            ["Communication channels that protect safety", "Written records of necessary communication", "No pressure for direct contact", "Emergency-only contact rules", "Professional-filtered communication when needed"],
            ["What channel is safe for necessary communication?", "What topics are essential to communicate?", "What response expectations are realistic and safe?", "Should communication go through a third party?", "What happens in an emergency?"],
            ["Option A: Written-only communication through a monitored app.", "Option B: Communication through attorneys or a coordinator.", "Option C: Emergency-only direct contact with all else in writing."],
            ["Is any direct communication safe?", "What must be communicated for the child?", "Would a communication app provide the needed structure?", "Who can assist if communication breaks down?"],
        ),
    },
    "safeguards": {
        "label": "Safeguards",
        **S(
            ["Documented safety arrangements", "Enforceable boundaries and orders", "Safe exchange procedures", "Support resources for the child and the safe parent", "Regular review of safeguards"],
            ["Which safeguards are currently in place?", "Are orders being followed?", "What additional protections are needed?", "How are exchanges made safe?", "When should safeguards be reviewed?"],
            ["Option A: Supervised exchanges or visitation where appropriate.", "Option B: Detailed court orders with specific protections.", "Option C: A safety plan developed with a family-violence professional."],
            ["Are current safeguards working?", "What would make exchanges safer?", "Is professional safety planning in place?", "What should be reviewed at the next check-in?"],
        ),
    },
    "custom": {
        "label": "Other / Custom Subject",
        **S(
            ["Clarity about the child's needs", "Both parents' perspectives considered", "Consistency where it matters most", "Information shared between homes", "Professional input when helpful"],
            ["What outcome would best serve the child?", "What does each parent observe that the other may not?", "What information is missing?", "What options have not been considered?", "What is a reasonable first step?"],
            ["Option A: Continue the discussion directly with a shared agenda.", "Option B: Gather additional information before deciding.", "Option C: Consult an appropriate professional together."],
            ["Could the parents agree on the goal without identical approaches?", "What information should always be shared?", "Would a professional's input help?", "What can the parents agree to try first?"],
        ),
    },
}

ORDERED_SUBJECT_KEYS = [
    "communication", "schedule", "education", "medical", "psychological", "activities",
    "transitions", "decision_making", "holidays", "technology", "routine",
    "co_parenting", "child_needs", "special_needs",
    "safety", "risk", "safety_communication", "safeguards",
    "mediation", "custom",
]

HUB_MAIN_SUBJECTS = [
    "co_parenting", "education", "medical", "psychological", "communication",
    "child_needs", "schedule", "special_needs", "activities", "transitions",
]

HUB_SAFETY_SUBJECTS = ["safety", "risk", "safety_communication", "safeguards"]


def merged_subject_config(subject_keys):
    if len(subject_keys) == 1:
        return SUBJECTS[subject_keys[0]]
    merged = {"needs": [], "conversation": [], "options": [], "questions": []}
    for k in subject_keys:
        cfg = SUBJECTS[k]
        label = cfg["label"]
        merged["needs"] += cfg["needs"][:3]
        merged["conversation"] += [f"[{label}] {q}" for q in cfg["conversation"][:3]]
        merged["options"] += [f"[{label}] {o}" for o in cfg["options"][:2]]
        merged["questions"] += [f"[{label}] {q}" for q in cfg["questions"][:2]]
    return merged


SAFETY_SUBJECT_KEYS = {"safety", "risk", "safety_communication", "safeguards"}
SAFETY_CONFIDENTIALITY = (
    "Confidentiality: Your individual responses will not be shared with the other party. "
    "This report is prepared for review with a third-party mediator. Only the completed "
    "comparison is provided to the mediator; your answers remain private."
)

SAFETY_PURPOSE = (
    "This report is prepared through a third-party mediator rather than directly between the "
    "parents. It compares the independently provided perspectives of both parents to identify "
    "areas of shared understanding, differences in perspective, and subjects that may benefit "
    "from professional assistance. Individual responses are not shared between the parties."
)

AGREEMENT_AREAS = [
    ("parenting_schedule", "Parenting Schedule", "What parenting schedule arrangement do you propose?"),
    ("holidays", "Holidays & Special Days", "What arrangement do you propose for holidays and special days?"),
    ("decision_making", "Decision-Making", "What arrangement do you propose for major decisions about the child?"),
    ("communication", "Parent Communication", "What arrangement do you propose for communication between the parents?"),
    ("exchanges", "Exchanges & Transportation", "What arrangement do you propose for exchanges and transportation?"),
    ("expenses", "Child-Related Expenses", "What arrangement do you propose for child-related expenses?"),
    ("information_sharing", "Information Sharing", "What arrangement do you propose for sharing school, medical, and activity information?"),
    ("dispute_resolution", "Dispute Resolution", "What arrangement do you propose for resolving future disagreements?"),
]

AGREEMENT_PURPOSE = (
    "This document brings together both parents' independently proposed terms for a co-parenting "
    "agreement. Terms where the parents' proposals align are ready to be formalized. Terms marked "
    "for discussion are candidates for parent conversation or mediation before finalizing. "
    "This document is not legal advice and does not determine which parent is right or wrong."
)

AGREEMENT_CONFIDENTIALITY = (
    "Each parent's proposals remain private until both have submitted. This combined document "
    "becomes visible to both parents only when complete."
)
