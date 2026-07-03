"""One-off script: generate the app intro narration.

Output: /app/frontend/public/intro-narration.mp3
"""
import asyncio
import os

from dotenv import load_dotenv

from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

SCRIPT = (
    "Welcome to our free SA Coparents App. "
    "In divorce and separation, kids' needs can get lost in the equation as their parents' "
    "conflict takes center stage. "
    "For us, helping parents meet those needs means helping parents meet their kids' needs, "
    "regardless of the quality of the relationship they share with their child's other parent — "
    "you know, your ex. "
    "To meet this challenge, the SA Coparents App provides you with three important resources. "
    "First, we help you assess your co-parenting relationship with your child's other parent "
    "from your perspective. "
    "Second, we help you create a Foundation Statement to clearly state the goals, concerns, "
    "and needs of your child. It is the Foundation Statement that we intend to use to create "
    "a Co-Parenting Commitment Agreement. "
    "Lastly, the app provides you a report we'd like you to take to your mediator, to ensure "
    "that your agreement matches the future goals you have envisioned for your children, as "
    "well as ensuring that your children's needs and concerns are met."
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
