"""Generate the 5 Listen First narrations for the guided parent journey.

Outputs (all 44.1 kHz stereo MP3, voice `nova`, speed 1.0):
  /app/frontend/public/audio/listen-first/step-1-assess-family-situation.mp3
  /app/frontend/public/audio/listen-first/step-2-coparenting-relationship.mp3
  /app/frontend/public/audio/listen-first/step-3-child-needs.mp3
  /app/frontend/public/audio/listen-first/step-4-foundation-statement.mp3
  /app/frontend/public/audio/listen-first/step-5-prepare-mediation.mp3
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/audio/listen-first")
OUT_DIR.mkdir(parents=True, exist_ok=True)


STEPS = [
    (
        "step-1-assess-family-situation.mp3",
        "Step 1 — Assess Your Family Situation",
        (
            "Before the assessment begins, it's important to remember that every family is "
            "different. Some parents communicate well. Others are experiencing ongoing "
            "conflict, separation, or concerns about safety. This assessment isn't about "
            "assigning blame or deciding who's right or wrong. It's designed to help you "
            "identify where your family is today, so we can provide guidance that's "
            "appropriate for your situation. "
            "As you answer each question, respond honestly based on your current experience. "
            "Your answers will help identify your communication strengths, areas of concern, "
            "and the level of support that may be most helpful for you and your children. "
            "The goal of SA Coparents is simple: to help parents make child-focused "
            "decisions, improve communication when it's safe to do so, and prepare for "
            "productive conversations, mediation, or parenting agreements. By understanding "
            "your family's current situation, we can guide you toward the tools and resources "
            "that best support your child's well-being. Let's get started."
        ),
    ),
    (
        "step-2-coparenting-relationship.mp3",
        "Step 2 — Understand Your Co-Parenting Relationship",
        (
            "Understanding your co-parenting relationship is an important step toward "
            "creating a more stable and supportive environment for your child. This "
            "assessment isn't about judging you or the other parent. It's about recognizing "
            "how you currently work together, where communication is effective, and where "
            "challenges may be affecting your child's well-being. "
            "As you answer these questions, think about your day-to-day interactions, how "
            "decisions are made, how conflict is handled, and how your child experiences the "
            "relationship between both parents. Be as honest as you can. There are no right "
            "or wrong answers. "
            "Your responses will help SA Coparents provide personalized guidance, practical "
            "communication strategies, and recommendations that fit your family's "
            "circumstances. Every family has a starting point, and understanding your "
            "co-parenting relationship is the first step toward building a healthier, more "
            "child-focused parenting partnership."
        ),
    ),
    (
        "step-3-child-needs.mp3",
        "Step 3 — Identify Child Needs",
        (
            "Every parenting decision has the potential to shape your child's sense of "
            "safety, security, and well-being. This step is designed to help you focus on "
            "what your child needs most — not what has happened between the adults. While "
            "every family's circumstances are unique, children consistently benefit from "
            "feeling loved, protected, heard, and supported by the important people in their "
            "lives. "
            "As you complete this section, think about your child's emotional, physical, "
            "educational, and social needs. Consider their routines, relationships, "
            "strengths, and any challenges they may be facing during this transition. Your "
            "responses will help create a child-focused foundation that can guide future "
            "conversations, mediation, and parenting agreements. "
            "At SA Coparents, we believe the strongest parenting plans begin by understanding "
            "the unique needs of each child, and making those needs the center of every "
            "decision."
        ),
    ),
    (
        "step-4-foundation-statement.mp3",
        "Step 4 — Create Foundation Statement",
        (
            "Your Foundation Statement is the starting point for building a child-focused "
            "co-parenting relationship. Rather than focusing on past disagreements, this is "
            "your opportunity to describe the future you want for your child. Think about the "
            "values you want to share, the stability you hope to provide, and the kind of "
            "relationship you want your child to have with both parents, whenever it is safe "
            "and appropriate. "
            "As you complete this section, focus on your child's needs, your parenting goals, "
            "and the principles that will guide future decisions. This statement can become "
            "the foundation for mediation discussions and the parenting agreement you create "
            "together. "
            "At SA Coparents, we believe that when parents begin with shared goals for their "
            "child, they create a stronger pathway toward respectful communication, "
            "thoughtful problem-solving, and lasting agreements that place children's "
            "well-being first."
        ),
    ),
    (
        "step-5-prepare-mediation.mp3",
        "Step 5 — Prepare for Mediation",
        (
            "You are now preparing to bring your Foundation Statement and your parenting "
            "goals into mediation. This is where the work you've done so far turns into a "
            "concrete plan for your child's future. Mediation is most effective when parents "
            "arrive prepared, focused on the child's needs, and ready to discuss practical, "
            "workable solutions. "
            "As you complete this section, revisit the values and goals you've already "
            "identified. Think about the schedules, decisions, and communication practices "
            "that will support your child's stability. Be ready to describe what has been "
            "working, what needs to change, and where you need help from a neutral third "
            "party. "
            "At SA Coparents, we believe strong mediation begins with strong preparation. "
            "By walking in with a child-focused foundation, you give yourself the best chance "
            "of building an agreement that protects your child's well-being, honors your role "
            "as a parent, and creates a more stable future for your family."
        ),
    ),
]


async def main() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    for filename, label, script in STEPS:
        out = OUT_DIR / filename
        print(f"generating {label} -> {out.name}")
        audio_bytes = await tts.generate_speech(
            text=script,
            model="tts-1-hd",
            voice="nova",
            speed=1.0,
        )
        out.write_bytes(audio_bytes)
        print(f"  wrote {len(audio_bytes) // 1024} KB")


if __name__ == "__main__":
    asyncio.run(main())
