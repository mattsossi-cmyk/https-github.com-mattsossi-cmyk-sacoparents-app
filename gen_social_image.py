"""Generate a Facebook social image for SA Coparents using Gemini Nano Banana."""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv(Path(__file__).parent / "backend" / ".env")

OUT = Path(__file__).parent / "frontend" / "public" / "social-share.png"

PROMPT = """Create a beautiful, calm social media share image — landscape orientation,
ideal Facebook share dimensions ~1.91:1 (around 1200 x 630 pixels). Soft, painterly,
sophisticated, dignified — feels like a digital sanctuary. NOT clinical, NOT corporate.

Composition:
- Background: soft watercolor wash blending muted sage green (#849D8E), warm sand cream (#FDFAF3)
  and a hint of warm terracotta (#C28771). Gentle organic curves, like two flowing shapes
  meeting in the middle. A subtle paper-grain texture overlay.
- Foreground: an abstract, minimal silhouette suggesting two adult hands holding a small
  child's hand between them — drawn as soft, painterly brush strokes, NOT photorealistic.
  Place this gesture on the left third of the image.
- Right side: leave generous negative space for text.
- Typography (rendered as part of the image): in the upper right, in a refined serif
  similar to Cormorant Garamond, the words "SA Coparents" small and elegant.
  Below it, in a larger serif, the line: "Mediation, prepared with care."
  Underneath, in a tiny sans-serif: "Five gentle steps to a calmer co-parenting conversation."
- Overall mood: warm morning light, hopeful but quiet. Earthy, organic, restorative.
- Do NOT include any harsh edges, no logos other than the wordmark, no children's faces.
"""

async def main():
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = (
        LlmChat(
            api_key=api_key,
            session_id="sa-coparents-social-1",
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
