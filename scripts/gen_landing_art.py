"""One-time landing-page artwork generation (owner 2026-10-22). Run manually; not part of the app."""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration  # noqa: E402

PROMPT = (
    "Minimal, elegant abstract illustration for a professional family-resolution platform. Two translucent flowing ribbons, "
    "one deep royal purple (#3D1A78) and one teal (#1A9E8F), start from opposite sides and gently converge and interweave into a "
    "single calm path leading toward a small warm golden-yellow circle at the center-right, suggesting a child at the center. "
    "Soft lavender-white background, subtle paper grain, generous negative space, flat vector style with soft gradients, "
    "no people, no faces, no text, no letters, no logos, no watermark. Square composition, premium editorial feel."
)


async def main(out: str) -> None:
    gen = OpenAIImageGeneration(api_key=os.environ["EMERGENT_LLM_KEY"])
    images = await gen.generate_images(prompt=PROMPT, model="gpt-image-1", number_of_images=1)
    if not images:
        raise SystemExit("no image returned")
    with open(out, "wb") as f:
        f.write(images[0])
    print("saved", out, len(images[0]), "bytes")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/app/frontend/public/align-hero-ai.png"))
