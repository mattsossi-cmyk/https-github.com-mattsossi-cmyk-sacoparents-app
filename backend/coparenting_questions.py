"""SA CoParents Co-Parenting Assessment — 10-section question bank.

Mirrors the layout of the sample Co-Parenting Assessment Report
(/api/insights/coparenting-report.pdf). Each question is a 5-point Likert:
    0 = Never
    1 = Rarely
    2 = Sometimes
    3 = Often
    4 = Always

Some questions are *reverse-scored* — e.g. "Conversations with the other
parent escalate" — where a higher raw answer means WORSE co-parenting.
For reverse-scored items the scoring engine flips the value (4 - v) before
averaging.
"""
from __future__ import annotations

from typing import Any, Dict, List

RESPONSE_SCALE = [
    {"value": 0, "label": "Never"},
    {"value": 1, "label": "Rarely"},
    {"value": 2, "label": "Sometimes"},
    {"value": 3, "label": "Often"},
    {"value": 4, "label": "Always"},
]


SECTIONS: List[Dict[str, Any]] = [
    {
        "id": "s1",
        "number": 1,
        "name": "Communication & Information Sharing",
        "goal": "Ensure both parents have the information needed to care for the child.",
        "triggers_toolkit": True,  # a Fair/Needs-Improvement rating triggers the Communication Toolkit
        "questions": [
            {"id": "s1q1", "prompt": "I share important updates about our child's school, health, and behavior with the other parent."},
            {"id": "s1q2", "prompt": "I respond to the other parent's messages in a reasonable timeframe."},
            {"id": "s1q3", "prompt": "Our co-parent conversations remain respectful, even during disagreements."},
            {"id": "s1q4", "prompt": "We use a shared calendar or communication app for schedule and updates."},
            {"id": "s1q5", "prompt": "When I need to share information, I focus on facts rather than emotions."},
            {"id": "s1q6", "prompt": "I get the information I need from the other parent about our child."},
            {"id": "s1q7", "prompt": "Our conversations tip into personal conflict rather than staying focused on our child.", "reverse": True},
        ],
    },
    {
        "id": "s2",
        "number": 2,
        "name": "Pick-Up, Drop-Off & Transitions",
        "goal": "Reduce stress and create predictable exchanges.",
        "questions": [
            {"id": "s2q1", "prompt": "Exchanges between homes happen on time."},
            {"id": "s2q2", "prompt": "Exchange locations are safe and consistent."},
            {"id": "s2q3", "prompt": "My child arrives at each home with medications, homework, clothing, and needed items."},
            {"id": "s2q4", "prompt": "Transition routines help reduce my child's anxiety around exchanges."},
            {"id": "s2q5", "prompt": "We communicate about any delays before an exchange."},
            {"id": "s2q6", "prompt": "My child shows anxiety in the hours before an exchange.", "reverse": True},
            {"id": "s2q7", "prompt": "Special equipment or comfort items travel with my child between homes."},
        ],
    },
    {
        "id": "s3",
        "number": 3,
        "name": "Educational Needs",
        "goal": "Ensure both parents actively support educational success.",
        "questions": [
            {"id": "s3q1", "prompt": "Both parents receive school communications and updates."},
            {"id": "s3q2", "prompt": "Homework routines are supported in each home."},
            {"id": "s3q3", "prompt": "I attend parent-teacher conferences and school meetings."},
            {"id": "s3q4", "prompt": "When my child has an IEP, 504, or behavior plan, both parents participate in meetings."},
            {"id": "s3q5", "prompt": "Classroom accommodations are followed consistently in both homes."},
            {"id": "s3q6", "prompt": "I share teacher recommendations and progress with the other parent."},
            {"id": "s3q7", "prompt": "My child's academic goals are aligned between both homes."},
        ],
    },
    {
        "id": "s4",
        "number": 4,
        "name": "Medical & Healthcare Needs",
        "goal": "Coordinate healthcare across both homes.",
        "questions": [
            {"id": "s4q1", "prompt": "Both parents are aware of routine medical, dental, and therapy appointments."},
            {"id": "s4q2", "prompt": "Medications are administered consistently in both homes."},
            {"id": "s4q3", "prompt": "Both parents can explain the current treatment plan."},
            {"id": "s4q4", "prompt": "Emergency contacts, insurance, and health records are shared and accessible."},
            {"id": "s4q5", "prompt": "We coordinate on specialist visits and follow-up appointments."},
            {"id": "s4q6", "prompt": "When my child has a health incident, I notify the other parent promptly."},
            {"id": "s4q7", "prompt": "Medical decisions come together with both parents' input."},
        ],
    },
    {
        "id": "s5",
        "number": 5,
        "name": "Daily Routines & Home Consistency",
        "goal": "Create predictable environments that help the child thrive.",
        "questions": [
            {"id": "s5q1", "prompt": "Morning routines are predictable in my home."},
            {"id": "s5q2", "prompt": "Bedtime routines are predictable in my home."},
            {"id": "s5q3", "prompt": "Meal times and healthy eating are consistent in my home."},
            {"id": "s5q4", "prompt": "Screen-time limits are similar to the other home."},
            {"id": "s5q5", "prompt": "Behavioral expectations are similar in both homes."},
            {"id": "s5q6", "prompt": "Homework and study time are structured in my home."},
            {"id": "s5q7", "prompt": "My child knows what to expect during her time with me."},
        ],
    },
    {
        "id": "s6",
        "number": 6,
        "name": "Emotional & Behavioral Support",
        "goal": "Help the child regulate emotions and feel secure.",
        "questions": [
            {"id": "s6q1", "prompt": "I help my child recognize and name her emotions."},
            {"id": "s6q2", "prompt": "I use positive reinforcement rather than only correction."},
            {"id": "s6q3", "prompt": "I have strategies that help my child through anxiety or meltdowns."},
            {"id": "s6q4", "prompt": "Behavior expectations are clear and consistent in my home."},
            {"id": "s6q5", "prompt": "My child feels safe expressing difficult feelings to me."},
            {"id": "s6q6", "prompt": "When my child struggles socially, I know how to help her."},
            {"id": "s6q7", "prompt": "My child is developing self-esteem and independence."},
        ],
    },
    {
        "id": "s7",
        "number": 7,
        "name": "Therapy & Skill Reinforcement",
        "goal": "Reinforce therapeutic strategies in both homes when applicable.",
        "questions": [
            {"id": "s7q1", "prompt": "If my child receives therapy, I follow through on therapy homework in my home."},
            {"id": "s7q2", "prompt": "I know my child's current therapy or coaching goals."},
            {"id": "s7q3", "prompt": "I reinforce social skills, coping strategies, or communication techniques taught in therapy."},
            {"id": "s7q4", "prompt": "I communicate with therapists directly about progress and concerns."},
            {"id": "s7q5", "prompt": "Behavioral interventions or parent-coaching strategies are used consistently in my home."},
            {"id": "s7q6", "prompt": "Progress is tracked and shared with the other parent when appropriate."},
        ],
    },
    {
        "id": "s8",
        "number": 8,
        "name": "Safety & Supervision",
        "goal": "Promote the child's physical and emotional safety.",
        "questions": [
            {"id": "s8q1", "prompt": "My child is appropriately supervised in my home."},
            {"id": "s8q2", "prompt": "My child travels in safe, age-appropriate transportation."},
            {"id": "s8q3", "prompt": "Medications are stored safely and administered correctly."},
            {"id": "s8q4", "prompt": "Emergency contacts are known and available."},
            {"id": "s8q5", "prompt": "Allergies, medical alerts, and dietary needs are managed in both homes."},
            {"id": "s8q6", "prompt": "My child is safe from environmental hazards in my home."},
            {"id": "s8q7", "prompt": "My child understands basic digital and community safety."},
        ],
    },
    {
        "id": "s9",
        "number": 9,
        "name": "Social & Community Participation",
        "goal": "Help the child develop relationships and participate in meaningful activities.",
        "questions": [
            {"id": "s9q1", "prompt": "My child has meaningful friendships."},
            {"id": "s9q2", "prompt": "My child participates in sports, arts, clubs, or community activities."},
            {"id": "s9q3", "prompt": "Both parents support my child's participation across households."},
            {"id": "s9q4", "prompt": "My child attends birthday parties, playdates, and social events."},
            {"id": "s9q5", "prompt": "Family and extended-family relationships are healthy for my child."},
            {"id": "s9q6", "prompt": "My child is developing social confidence and peer skills."},
        ],
    },
    {
        "id": "s10",
        "number": 10,
        "name": "Long-Term Child Success",
        "goal": "Keep decisions focused on the child's continued growth.",
        "questions": [
            {"id": "s10q1", "prompt": "I encourage my child's independence at an age-appropriate level."},
            {"id": "s10q2", "prompt": "I help my child build problem-solving and decision-making skills."},
            {"id": "s10q3", "prompt": "My child is developing self-advocacy skills."},
            {"id": "s10q4", "prompt": "Achievements — big and small — are celebrated in my home."},
            {"id": "s10q5", "prompt": "I have a long-term vision for my child's growth and success."},
            {"id": "s10q6", "prompt": "I make decisions today with my child's future in mind."},
        ],
    },
]


def all_question_ids() -> List[str]:
    return [q["id"] for s in SECTIONS for q in s["questions"]]


def total_question_count() -> int:
    return sum(len(s["questions"]) for s in SECTIONS)


def find_question(qid: str) -> Dict[str, Any] | None:
    for s in SECTIONS:
        for q in s["questions"]:
            if q["id"] == qid:
                return q
    return None
