"""Generate the app intro narration.

Output: /app/frontend/public/intro-narration.mp3
"""
import asyncio
import os

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")


SCRIPT = (
    "When parents separate or divorce, it is easy for conflict to become the focus "
    "while children's needs unintentionally take a back seat. "
    "At SA Coparents, we believe every parenting decision should begin with one "
    "question: What does our child need? "
    "Regardless of your relationship with your child's other parent, our goal is to "
    "help you stay focused on your child's well-being by providing practical tools "
    "that support thoughtful, child-centered decision-making. "
    "The SA Coparents App guides you through three important steps. "
    "Step One. Assess Your Co-Parenting Relationship. "
    "Complete a confidential assessment to better understand your current co-parenting "
    "relationship from your perspective. Your personalized report identifies strengths, "
    "challenges, and opportunities for improvement. "
    "Step Two. Create Your Foundation Statement. "
    "Develop a clear statement outlining your child's needs, your parenting goals, and "
    "the concerns you believe should be addressed. This Foundation Statement serves as "
    "the starting point for creating a meaningful Co-Parenting Commitment Agreement. "
    "Step Three. Prepare for Mediation. "
    "Receive a report designed to support productive mediation by helping ensure that "
    "any parenting agreement reflects your child's needs, your long-term parenting "
    "goals, and the commitments both parents make moving forward. "
    "Our mission is simple: help parents reduce conflict, improve communication when "
    "appropriate, and create parenting agreements that place children first."
)


async def main():
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="nova",
        speed=1.0,
    )
    out = "/app/frontend/public/intro-narration.mp3"
    with open(out, "wb") as f:
        f.write(audio_bytes)
    print(f"wrote {out} ({len(audio_bytes) // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
