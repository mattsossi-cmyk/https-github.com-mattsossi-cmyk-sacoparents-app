"""Generate the app intro narration.

Output: /app/frontend/public/intro-narration.mp3
"""
import asyncio
import os

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")


SCRIPT = (
    "Welcome to the SA CoParents App. "
    "No matter where you are in your co-parenting journey, one thing remains "
    "the same — your child deserves to feel safe, loved, and supported. "
    "This app is designed to help you take the next step toward healthier "
    "co-parenting by guiding you through a simple, child-focused process. "
    "You'll assess your current parenting relationship, identify your child's "
    "goals and needs, create a personalized Foundation Statement, and prepare "
    "for productive mediation or constructive conversations with your child's "
    "other parent. "
    "Along the way, you'll receive practical tools, personalized reports, and "
    "thoughtful guidance to help reduce conflict, improve communication, and "
    "keep your focus where it matters most — on your child's future. "
    "Let's get started together."
)


async def main():
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="shimmer",
        speed=1.0,
    )
    out = "/app/frontend/public/intro-narration.mp3"
    with open(out, "wb") as f:
        f.write(audio_bytes)
    print(f"wrote {out} ({len(audio_bytes) // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
