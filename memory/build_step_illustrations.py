"""Generate 7 watercolor step-illustration images via Gemini Nano Banana.

Each image is saved as PNG to /app/frontend/public/images/steps/. They are
also used as the backdrop for the corresponding reflection video via
build_step_videos_from_images.py.

Style: warm watercolor + purple/teal SA Coparents palette, matching the
Dashboard collage aesthetic. Hand-painted feel, no photorealism, no clinical
imagery, editorial and dignified.
"""
from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage


load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/images/steps")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAND_STYLE = (
    "watercolor illustration in the SA Coparents brand palette of deep purple "
    "(#3D1A78) blending into soft teal (#2DB5B5), with warm cream (#F8F6EE) "
    "accents. hand-painted watercolor style with visible brush strokes, soft "
    "washes, and gentle grain — editorial, dignified, calm, and warm. NO "
    "photorealism, NO clinical or corporate imagery. Portrait 1080x1350 aspect "
    "ratio (4:5). Leave the bottom third of the composition slightly quieter so "
    "text can be overlaid comfortably. Diverse, non-stereotyped, faceless-or-"
    "gentle silhouettes preferred — the vibe is human, not literal."
)

PROMPTS = [
    (
        "step-safety-assessment.png",
        "A calm watercolor scene of a mother and her child sitting close on a "
        "sofa with a soft blanket, a warm lamp glowing beside them, symbolizing "
        "safety and shelter. In the distance a soft light through a window. "
        "This image supports a reflection about family safety and honest "
        "self-assessment. No violent imagery.",
    ),
    (
        "step-comm-style.png",
        "A watercolor scene of two parents sitting on opposite sides of a small "
        "round wooden table, leaning in slightly, listening — no yelling, no "
        "tension — with warm tea between them. Their posture suggests careful "
        "conversation. In the background, soft brushstrokes suggest a home in "
        "transition. About co-parenting communication.",
    ),
    (
        "step-child-goals.png",
        "A watercolor of a single child (age uncertain, gender ambiguous) "
        "standing in a warm meadow at sunrise, holding a small kite or a paper "
        "boat, gazing forward with quiet hope. A soft rainbow wash of purples "
        "and teals suggests possibility. About focusing on the child's future "
        "needs.",
    ),
    (
        "step-issues.png",
        "A watercolor of soft floating clouds and tangled ribbons of purple and "
        "teal being gently un-knotted by a pair of open hands. Symbolic of "
        "naming and untangling unresolved issues in a co-parenting "
        "relationship. No text, no words in the image.",
    ),
    (
        "step-priority.png",
        "A watercolor of three small hand-painted stones stacked carefully on "
        "top of each other on a wooden ledge, each stone painted a different "
        "shade of purple and teal, with soft grass at the base. Symbolic of "
        "ranking priorities gently, one on top of the other. Balanced, "
        "meditative composition.",
    ),
    (
        "step-foundation.png",
        "A watercolor of two hands, one adult and one child-sized, gently "
        "placing a small seedling in warm earth. Golden sunlight from the "
        "upper left. Symbolic of building a Foundation Statement for a child's "
        "future — the beginning of something that will grow.",
    ),
    (
        "step-readiness.png",
        "A watercolor of a warm-lit doorway seen from inside a cozy home, with "
        "morning light streaming in and a soft path leading forward through a "
        "peaceful landscape. Symbolic of preparing to walk into mediation with "
        "clarity. No people needed. Feels like a threshold.",
    ),
]


async def main() -> None:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    for filename, subject in PROMPTS:
        out = OUT_DIR / filename
        chat = LlmChat(
            api_key=api_key,
            session_id=f"sacoparents-illust-{filename}",
            system_message="You are an assistant that generates watercolor illustrations for a co-parenting app.",
        )
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        prompt = f"Create an illustration. Subject: {subject}\n\nStyle: {BRAND_STYLE}"
        msg = UserMessage(text=prompt)
        try:
            _text, images = await chat.send_message_multimodal_response(msg)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {filename}: {e}")
            continue
        if not images:
            print(f"NO IMAGE returned for {filename}")
            continue
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        out.write_bytes(image_bytes)
        print(f"wrote {out.name} ({len(image_bytes) // 1024} KB, {img.get('mime_type')})")


if __name__ == "__main__":
    asyncio.run(main())
