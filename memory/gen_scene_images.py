import asyncio, os, base64
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

STYLE = ("Flat vector illustration, clean modern style, soft white background, brand palette of deep purple #5B2A86, teal #1f8a8a, warm gold accents and gentle greens. "
         "Two co-parents (a man and a woman, standing apart but both present and supportive, no romantic contact) together with their child. Faces simple and friendly, no text, no logos, "
         "landscape 3:2 composition, consistent character design across images.")
SCENES = {
    "moment-graduation": "Both parents applauding proudly at their teenage child's graduation ceremony; the child in cap and gown holding a diploma, a stage and banner blurred behind.",
    "moment-school": "Both parents at a parent-teacher meeting in a bright classroom, sitting on either side of the teacher's desk, their young child showing a drawing; books and a chalkboard behind.",
    "moment-doctor": "Both parents calmly attending their child's pediatric check-up together; a friendly doctor with a stethoscope talks to the child on the exam table.",
    "moment-certificate": "Both parents standing side by side proudly holding a framed 'SA CoParents' co-parenting completion certificate (represented by a certificate with a purple ribbon seal, no readable text), their child between them smiling.",
}


async def gen(name, scene):
    chat = LlmChat(api_key=os.getenv("EMERGENT_LLM_KEY"), session_id=f"scene-{name}", system_message="You are an illustrator.").with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    _, images = await chat.send_message_multimodal_response(UserMessage(text=f"{scene} {STYLE}"))
    if images:
        open(f"/app/frontend/public/{name}.png", "wb").write(base64.b64decode(images[0]["data"]))
    print(name, bool(images))


async def main():
    await asyncio.gather(*(gen(n, s) for n, s in SCENES.items()))

asyncio.run(main())
