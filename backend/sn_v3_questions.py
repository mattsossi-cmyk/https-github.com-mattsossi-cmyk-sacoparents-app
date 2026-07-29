"""SA CoParents Special Needs 10-Principle Assessment question bank.

Mirrors the 10-principle framework used in the Special Needs sample report.
5-point Likert scale (Never/Rarely/Sometimes/Often/Always) with reverse-scored
items marked reverse=True.
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
        "id": "p1",
        "number": 1,
        "name": "Build an Individualized Parenting Plan",
        "goal": "Tailor the schedule to your child's needs rather than a generic template.",
        "questions": [
            {"id": "p1q1", "prompt": "Our parenting plan reflects my child's specific transition needs and sensory preferences."},
            {"id": "p1q2", "prompt": "Our schedule was tailored to my child's regulation patterns rather than a generic template."},
            {"id": "p1q3", "prompt": "I revisit and update the plan when my child's needs change."},
            {"id": "p1q4", "prompt": "The plan documents the supports my child needs during exchanges."},
            {"id": "p1q5", "prompt": "The plan considers therapy, school, and medical schedules."},
            {"id": "p1q6", "prompt": "The plan feels workable in daily life."},
        ],
    },
    {
        "id": "p2",
        "number": 2,
        "name": "Prioritize Consistent Routines & Predictability",
        "goal": "Keep core routines the same in both homes to reduce anxiety.",
        "questions": [
            {"id": "p2q1", "prompt": "Meal times are consistent in my home."},
            {"id": "p2q2", "prompt": "Bedtime routines are predictable."},
            {"id": "p2q3", "prompt": "Therapy schedules are honored consistently."},
            {"id": "p2q4", "prompt": "Transition routines look similar across both homes."},
            {"id": "p2q5", "prompt": "My child knows what to expect during her time with me."},
            {"id": "p2q6", "prompt": "Screen-time and behavioral expectations are similar between homes."},
        ],
    },
    {
        "id": "p3",
        "number": 3,
        "name": "Maintain Open, Child-Focused Communication",
        "goal": "Schedule dedicated, child-focused communication; log details in shared tools.",
        "triggers_toolkit": True,
        "questions": [
            {"id": "p3q1", "prompt": "I share therapy updates, medication changes, and school notes with the other parent."},
            {"id": "p3q2", "prompt": "We have dedicated time to discuss my child's progress and changes."},
            {"id": "p3q3", "prompt": "We use a shared calendar, app, or journal for important details."},
            {"id": "p3q4", "prompt": "Conversations remain focused on my child, not on our differences."},
            {"id": "p3q5", "prompt": "I respond to the other parent's messages in a reasonable timeframe."},
            {"id": "p3q6", "prompt": "Conversations with the other parent escalate into conflict.", "reverse": True},
        ],
    },
    {
        "id": "p4",
        "number": 4,
        "name": "Align on Core Expectations",
        "goal": "Agree on core rules even when parenting styles differ.",
        "questions": [
            {"id": "p4q1", "prompt": "Medication schedules are aligned between homes."},
            {"id": "p4q2", "prompt": "Therapy participation is supported in both homes."},
            {"id": "p4q3", "prompt": "Screen-time limits are similar in both homes."},
            {"id": "p4q4", "prompt": "Behavioral rules and consequences are consistent."},
            {"id": "p4q5", "prompt": "Bedtime and morning routines are aligned."},
            {"id": "p4q6", "prompt": "We agree on core discipline approaches for meltdowns and behavioral events."},
        ],
    },
    {
        "id": "p5",
        "number": 5,
        "name": "Understand & Share Your Child's Diagnosis and Needs",
        "goal": "Build shared knowledge of the diagnosis and its daily impact.",
        "questions": [
            {"id": "p5q1", "prompt": "I understand my child's diagnosis (e.g. autism, ADHD, sensory processing)."},
            {"id": "p5q2", "prompt": "I understand how the diagnosis affects daily life."},
            {"id": "p5q3", "prompt": "I share diagnosis-related updates with the other parent."},
            {"id": "p5q4", "prompt": "Both parents understand my child's support needs."},
            {"id": "p5q5", "prompt": "I proactively seek information about my child's condition."},
            {"id": "p5q6", "prompt": "Providers and teachers know my child's diagnosis."},
        ],
    },
    {
        "id": "p6",
        "number": 6,
        "name": "Coordinate Education & Therapy",
        "goal": "Work together on IEP/504 plans, school placement, and therapy carryover.",
        "questions": [
            {"id": "p6q1", "prompt": "Both parents participate in IEP/ARD or 504 meetings."},
            {"id": "p6q2", "prompt": "Classroom accommodations are followed in both homes."},
            {"id": "p6q3", "prompt": "I reinforce therapy homework (OT/speech/behavioral) at home."},
            {"id": "p6q4", "prompt": "Visual schedules and sensory-friendly spaces are used at home."},
            {"id": "p6q5", "prompt": "School communications reach both parents."},
            {"id": "p6q6", "prompt": "Therapist recommendations are followed at home."},
        ],
    },
    {
        "id": "p7",
        "number": 7,
        "name": "Manage Transitions Smoothly",
        "goal": "Plan exchanges to minimize sensory and emotional stress.",
        "questions": [
            {"id": "p7q1", "prompt": "Exchange locations are sensory-friendly."},
            {"id": "p7q2", "prompt": "Transportation between homes is calm and predictable."},
            {"id": "p7q3", "prompt": "Comfort items and sensory supports travel with my child."},
            {"id": "p7q4", "prompt": "I use transition warnings and visual schedules before exchanges."},
            {"id": "p7q5", "prompt": "My child shows anxiety before exchanges.", "reverse": True},
            {"id": "p7q6", "prompt": "Exchanges happen on time and without conflict."},
        ],
    },
    {
        "id": "p8",
        "number": 8,
        "name": "Be Flexible and Adaptable",
        "goal": "Adjust the plan as the child's needs, abilities, and preferences evolve.",
        "questions": [
            {"id": "p8q1", "prompt": "I adjust routines as my child's needs evolve."},
            {"id": "p8q2", "prompt": "I revisit the plan after major changes (new school, medication, growth phase)."},
            {"id": "p8q3", "prompt": "I remain calm when things change unexpectedly."},
            {"id": "p8q4", "prompt": "I recognize when my child's coping strategies need to change."},
            {"id": "p8q5", "prompt": "I welcome input from teachers, therapists, and specialists on adjusting the plan."},
            {"id": "p8q6", "prompt": "I am open to trying new approaches when current ones stop working."},
        ],
    },
    {
        "id": "p9",
        "number": 9,
        "name": "Build a Support Network",
        "goal": "Engage therapists, educators, and other professionals as partners.",
        "questions": [
            {"id": "p9q1", "prompt": "My child's therapists and educators are actively engaged."},
            {"id": "p9q2", "prompt": "I have access to a special-needs-experienced attorney or mediator if needed."},
            {"id": "p9q3", "prompt": "I connect with other parents in similar situations."},
            {"id": "p9q4", "prompt": "I use community resources (support groups, respite care, advocacy orgs)."},
            {"id": "p9q5", "prompt": "I have professionals I can consult when I'm stuck."},
            {"id": "p9q6", "prompt": "I ask for help when I need it."},
        ],
    },
    {
        "id": "p10",
        "number": 10,
        "name": "Practice Compassion and Patience",
        "goal": "Approach disagreements with empathy; keep the child at the center.",
        "questions": [
            {"id": "p10q1", "prompt": "I approach disagreements with the other parent with empathy."},
            {"id": "p10q2", "prompt": "I model self-regulation for my child."},
            {"id": "p10q3", "prompt": "I focus on solutions rather than blame."},
            {"id": "p10q4", "prompt": "I recognize my own limits and take care of myself."},
            {"id": "p10q5", "prompt": "I speak respectfully about the other parent in my child's presence."},
            {"id": "p10q6", "prompt": "I remember that my child's needs come first, even during hard moments."},
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
