"""One-off script: generate the app intro narration.

Output: /app/frontend/public/intro-narration.mp3
"""
import asyncio
import os

from dotenv import load_dotenv

from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

SCRIPT = (
    "No matter what your co-parenting situation looks like, one thing remains the same: "
    "your child's needs come first. "
    "The SA CoParenting App is designed to help parents stay focused on what matters most—"
    "the well-being of their child—through three powerful reports. "
    "First, you'll receive a Co-Parenting Assessment that evaluates the quality of your "
    "co-parenting relationship and provides practical recommendations to help you better "
    "meet your child's needs and achieve your parenting goals. "
    "Second, the app helps you create a Co-Parenting Agreement Draft by identifying the "
    "goals, interests, and concerns that both parents have for their child. "
    "This creates a foundation for productive discussions and collaborative decision-making. "
    "Third, you'll receive a Child Needs Statement that summarizes your child's most important "
    "needs and priorities. This report can be brought to mediation to help ensure that any "
    "agreements reached align with the goals and needs you have identified for your child. "
    "The SA CoParenting App—helping parents create child-centered solutions, one step at a time."
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
