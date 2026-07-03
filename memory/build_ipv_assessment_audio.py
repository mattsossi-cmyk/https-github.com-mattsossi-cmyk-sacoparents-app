"""Generate the IPV Assessment 'Listen First' narration.

Outputs: /app/frontend/public/audio/listen-first/step-ipv-assessment.mp3

This narration is used on the /safety-assessment page (the IPV Communication
Safety Assessment). It replaces the earlier 'Assess Your Family Situation'
narration on that page.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/audio/listen-first/step-ipv-assessment.mp3")

SCRIPT = (
    "When in Need, Use Our SA Coparents Family Violence Assessment. "
    "Not every parenting situation is the same, and before discussing communication "
    "or co-parenting, it's important to understand whether safety concerns exist. "
    "This confidential assessment helps identify signs of family violence, coercive "
    "control, intimidation, harassment, or other behaviors that may affect parenting "
    "decisions and communication. "
    "Your responses will help determine the safest and most appropriate pathway for "
    "your family. If concerns are identified, the focus will be on protecting you and "
    "your children while exploring child-focused options for communication, parenting, "
    "and future decision-making. "
    "At SA Coparents, we believe every child deserves a safe environment, and every "
    "parenting plan should begin with safety first."
)


async def main() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="nova",
        speed=1.0,
    )
    OUT.write_bytes(audio_bytes)
    print(f"wrote {OUT} ({len(audio_bytes) // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
