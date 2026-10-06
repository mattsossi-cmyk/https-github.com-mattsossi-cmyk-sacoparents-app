"""Section-by-section walk-through for the Professional Alignment Report (editor tips + PDF 'How to read this report' page)."""

WALKTHROUGH = [
    ("Case & Assessment Overview", "Who, what and which assessments were reviewed.", "Identify the matter, the parents, the professional and the sources considered. Tick only assessments you actually reviewed.",
     "No opinions here — facts of the engagement only."),
    ("Alignment Snapshot & Safety Screening", "Where each parent and the co-parenting dynamic sit on the 1–10 scale, and whether a joint process is safe.",
     "Rate Parent A, Parent B and Joint on the 1–10 continuum. Record the risk screening and state whether a joint process is appropriate. Safety findings override ordinary recommendations.",
     "Scores describe co-parenting behaviour, never fitness or credibility. No diagnosis."),
    ("Parent A Perspective", "Parent A's account, summarised neutrally with successes, challenges and growth priorities.",
     "Summarise what Parent A reported (Successes / Challenges / Growth Priorities). Use 'Parent A describes…'. Raw answers stay private.",
     "No credibility findings; do not declare either account correct."),
    ("Parent B Perspective", "Parent B's account, summarised the same way.", "Mirror the structure used for Parent A so the report is even-handed.", "Same neutrality rules as Parent A."),
    ("Joint Co-Parenting Assessment", "What the parents agree on, where they differ, and issues needing attention.",
     "Areas of alignment, areas of difference, partial alignment and shared concerns. Note issues that need discussion or professional attention.",
     "Describe differences as perspectives, not facts."),
    ("Child-Focused Legal Issues", "How the differences affect the child's day-to-day needs.", "Tick the categories that affect the child and write the concern and a potential focus for each.",
     "Child's needs, not parents' grievances. No custody or possession recommendation."),
    ("Options & Resources", "Neutral services and referrals that may help.", "Select resources from the directory; state the purpose of each.", "Resources are options, not orders."),
    ("Conflict Resolution Pathways", "The step-by-step process suggested for resolving disputes.", "Select pathways and explain why they fit the identified issues; the Safety Override applies when indicators exist.",
     "Pathways are procedural suggestions, not legal conclusions."),
    ("Legal Conflict & Agreement-Building Analysis", "Where agreement is realistic and what still needs resolution.",
     "List areas potentially capable of agreement, issues requiring further resolution, existing agreements/orders noted and procedural considerations.",
     "Do not predict court outcomes."),
    ("Professional Legal Statement & Roadmap", "The professional's own observation and the 30–90 day / 6–12 month plan.",
     "Write your observation in your own voice, then goals, success indicators, long-term goals and reassessment triggers.",
     "Clearly your judgment — distinct from parent-reported and AI/system text."),
    ("Concise Court Summary", "A short, neutral summary the court can read in a minute.", "Levels for A, B and Joint plus 3–6 neutral sentences. Then review the PDF, finalize and certify.",
     "Neutral and procedural: no recommendations, diagnoses or legal conclusions."),
]

SIX_QUESTIONS = [
    ("What did each parent report?", [3, 4]), ("Where are they aligned?", [2, 5]), ("Where do their perspectives differ?", [5]),
    ("What child-focused issues need attention?", [6]), ("What options and resources are available?", [7]), ("What conflict-resolution pathway could be considered?", [8]),
]
QUESTION_OF_SECTION = {1: "Case record", 2: "Q2 · Where are they aligned?", 3: "Q1 · What did each parent report?", 4: "Q1 · What did each parent report?",
                       5: "Q2 & Q3 · Where are they aligned — and where do their perspectives differ?", 6: "Q4 · What child-focused issues need attention?",
                       7: "Q5 · What options and resources are available?", 8: "Q6 · What conflict-resolution pathway could be considered?",
                       9: "Professional Statement · agreement-building analysis", 10: "Professional Statement · the professional's own observation", 11: "Professional Statement · court summary"}
SOURCE_OF_SECTION = {1: "professional", 2: "system", 3: "parent", 4: "parent", 5: "system", 6: "professional", 7: "professional", 8: "professional", 9: "professional", 10: "professional", 11: "professional"}
SOURCE_LEGEND = [
    ("parent", "Parent-reported information", "What a parent said about their own experience, summarised neutrally. Not verified, not a finding."),
    ("system", "System-generated comparison", "Align lines up the two accounts side by side. It shows alignment and difference; it does not decide who is right."),
    ("ai", "AI-assisted draft", "Wording first drafted by an AI aid at the professional's request, then reviewed and owned by the professional."),
    ("professional", "Professional observation", "The professional's own observation, analysis and plan — the only opinion in this report."),
]
DISTINCTIONS = [
    ("Assessment", "finding", "A self-assessment records what a parent reports. It does not establish what happened."),
    ("Difference in perspective", "fact determination", "Two accounts can differ without either being false. This report does not resolve which is accurate."),
    ("AI summary", "professional opinion", "AI drafts only organise wording. Every judgment in this report is the professional's, after review."),
    ("Professional report", "court determination", "This report informs; it does not recommend custody, assess credibility, diagnose, or decide."),
]
WORKFLOW = [("Invite", "The professional opens the case and invites each parent privately."), ("Assess", "Each parent completes their own assessment; neither sees the other's answers."),
            ("Align", "Align lines up the two perspectives: shared ground, differences, child-focused issues."), ("Review", "The professional reviews, edits and certifies — nothing is automatic."),
            ("Respond", "Options, resources and a pathway — released only to authorised recipients.")]

READER_INTRO = ("This report organizes information from two parents' separate assessments, safety screenings and a system-generated Joint Report, reviewed by an authorized professional. "
                "It is designed to help the court and professionals understand where the parents align, where they differ, and what neutral options may help the child. "
                "It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.")

SCALE_NOTE = ("The 1–10 Co-Parenting Continuum: 1–3 Crisis / High Conflict (safety-first, structured, minimal direct contact) · 4–6 Restricted or Business-Like (structured, task-focused) · "
              "7–10 Cooperative to Unified (flexible, collaborative). Scores describe the current co-parenting context and are expected to change with reassessment.")
