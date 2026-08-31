UNSURE = "Unsure / need more information"

SCALE = ["No concern", "Minimal concern", "Moderate concern", "Significant concern", UNSURE]

PHILOSOPHY = "We value the parenting system by how well it supports the child, not by how friendly the adults appear."

STANDARD_DISCLAIMER = (
    "This report is not designed to determine which parent is right or wrong. "
    "Different perspectives provide information that can help parents and professionals "
    "better understand the child's needs."
)

IPV_DISCLAIMER = (
    "Agreement between parents is not the measure of success where safety is a concern. "
    "The goal is a parenting structure that appropriately addresses safety, power imbalances, "
    "and the child's needs."
)

DIFFERENCES_NOTE = (
    "Different perspectives do not necessarily mean that either parent is wrong. "
    "Parents may observe their child at different times, in different environments, "
    "and under different circumstances."
)

PURPOSE_ITEMS = [
    "Areas of alignment",
    "Differences in perspective",
    "Child needs and priorities",
    "Issues needing further discussion",
    "Options and resources",
    "Questions for mediation or professional consultation",
]

ALIGNMENT_FOUNDATION_NOTE = (
    "You do not need to agree about everything to successfully parent your child. "
    "Areas where you already agree can provide a foundation for addressing the areas "
    "where your perspectives differ."
)

DISCUSSION_SEQUENCE = [
    {"step": "Begin with alignment", "question": "What do both parents want for this child?"},
    {"step": "Identify the child's need", "question": "What does the child need regarding this issue?"},
    {"step": "Understand different perspectives", "question": "What is each parent observing?"},
    {"step": "Identify missing information", "question": "What information would help?"},
    {"step": "Generate options", "question": "What are the available choices?"},
    {"step": "Determine next steps", "question": "What can the parents agree to try?"},
]

STANDARD_PAGE_TITLES = [
    "Joint Alignment Overview",
    "Your Child at the Center",
    "Where You Align",
    "Where Your Perspectives Differ",
    "What Might Your Child Need?",
    "Options & Resources",
    "Questions for Parent Conversation",
    "Professional Conversation Guide",
    "Parent Action Plan",
    "Joint Alignment Summary",
]

IPV_PAGE_TITLES = [
    "Safety Notice",
    "Individual Communication Concerns",
    "Areas of Shared Child Concern",
    "Differences in Perceived Safety",
    "Communication Risk Factors",
    "Options for Reducing Direct Interaction",
    "Exchange / Transition Considerations",
    "Professional Resources",
    "Questions for Attorney / Mediator / Professional",
    "Safety-Oriented Parenting Structure",
]

SHARED_GOALS_BASE = [
    "Educational stability",
    "Healthy relationship with both parents",
    "Consistent medical care",
    "Emotional security",
    "Predictable routines",
    "Reduced exposure to adult conflict",
]


def T(key, label, question, aligned, action, need):
    return {
        "key": key,
        "label": label,
        "question": question,
        "aligned_text": aligned,
        "action_phrase": action,
        "child_need": need,
    }


