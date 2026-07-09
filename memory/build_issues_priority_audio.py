"""Generate Issues & Priority narrations for the guided journey."""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/audio/listen-first")
OUT.mkdir(parents=True, exist_ok=True)

SCRIPTS = [
    (
        "step-issues.mp3",
        (
            "Every co-parenting relationship has areas that feel unresolved. Some are "
            "practical — schedules, holidays, expenses. Others are deeper — trust, "
            "communication, safety, or how decisions get made. "
            "This step is not about assigning blame. It is about naming what is "
            "unresolved, so it can be brought to mediation clearly instead of coming "
            "out sideways later. "
            "As you list your concerns, be honest and specific. Focus on your child's "
            "experience whenever you can. Concerns that begin with 'my child needs' "
            "are almost always the ones that lead to better parenting agreements. "
            "At SA Coparents, we believe naming the real issues, gently and clearly, "
            "is the first step toward solving them."
        ),
    ),
    (
        "step-priority.mp3",
        (
            "Not every concern carries the same weight. Some can wait. Others cannot. "
            "This step helps you separate what is urgent from what is important, and "
            "what is important from what is merely frustrating. Ranking your "
            "priorities does not mean giving up on the smaller ones. It means walking "
            "into mediation with clarity about which battles are worth having, and "
            "which are best set aside for later. "
            "Think about safety first, then stability, then routine. Trust yourself. "
            "You know your child. You know what they need most. "
            "When your priorities are clear, your co-parenting agreement gets stronger, "
            "and your child gets a calmer, more predictable home."
        ),
    ),
]


async def main() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    for filename, script in SCRIPTS:
        audio = await tts.generate_speech(text=script, model="tts-1-hd", voice="shimmer", speed=1.0)
        (OUT / filename).write_bytes(audio)
        print(f"wrote {filename} ({len(audio) // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
