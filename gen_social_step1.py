"""Generate a 1080x1080 'Step 1' social media image for SA Coparents."""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv(Path(__file__).parent / "backend" / ".env")

OUT = Path(__file__).parent / "frontend" / "public" / "social-step1.jpg"

PROMPT = """Create a beautiful, calm SQUARE social media image — 1:1 aspect ratio,
1080 x 1080 pixels. Soft, painterly, sophisticated, dignified — a digital sanctuary feel.
NOT clinical, NOT corporate. The audience is San Antonio coparents preparing for mediation.

Composition (vertical, centered):
- Background: soft watercolor wash blending muted sage green (#849D8E), warm sand cream
  (#FDFAF3) and a hint of warm terracotta (#C28771). Gentle organic curves like two flowing
  shapes meeting in the middle. Subtle paper-grain texture overlay.
- Top-center: a small circular numeral badge with the number "1" inside a soft sage circle,
  painted in painterly brushwork. Above the circle a tiny letterspaced label STEP.
- Middle area: a minimal painterly illustration evoking a parent's protective hand
  cupping around a small symbolic child — could be rendered as a softly stylized heart
  shape formed by the hand and the child's silhouette together. NOT photorealistic.
- Lower half: generous negative space for the wordmark and copy.
- Typography rendered as part of the image, centered. Exact words and order — spell
  every word carefully:
    Line A (small uppercase letterspaced, soft sage tone): SAN ANTONIO COPARENTS
    Line B (large elegant serif headline, Cormorant Garamond style, dark charcoal,
            on two lines, centered, with elegant spacing):
            Step 1 — Create Your
            Coparenting Agreement
    Line C (medium serif italic in sage tone): Define your child-centered goals.
    Line D (tiny clean sans-serif, soft gray): A calm first step toward mediation.
- Mood: warm morning light, hopeful but quiet. Earthy, organic, restorative.
- Do NOT include children's faces, photorealistic people, harsh edges, UI mockups,
  phone illustrations, or any other logos or watermarks.
- Spell every word exactly as written above. No extra text.
"""

async def main():
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = (
        LlmChat(
            api_key=api_key,
            session_id="sa-coparents-social-step1",
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
