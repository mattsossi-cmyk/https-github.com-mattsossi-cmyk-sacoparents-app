import asyncio, os, base64
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from PIL import Image

STYLE = ("Flat vector illustration, clean modern style, soft white background, brand palette of deep purple #5B2A86, teal #1f8a8a, warm gold accents and gentle greens. "
         "Faces simple and friendly, no text, no logos, landscape 3:2 composition. Keep the same character design (a man in a mustard shirt and a woman in a purple top) as the reference image.")
SCENE = ("Pediatric check-up: the child sits on the exam table in the CENTER. The friendly doctor with a stethoscope stands on the LEFT side of the table. BOTH parents stand together "
         "on the RIGHT side of the table, opposite the doctor, side by side, listening attentively — the parents are clearly on the same side, facing the doctor across the table.")


async def main():
    ref = base64.b64encode(open("/app/frontend/public/moment-doctor.jpg", "rb").read()).decode()
    chat = LlmChat(api_key=os.getenv("EMERGENT_LLM_KEY"), session_id="scene-doctor-v2", system_message="You are an illustrator.").with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    _, images = await chat.send_message_multimodal_response(UserMessage(text=f"Redraw this scene. {SCENE} {STYLE}", file_contents=[ImageContent(ref)]))
    assert images, "no image"
    open("/app/memory/moment-doctor-v2.png", "wb").write(base64.b64decode(images[0]["data"]))
    im = Image.open("/app/memory/moment-doctor-v2.png").convert("RGB"); w, h = im.size; th = int(w * 2 / 3)
    if h > th:
        im = im.crop((0, (h - th) // 2, w, (h + th) // 2))
    im.thumbnail((1200, 800)); im.save("/app/frontend/public/moment-doctor.jpg", quality=82); print("saved", im.size)

asyncio.run(main())
