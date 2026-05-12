"""Generate a 1080x1080 square Instagram-friendly social image."""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv(Path(__file__).parent / "backend" / ".env")

OUT = Path(__file__).parent / "frontend" / "public" / "social-square.jpg"

PROMPT = """Create a beautiful, calm SQUARE social media image — 1:1 aspect ratio, ideal
for an Instagram or Facebook square post (around 1080 x 1080 pixels). Soft, painterly,
sophisticated, dignified — feels like a digital sanctuary. NOT clinical, NOT corporate.

Composition (vertical stack, centered):
- Background: soft watercolor wash blending muted sage green (#849D8E), warm sand cream
  (#FDFAF3) and a hint of warm terracotta (#C28771). Gentle organic curves like two flowing
  shapes meeting in the middle. Subtle paper-grain texture overlay throughout.
- Upper half (centered): a minimal, painterly illustration of two adult hands gently
  holding a small child's hand between them — abstract brush strokes, NOT photorealistic,
  no faces, no full bodies. The gesture should sit in the upper-center area.
- Lower half: generous negative space for the wordmark and tagline.
- Typography rendered as part of the image, centered. Exact words and order — spell carefully:
    Line 1 (small uppercase letterspaced, soft sage tone): SA COPARENTS
    Line 2 (large elegant serif, Cormorant Garamond style, dark charcoal,
            on two lines, centered):
            Creating Your
            Coparenting Agreement
    Line 3 (tiny clean sans-serif, soft gray): A calm, child-centered way to prepare.
- Overall mood: warm morning light, hopeful but quiet. Earthy, organic, restorative.
- Do NOT include harsh edges, no logos other than the wordmark, no children's faces,
  no UI mockups, no phone illustrations.
- Spell every word exactly as written above. No extra text, no other words.
"""

async def main():
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = (
        LlmChat(
            api_key=api_key,
            session_id="sa-coparents-social-square-1",
            system_message="You are an expert calm-aesthetic illustrator.",
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )
    text, images = await chat.send_message_multimodal_response(UserMessage(text=PROMPT))
    print("Text response:", (text or "")[:160])
    if not images:
        print("No images returned.")
        return
    img = images[0]
    print("Mime:", img.get("mime_type"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(base64.b64decode(img["data"]))
    print(f"Saved -> {OUT}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
