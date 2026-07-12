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
    "seen from behind. A mother and a father stand on the sideline of a bright "
    "green grass soccer field, watching their young child (roughly 8 years old) "
    "play soccer. IMPORTANT: the two parents are clearly APART from each other "
    "— they are separated by a visible gap of empty grass between them, "
    "standing several feet apart, not touching, not looking at each other. "
    "Each parent is a lone silhouette, arms crossed or hands in pockets, "
    "individually focused on the child. Their body language shows they are "
    "co-parents who came separately — polite distance, no interaction between "
    "them. The mother is on the left, wearing a navy sweater and jeans. The "
    "father is on the right, wearing a plaid shirt and dark pants. Between "
    "them, in the middle distance on the field, their child in a colourful "
    "soccer jersey (number 8) is mid-stride kicking a ball. Other kids and a "
    "goal net in the background. Soft bokeh, hopeful light, quiet dignity, "
    "no bitterness — just distance. No text, no logos, no watermarks. "
    "Landscape orientation, cinematic 16:10 aspect ratio."
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
