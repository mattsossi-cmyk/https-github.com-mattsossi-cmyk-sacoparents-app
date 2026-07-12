"""One-off: generate a hero image for the SA Coparents flyer.

Scene: parents (mom + dad) from behind, warmly watching their child play
soccer on a bright green field. Photorealistic, cinematic, uplifting.
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/flyers/hero-soccer-parents.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Photorealistic cinematic photograph, warm golden-hour light. Composition: "
    "seen from slightly behind and above the parents. A mother and father stand "
    "close together on the sideline of a bright green grass soccer field, "
    "watching their young child (roughly 8 years old) play soccer. The parents "
    "are unified — the mother's hand rests gently on the father's arm — showing "
    "quiet partnership even though we cannot see their faces. In the middle "
    "distance, the child in a colourful soccer jersey is mid-stride kicking a "
    "ball toward a goal, other kids visible around. Soft bokeh in the "
    "background, sunlight filtering through trees, hopeful, calm, family-first "
    "atmosphere. No text, no logos, no watermarks. Landscape orientation, "
    "cinematic 16:10 aspect ratio."
)


async def main():
    api_key = os.getenv("EMERGENT_LLM_KEY")
    assert api_key, "EMERGENT_LLM_KEY missing"

    chat = LlmChat(
        api_key=api_key,
        session_id="sa-coparents-hero-soccer",
        system_message="You are a helpful image generation assistant.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(text=PROMPT)
    text, images = await chat.send_message_multimodal_response(msg)
    print("text:", (text or "")[:200])
    if not images:
        raise SystemExit("No image returned")

    img = images[0]
    print("mime:", img.get("mime_type"))
    OUT.write_bytes(base64.b64decode(img["data"]))
    print("wrote:", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    asyncio.run(main())
