"""Regenerate the IPV (Intimate Partner Violence) Assessment narration.

Output: /app/frontend/public/audio/listen-first/step-ipv-assessment.mp3
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/audio/listen-first/step-ipv-assessment.mp3")

SCRIPT = (
    "Every family's situation is different. If your relationship has involved "
    "intimidation, threats, coercive control, emotional abuse, or physical "
    "violence, your safety — and your child's safety — must come first. "
    "This assessment is designed to help you reflect on your current situation "
    "and identify the safest way to communicate and make parenting decisions. "
    "There are no right or wrong answers. Simply answer honestly based on your "
    "experience. "
    "Your responses will help identify strategies that protect your well-being "
    "while supporting your child's needs. "
    "At SA Coparents, we believe every child benefits from healthy parenting — "
    "but healthy parenting always begins with safety."
)


async def main() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio = await tts.generate_speech(text=SCRIPT, model="tts-1-hd", voice="nova", speed=1.0)
    OUT.write_bytes(audio)
    print(f"wrote {OUT} ({len(audio) // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