ASSESSMENT_TYPES = {
    "general": {
        "key": "general",
        "title": "General Co-Parenting",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "General Co-Parenting",
        "description": "The broadest view of your co-parenting system: communication, decision-making, consistency, transitions, boundaries, and more.",
        "central_question": "What predictable structure would help both parents consistently meet this child's needs?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, developing a more predictable method for {focus} appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("communication", "Communication", "How well are you and the other parent exchanging child-related information?", "Both parents rated their communication effectiveness similarly.", "improving how child-related information is exchanged", "A predictable, low-conflict method for exchanging child-related information."),
            T("decision_making", "Decision-Making", "How satisfied are you with how major decisions about your child are made?", "Both parents view the current decision-making process similarly.", "clarifying how major child-related decisions are made", "A clear, agreed process for making child-related decisions."),
            T("consistency", "Consistency Between Households", "How consistent are rules and expectations between your two households?", "Both parents rated household consistency similarly.", "creating more consistent expectations between households", "More consistent expectations between households."),
            T("transitions", "Transitions & Exchanges", "How smoothly are exchanges, pickups, and drop-offs currently working?", "Both parents view transitions and exchanges similarly.", "making exchanges and transitions more predictable", "Predictable, low-stress exchanges and transitions."),
            T("boundaries", "Boundaries", "How appropriate are parent and child boundaries in your co-parenting relationship?", "Both parents rated parent and child boundaries similarly.", "strengthening parent and child boundaries", "Clear boundaries that keep adult matters between adults."),
            T("conflict_exposure", "Child Exposure to Conflict", "How often is your child exposed to adult disagreement or tension?", "Both parents rated the child's exposure to conflict similarly.", "reducing the child's exposure to adult conflict", "Reduced exposure to adult disagreement."),
            T("parenting_roles", "Parenting Roles", "How clear are you and the other parent about each person's parenting responsibilities?", "Both parents view parenting roles and responsibilities similarly.", "clarifying parenting roles and responsibilities", "Shared clarity about each parent's responsibilities."),
            T("problem_solving", "Problem Solving", "How effectively are disagreements about your child currently resolved?", "Both parents rated problem solving similarly.", "resolving child-related disagreements more constructively", "A constructive process for resolving disagreements."),
            T("schedule", "Parenting Schedule", "How well is the current parenting schedule working for your child?", "Both parents view the parenting schedule similarly.", "adjusting the parenting schedule", "A predictable parenting schedule the child can rely on."),
            T("information_sharing", "Information Sharing", "How completely is important information (school, medical, activities) shared between households?", "Both parents rated information sharing similarly.", "sharing school, medical, and activity information more reliably", "Both parents receiving the same child-related information."),
        ],
        "options": [
            "Co-parenting communication app",
            "Structured communication protocol",
            "Shared parenting calendar",
            "Detailed parenting plan",
            "Parenting coordinator",
            "Child-focused mediation",
            "Co-parenting counseling",
            "Consistent household routines",
            "Scheduled parent check-in meetings",
            "Written information-sharing agreement",
        ],
        "needs": [
            {"title": "Consistency", "text": "The child may benefit from more consistent expectations between households."},
            {"title": "Information", "text": "Both parents may benefit from receiving the same child-related information directly."},
            {"title": "Professional Input", "text": "An appropriate professional may provide information that helps parents make decisions."},
            {"title": "Predictability", "text": "The child may benefit from knowing what to expect in each household."},
        ],
        "demo_concern_a": "Communication between households feels inconsistent and important details get lost.",
        "demo_concern_b": "The child seems unsettled by different rules and expectations in each home.",
    },
    "communication": {
        "key": "communication",
        "title": "Communication",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "Communication",
        "description": "A practical look at how parents exchange information: frequency, tone, response time, method, and boundaries.",
        "central_question": "What communication structure would allow both parents to exchange necessary information while reducing opportunities for conflict?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, establishing a structured method for {focus} appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("frequency", "Communication Frequency", "How do you feel about the frequency of communication with the other parent?", "Both parents rated communication frequency similarly.", "adjusting how often the parents communicate", "A communication frequency that keeps both parents informed without overload."),
            T("tone", "Message Tone", "How would you rate the tone of messages exchanged with the other parent?", "Both parents rated the tone of their communication similarly.", "improving the tone of written communication", "A respectful, child-focused message tone."),
            T("response_time", "Response Time", "How satisfied are you with response times between you and the other parent?", "Both parents rated response-time expectations similarly.", "setting shared expectations for response times", "Agreed response-time expectations."),
            T("method", "Communication Method", "How well does your current communication method (text, email, app) work?", "Both parents view the current communication method similarly.", "choosing a more reliable communication method or platform", "A communication method both parents can rely on."),
            T("emergency", "Emergency Communication", "How clearly defined is your process for emergency communication?", "Both parents rated the emergency communication process similarly.", "creating clear emergency communication rules", "A clear emergency communication protocol."),
            T("child_info", "Child-Related Information", "How reliably is child-related information (school, health, activities) communicated?", "Both parents rated the flow of child-related information similarly.", "improving the flow of child-related information", "Reliable exchange of child-related information."),
            T("boundaries", "Communication Boundaries", "How respected are communication boundaries (times, topics, channels)?", "Both parents rated communication boundaries similarly.", "establishing clearer communication boundaries", "Boundaries that keep communication child-focused."),
            T("hostile_messages", "Hostile or Accusatory Messages", "How often do messages feel hostile, accusatory, or blaming?", "Both parents rated the presence of hostile messaging similarly.", "reducing hostile or accusatory messages", "Communication free of blame and accusation."),
            T("overcommunication", "Overcommunication", "How often does communication feel excessive or overwhelming?", "Both parents rated communication volume similarly.", "reducing unnecessary communication volume", "A manageable volume of communication."),
            T("undercommunication", "Failure to Communicate", "How often do important matters go uncommunicated?", "Both parents rated the reliability of important communication similarly.", "ensuring important matters are consistently communicated", "Consistent communication of important matters."),
        ],
        "options": [
            "BIFF communication approach",
            "Structured messaging guidelines",
            "Email-only communication",
            "App-based communication",
            "Emergency communication rules",
            "Agreed response windows",
            "Child-only topics agreement",
            "Professional-assisted communication",
        ],
        "needs": [
            {"title": "Structure", "text": "The child may benefit when both parents exchange information through a predictable structure."},
            {"title": "Information", "text": "Both parents may benefit from receiving the same child-related information directly."},
            {"title": "Boundaries", "text": "Clear communication boundaries may reduce opportunities for misunderstanding."},
            {"title": "Professional Input", "text": "A communication professional or mediator may help design a workable protocol."},
        ],
        "demo_concern_a": "Messages frequently turn hostile and important child information gets buried.",
        "demo_concern_b": "There are too many messages per day, and response expectations are unclear.",
    },
    "high_conflict": {
        "key": "high_conflict",
        "title": "High-Conflict Co-Parenting",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "High-Conflict Co-Parenting",
        "description": "Focuses on building a functional parenting system despite ongoing conflict — not on forcing cooperation.",
        "central_question": "What parenting structure can reduce opportunities for adult conflict while still ensuring the child's needs are met?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, creating a structure that reduces opportunities for adult conflict around {focus} appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("conflict_frequency", "Conflict Frequency", "How often do you and the other parent experience conflict?", "Both parents rated the frequency of conflict similarly.", "reducing how often conflicts occur", "Fewer conflict situations around the child."),
            T("conflict_intensity", "Conflict Intensity", "How intense are conflicts when they occur?", "Both parents rated the intensity of conflict similarly.", "reducing the intensity of conflicts", "Lower-intensity interactions between the adults."),
            T("boundaries", "Boundary Problems", "How often are parenting boundaries crossed?", "Both parents rated boundary problems similarly.", "establishing firmer parenting boundaries", "Clear boundaries that keep adult matters between adults."),
            T("repeated_disputes", "Repeated Disputes", "How often do the same disputes repeat without resolution?", "Both parents rated repeated disputes similarly.", "resolving recurring disputes once and for all", "Resolution of recurring disputes so the child is not caught in between."),
            T("decision_making", "Decision-Making", "How often does decision-making stall because of conflict?", "Both parents rated decision-making similarly.", "creating a decision-making protocol that works despite conflict", "Timely decisions about the child's needs."),
            T("transitions", "Transitions", "How often do exchanges or transitions become conflict situations?", "Both parents rated transition conflict similarly.", "making exchanges conflict-free", "Calm, predictable exchanges and transitions."),
            T("communication_triggers", "Communication Triggers", "How often does direct communication trigger conflict?", "Both parents rated communication triggers similarly.", "reducing communication that triggers conflict", "Communication structures that do not expose the child to conflict."),
            T("child_involvement", "Child Involvement in Conflict", "How often is the child drawn into adult disagreements?", "Both parents rated child involvement similarly.", "keeping the child out of adult disagreements", "Protection from being drawn into adult disagreements."),
            T("litigation_patterns", "Litigation Patterns", "How often do disputes escalate toward court or attorneys?", "Both parents rated escalation toward litigation similarly.", "reducing escalation toward court", "Resolution of disputes without repeated litigation."),
            T("disengagement", "Ability to Disengage", "How difficult is it to disengage from unproductive interactions?", "Both parents rated the ability to disengage similarly.", "building the ability to disengage from unproductive interactions", "Adults who can disengage rather than escalate."),
        ],
        "options": [
            "Parallel parenting",
            "Structured exchanges",
            "Limited communication",
            "Written communication only",
            "Specific decision protocols",
            "Parenting coordinator / facilitator",
            "Mediation",
            "Professional consultation",
            "Detailed parenting plan",
        ],
        "needs": [
            {"title": "Structure", "text": "The child may benefit from a parenting structure that reduces opportunities for adult conflict."},
            {"title": "Predictability", "text": "The child may benefit from knowing exactly what to expect, regardless of adult disagreement."},
            {"title": "Protection", "text": "The child may benefit from being shielded from adult disagreements."},
            {"title": "Professional Input", "text": "A parenting coordinator, mediator, or other professional may help design a functional system."},
        ],
        "demo_concern_a": "Every exchange turns into an argument, and the child is starting to notice.",
        "demo_concern_b": "The same disputes keep repeating and nothing ever gets resolved.",
    },
    "ipv": {
        "key": "ipv",
        "title": "IPV / Family Violence Safety",
        "report_title": "JOINT COMMUNICATION & SAFETY CONSIDERATIONS REPORT",
        "subtitle": "Communication & Safety Considerations",
        "description": "A safety-first report for situations involving intimate partner violence or family violence. Safety comes before agreement.",
        "central_question": "What parenting structure appropriately addresses safety, power imbalances, and the child's needs?",
        "shared_goal_options": [
            "The child's physical safety",
            "The child's emotional security",
            "Predictable, safe exchanges",
            "Healthy relationship with both parents where safe",
            "Reduced exposure to adult conflict",
            "Stable routines",
        ],
        "priority_statement": "Based on both parents' responses, a parenting structure that prioritizes safety around {focus} appears to be an important area for professional guidance.",
        "page_titles": IPV_PAGE_TITLES,
        "disclaimer": IPV_DISCLAIMER,
        "topics": [
            T("direct_contact_safety", "Safety of Direct Communication", "How safe do you feel during direct communication with the other parent?", "Both parents rated the safety of direct communication similarly.", "structuring safer communication", "Communication structures that protect safety."),
            T("exchange_safety", "Safety of Exchanges", "How safe do exchanges and transitions feel for you and the child?", "Both parents rated the safety of exchanges similarly.", "making exchanges safer", "Safe, neutral exchanges for the child."),
            T("boundary_violations", "Boundary Violations", "How often have agreed boundaries been violated?", "Both parents rated boundary violations similarly.", "establishing enforceable boundaries", "Boundaries that are respected and enforceable."),
            T("intimidation", "Intimidation or Threats", "How often has intimidation or threatening behavior occurred?", "Both parents rated intimidation concerns similarly.", "reducing intimidation through structure", "Freedom from intimidation in parenting interactions."),
            T("information_control", "Control of Information", "How often is child-related information withheld or used to control?", "Both parents rated information control similarly.", "ensuring child-related information flows appropriately", "Child-related information that is not used as leverage."),
            T("child_concerns", "Concerns About the Child", "How concerned are you about the child's emotional or physical wellbeing?", "Both parents rated concerns about the child similarly.", "addressing concerns about the child's wellbeing", "The child's emotional and physical wellbeing protected."),
            T("emergency_readiness", "Emergency Readiness", "How prepared do you feel to respond to an emergency involving the child?", "Both parents rated emergency readiness similarly.", "creating clear emergency protocols", "Clear emergency protocols for the child."),
            T("support_resources", "Support Resources", "How connected are you to appropriate family-violence resources or support?", "Both parents rated their connection to support resources similarly.", "connecting with appropriate family-violence resources", "Appropriate support for both the child and the safe parent."),
            T("legal_protections", "Legal Protections", "How clear are you about current legal protections or orders?", "Both parents rated clarity about legal protections similarly.", "clarifying legal protections and orders", "Clear legal protections that support safety."),
            T("professional_guidance", "Professional Guidance", "How helpful would professional guidance be in structuring communication?", "Both parents rated the value of professional guidance similarly.", "obtaining professional guidance on communication structure", "Professional guidance that accounts for safety and power imbalances."),
        ],
        "options": [
            "Third-party exchanges",
            "Neutral exchange locations",
            "Written-only communication",
            "Communication through professionals",
            "Parallel parenting",
            "Separate mediation sessions",
            "Virtual mediation",
            "Attorney-assisted communication",
            "Detailed parenting orders",
            "Emergency protocols",
            "Appropriate family-violence resources",
        ],
        "needs": [
            {"title": "Safety", "text": "The child's physical and emotional safety is the foundation for every other consideration."},
            {"title": "Reduced Direct Interaction", "text": "The child may benefit when parenting structures limit unnecessary direct adult interaction."},
            {"title": "Predictability", "text": "The child may benefit from detailed, unambiguous arrangements that leave little room for dispute."},
            {"title": "Professional Input", "text": "Professionals experienced with family violence may help design an appropriate structure."},
        ],
        "demo_concern_a": "Direct contact feels unsafe, and exchanges need a neutral location.",
        "demo_concern_b": "Written communication is preferred; clarity about current orders is needed.",
    },
    "medical": {
        "key": "medical",
        "title": "Medical Needs",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "Medical Needs",
        "description": "Aligns both parents around the child's medical care: providers, medication, appointments, and treatment plans.",
        "central_question": "What structure would ensure the child receives consistent medical care across both households?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, ensuring consistent medical care regarding {focus} appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("condition_awareness", "Understanding of Medical Needs", "How well do you understand the child's current medical needs?", "Both parents rated their understanding of the child's medical needs similarly.", "building a shared understanding of the child's medical needs", "Both parents understanding the child's medical needs."),
            T("severity_view", "View of Severity", "How significant do you consider the child's medical condition to be?", "Both parents view the severity of the child's condition similarly.", "aligning on the significance of the child's condition", "A shared understanding of how significant the condition is."),
            T("provider_access", "Healthcare Providers", "How satisfied are you with the child's current healthcare providers?", "Both parents rated the child's healthcare providers similarly.", "aligning on the child's healthcare providers", "Confidence in the child's healthcare providers."),
            T("appointments", "Appointments", "How well are medical appointments being scheduled and attended?", "Both parents rated appointment management similarly.", "improving how appointments are scheduled and attended", "Medical appointments reliably scheduled and attended."),
            T("medication", "Medication", "How concerned are you about the child's medication use?", "Both parents rated medication concerns similarly.", "aligning on the child's medication use", "Consistent implementation of the child's medication plan."),
            T("prescription_management", "Prescription Management", "How well are prescriptions managed between households?", "Both parents rated prescription management similarly.", "improving prescription management between households", "Prescriptions managed consistently across both homes."),
            T("insurance", "Insurance & Costs", "How well are insurance and medical costs being handled?", "Both parents rated the handling of insurance and costs similarly.", "clarifying insurance and medical cost responsibilities", "Clear handling of insurance and medical costs."),
            T("emergency_care", "Emergency Care", "How clear is the plan for emergency medical care?", "Both parents rated the emergency care plan similarly.", "creating a clear emergency medical plan", "A clear emergency medical plan in both households."),
            T("info_sharing", "Medical Information Sharing", "How completely is medical information shared between parents?", "Both parents rated medical information sharing similarly.", "ensuring both parents receive the same medical information", "Both parents receiving the same medical information directly."),
            T("treatment_adherence", "Treatment Plan Adherence", "How consistently is the child's treatment plan followed across households?", "Both parents rated treatment plan adherence similarly.", "improving treatment plan consistency across households", "Consistent implementation of the child's medical treatment plan."),
        ],
        "options": [
            "Joint pediatrician meeting",
            "Written medication protocol",
            "Shared patient portal access",
            "Medication log",
            "Duplicate medication at each home, if medically and legally appropriate",
            "Emergency medical plan",
            "Specialist consultation",
            "Second opinion consultation",
        ],
        "needs": [
            {"title": "Consistency", "text": "The child may benefit from consistent implementation of the medical treatment plan in both households."},
            {"title": "Information", "text": "Both parents may benefit from receiving the same medical information directly from providers."},
            {"title": "Professional Input", "text": "A pediatrician or specialist may provide information that helps parents make decisions."},
            {"title": "Preparedness", "text": "The child may benefit from both households being equally prepared for a medical emergency."},
        ],
        "demo_concern_a": "Medication is not administered the same way in both homes.",
        "demo_concern_b": "Medical information from appointments is not always shared promptly.",
    },
    "educational": {
        "key": "educational",
        "title": "Educational Needs",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "Educational Needs",
        "description": "Aligns both parents around the child's education: academics, homework, teacher communication, tutoring, and special education.",
        "central_question": "What structure would best help this child succeed academically in both homes?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, maintaining educational consistency while obtaining additional information regarding the child's academic needs appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("academic_performance", "Academic Performance", "How concerned are you about the child's current academic performance?", "Both parents rated the child's academic performance similarly.", "supporting the child's academic performance", "Consistent academic support in both homes."),
            T("attendance", "School Attendance", "How concerned are you about the child's school attendance?", "Both consider regular attendance a priority.", "supporting regular school attendance", "Regular, predictable school attendance."),
            T("homework", "Homework Structure", "How much additional structure does the child need for homework?", "Both believe the child needs additional homework structure.", "creating a consistent homework structure", "A consistent homework routine that works in both homes."),
            T("school_behavior", "Behavior at School", "How concerned are you about the child's behavior at school?", "Both parents rated the child's behavior at school similarly.", "supporting the child's behavior at school", "Consistent expectations about school behavior."),
            T("teacher_communication", "Teacher Communication", "How important is direct communication with the child's teacher?", "Both support communication with the child's teacher.", "improving communication with the child's teacher", "Both parents receiving the same information from the school."),
            T("tutoring", "Tutoring", "How urgently does the child need tutoring or additional academic support?", "Both parents view the need for tutoring similarly.", "determining whether tutoring would benefit the child", "Timely academic support if it is needed."),
            T("evaluation", "School Evaluation / Testing", "How supportive are you of a formal school evaluation or testing?", "Both parents view school evaluation or testing similarly.", "determining whether a school evaluation would help", "Information about whether additional evaluation is needed."),
            T("special_education", "Special Education (ARD/IEP)", "How relevant are special education services (ARD/IEP) for the child?", "Both parents view special education services similarly.", "exploring special education services (ARD/IEP)", "Access to appropriate services if the child qualifies."),
            T("school_counselor", "School Counselor", "How helpful would the school counselor be right now?", "Both parents view the school counselor's role similarly.", "consulting the school counselor", "Access to school-based support."),
            T("extracurricular", "Extracurricular Activities", "How important is it that the child continues extracurricular activities?", "Both want the child to continue participating.", "supporting the child's extracurricular participation", "Continued participation in activities the child enjoys."),
        ],
        "options": [
            "Joint parent-teacher conference",
            "Separate parent-teacher communications",
            "Shared school portal access",
            "Tutoring consultation",
            "ARD / IEP meeting",
            "School counselor consultation",
            "Pediatrician consultation",
            "Child therapist consultation",
            "Parenting coordinator",
            "Child-focused mediation",
            "Co-parenting mediation",
            "Structured communication protocol",
        ],
        "needs": [
            {"title": "Consistency", "text": "The child may benefit from more consistent academic expectations between households."},
            {"title": "Information", "text": "Both parents may benefit from receiving the same information directly from the school."},
            {"title": "Professional Input", "text": "A teacher, counselor, pediatrician, therapist, or other appropriate professional may provide information that helps parents make decisions."},
            {"title": "Predictability", "text": "The child may benefit from knowing what to expect academically in each household."},
        ],
        "demo_concern_a": "Difficulty completing homework between households.",
        "demo_concern_b": "Child appears overwhelmed by current academic expectations.",
    },
    "psychological": {
        "key": "psychological",
        "title": "Psychological / Behavioral",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "Psychological / Behavioral Observations",
        "description": "Compares parental observations about the child's emotional and behavioral wellbeing — without diagnosing.",
        "central_question": "What information and structure would help both parents support the child's emotional wellbeing across both homes?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, obtaining additional information about {focus} while maintaining consistent routines appears to be an important area for continued parental discussion.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("emotional_regulation", "Emotional Regulation", "How concerned are you about the child's emotional regulation?", "Both parents rated observations about emotional regulation similarly.", "supporting the child's emotional regulation", "Support for the child's emotional regulation."),
            T("behavior_changes", "Behavior Changes", "How concerned are you about recent changes in the child's behavior?", "Both parents rated recent behavior changes similarly.", "understanding recent changes in the child's behavior", "Attention to recent changes in behavior."),
            T("anxiety_stress", "Anxiety / Stress Observations", "How often have you observed behaviors you associate with anxiety or stress?", "Both parents reported similar observations they associate with anxiety or stress.", "understanding behaviors the parents associate with anxiety or stress", "Understanding of what may be driving stress-related behaviors."),
            T("school_behavior", "School Behavior", "How concerned are you about the child's behavior at school?", "Both parents rated the child's school behavior similarly.", "understanding the child's behavior at school", "Consistent responses to school behavior."),
            T("sleep", "Sleep", "How concerned are you about the child's sleep?", "Both parents rated the child's sleep similarly.", "supporting healthy sleep for the child", "Healthy, consistent sleep routines."),
            T("transitions", "Transitions Between Homes", "How does the child seem to handle transitions between households?", "Both parents rated the child's handling of transitions similarly.", "easing transitions between households for the child", "Smoother transitions between households."),
            T("therapy", "Therapy / Counseling", "How supportive are you of therapy or counseling for the child?", "Both parents view therapy or counseling similarly.", "determining whether therapy or counseling would benefit the child", "Access to appropriate support if needed."),
            T("medication", "Medication Perspectives", "How comfortable are you with medication as part of any treatment?", "Both parents view medication as part of treatment similarly.", "understanding the treatment options regarding medication", "Informed, shared decisions about treatment options."),
            T("provider_communication", "Provider Communication", "How important is shared communication with the child's providers?", "Both parents view provider communication similarly.", "sharing communication with the child's providers", "Both parents receiving the same information from providers."),
            T("routines", "Consistency of Routines", "How important are consistent routines for the child's wellbeing?", "Both parents view consistent routines similarly.", "aligning routines across households", "Consistent, calming routines in both homes."),
        ],
        "options": [
            "Pediatrician consultation",
            "Mental health professional consultation",
            "School counselor consultation",
            "Parent consultation with a child specialist",
            "Shared provider information",
            "Consistent routines across households",
            "Follow-up assessment by an appropriate professional",
        ],
        "needs": [
            {"title": "Observation, Not Diagnosis", "text": "One or both parents reported observing behaviors they associate with anxiety or stress. Only an appropriate professional can evaluate what these observations mean."},
            {"title": "Consistency", "text": "The child may benefit from consistent, calming routines between households."},
            {"title": "Professional Input", "text": "A pediatrician, mental health professional, or school counselor may provide information that helps parents make decisions."},
            {"title": "Information", "text": "Both parents may benefit from receiving the same information directly from any provider involved with the child."},
        ],
        "demo_concern_a": "The child has trouble settling down after transitions between homes.",
        "demo_concern_b": "Observed behaviors that seem like worry or stress before school days.",
    },
    "court": {
        "key": "court",
        "title": "Preparing for Court / Parenting Structure",
        "report_title": "JOINT ALIGNMENT REPORT",
        "subtitle": "Parenting Structure Preparation",
        "description": "Turns parenting-plan issues into a mediation roadmap: agreed terms, terms close to agreement, and terms requiring discussion.",
        "central_question": "Which parenting terms are already agreed, which are close, and which need structured discussion?",
        "shared_goal_options": SHARED_GOALS_BASE,
        "priority_statement": "Based on both parents' responses, {focus} appears to be an important area for structured discussion before or during the legal process.",
        "page_titles": STANDARD_PAGE_TITLES,
        "disclaimer": STANDARD_DISCLAIMER,
        "topics": [
            T("schedule", "Parenting Schedule", "How confident are you in your preferred parenting schedule?", "Both parents expressed similar parenting schedule preferences.", "aligning on a parenting schedule", "A parenting schedule the child can rely on."),
            T("decision_making", "Decision-Making", "How clear are you on how major decisions should be allocated?", "Both parents expressed similar views on decision-making.", "aligning on decision-making allocation", "Clear allocation of major decisions."),
            T("school", "School", "How clear are your preferences regarding school choice and involvement?", "Both parents expressed similar school-related preferences.", "aligning on school-related terms", "Stability in the child's schooling."),
            T("medical", "Medical", "How clear are your preferences regarding medical decision-making?", "Both parents expressed similar medical decision-making preferences.", "aligning on medical decision-making terms", "Clear medical decision-making for the child."),
            T("activities", "Activities", "How clear are your preferences about the child's activities?", "Both parents expressed similar activity preferences.", "aligning on activity-related terms", "Continuity in the child's activities."),
            T("transportation", "Transportation", "How clear are you on transportation responsibilities?", "Both parents expressed similar transportation preferences.", "aligning on transportation responsibilities", "Reliable transportation arrangements."),
            T("holidays", "Holidays & Special Days", "How clear are your preferences for holidays and special days?", "Both parents expressed similar holiday preferences.", "aligning on holiday schedules", "Predictable holidays and special days for the child."),
            T("travel", "Travel", "How clear are your preferences about travel with the child?", "Both parents expressed similar travel preferences.", "aligning on travel terms", "Clear expectations around travel."),
            T("communication", "Parent Communication", "How clear are you on parent-to-parent communication expectations?", "Both parents expressed similar communication expectations.", "aligning on communication expectations", "Reliable communication about the child."),
            T("dispute_resolution", "Dispute Resolution", "How clear are you on how future disputes should be resolved?", "Both parents expressed similar dispute-resolution preferences.", "aligning on a dispute-resolution process", "A way to resolve future disputes without repeated conflict."),
        ],
        "options": [
            "Child-focused mediation",
            "Parenting coordinator / facilitator",
            "Collaborative law consultation",
            "Detailed parenting plan drafting",
            "Professional consultation on disputed terms",
            "Settlement conference",
            "Structured negotiation through attorneys",
        ],
        "needs": [
            {"title": "Clarity", "text": "The child may benefit from clear, specific parenting terms that leave little room for dispute."},
            {"title": "Predictability", "text": "The child may benefit from knowing the schedule and expectations well in advance."},
            {"title": "Information", "text": "Terms that are close to agreement may settle quickly once both parents have the same information."},
            {"title": "Professional Input", "text": "A mediator or attorney may help convert areas of alignment into durable agreements."},
        ],
        "demo_concern_a": "Want a week-on/week-off schedule with clear holiday rotation.",
        "demo_concern_b": "Prefer the current schedule with adjustments for summer and travel.",
    },
}

ORDERED_TYPE_KEYS = ["general", "communication", "high_conflict", "ipv", "medical", "educational", "psychological", "court"]

_DEMO_A_PATTERN = [3, 1, 2, 0, 2, 1, 3, 2, 1, 2, 3, 0]
_DEMO_B_PATTERN = [3, 1, 1, 0, 4, 1, 3, 3, 1, 2, 4, 0]  # 4 == UNSURE index


def demo_payload(type_key):
    cfg = ASSESSMENT_TYPES[type_key]
    topics = cfg["topics"]
    a_answers, b_answers = {}, {}
    for i, t in enumerate(topics):
        a_answers[t["key"]] = SCALE[_DEMO_A_PATTERN[i % len(_DEMO_A_PATTERN)]]
        b_answers[t["key"]] = SCALE[_DEMO_B_PATTERN[i % len(_DEMO_B_PATTERN)]]
    goals = cfg["shared_goal_options"][:4]
    return {
        "a": {"answers": a_answers, "primary_concern": cfg["demo_concern_a"], "goals": goals},
        "b": {"answers": b_answers, "primary_concern": cfg["demo_concern_b"], "goals": goals},
        "child_name": "Alex",
        "parent_a_name": "Parent A",
        "parent_b_name": "Parent B",
    }
