"""Generate the app intro narration.

Output: /app/frontend/public/intro-narration.mp3
"""
import asyncio
import os

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")


SCRIPT = (
    "Welcome to the free SA Coparents App. "
    "Conflict between parents doesn't have to define a child's future. "
    "Whether you're just beginning the separation process, preparing for "
    "mediation, or working through ongoing co-parenting challenges, the SA "
    "Coparents App helps you stay focused on what matters most — meeting your "
    "child's needs. "
    "Our guided process includes three powerful tools. "
    "Step One. Assess Your Co-Parenting Relationship. "
    "Gain insight into your current co-parenting relationship through a "
    "confidential assessment and receive practical feedback to help you move "
    "forward. "
    "Step Two. Create Your Foundation Statement. "
    "Clearly identify your child's needs, your parenting priorities, and the "
    "goals you hope to achieve. This statement becomes the foundation for "
    "developing a child-focused Co-Parenting Commitment Agreement. "
    "Step Three. Prepare for Mediation. "
    "Generate a personalized report to share with your mediator, helping ensure "
    "that discussions remain focused on your child's best interests and that "
    "any agreements reflect the future you want to create for your child. "
    "At SA Coparents, we believe that successful co-parenting isn't measured "
    "by the quality of the relationship between parents. It is measured by how "
    "well parents work to meet the needs of their children."
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
