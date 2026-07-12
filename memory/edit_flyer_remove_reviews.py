"""Edit the back-side flyer with Gemini Nano Banana to remove the testimonials
section ("WHY PARENTS LOVE SA COPARENTS" — the 3 review cards + the "BUILT IN
SAN ANTONIO" purple block next to them).

Everything else on the flyer stays exactly the same (6-step journey, footer,
QR code band, contact strip)."""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")

SRC = Path("/app/frontend/public/flyers/sacoparents-poster-back.png")
OUT = Path("/app/frontend/public/flyers/sacoparents-poster-back-noreviews.png")

PROMPT = (
    "Edit this flyer to REMOVE the entire 'WHY PARENTS LOVE SA COPARENTS' "
    "section — that is, remove the section header 'WHY PARENTS LOVE SA "
    "COPARENTS', all three star-rating testimonial cards ('This app changed "
    "the way we communicate…', 'The step-by-step process…', 'Finally, a "
    "resource that helps parents…'), AND the purple block on the right that "
    "says 'BUILT IN SAN ANTONIO FOR FAMILIES LIKE YOURS'. Everything else "
    "must remain unchanged: keep the top 'A BETTER WAY TO CO-PARENT' header "
    "with the Alamo photograph, keep the six numbered journey icons "
    "(ASSESSMENT, CHILD GOALS, FOUNDATION STATEMENT, MEDIATION PREPARATION, "
    "PERSONALIZED REPORTS, CERTIFICATE OF COMPLETION) exactly as they are, "
    "and keep the entire teal footer strip at the bottom with the QR code, "
    "'PROFESSIONAL PARTNERS' section, 'SCAN TO LEARN MORE OR DOWNLOAD THE "
    "APP!' block, San Antonio Texas contact info, FOLLOW US icons, and the "
    "SA CoParents logo. Close the gap where the testimonials used to be so "
    "the six-step journey section flows naturally into the teal footer — no "
    "empty white space. Preserve exact colours, fonts, and layout style of "
    "the rest of the flyer. Output the full edited flyer image."
)


async def main():
    api_key = os.getenv("EMERGENT_LLM_KEY")
    assert api_key, "EMERGENT_LLM_KEY missing"

    src_bytes = SRC.read_bytes()
    src_b64 = base64.b64encode(src_bytes).decode("utf-8")

    chat = LlmChat(
        api_key=api_key,
        session_id="sa-coparents-remove-reviews",
        system_message="You are a helpful image editing assistant.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(
        text=PROMPT,
        file_contents=[ImageContent(src_b64)],
    )
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
