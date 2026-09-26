import asyncio, os, base64, sys
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ref = base64.b64encode(open('/app/frontend/public/badge-uniform.png', 'rb').read()).decode()


async def main():
    chat = LlmChat(api_key=os.getenv("EMERGENT_LLM_KEY"), session_id="badge-agreement", system_message="You are a brand designer.").with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    msg = UserMessage(text=("Create a matching circular badge in exactly the same style, proportions, white background and flat vector look as this reference badge. "
                            "Colour scheme: fresh green (#5aa839) ring and text instead of purple, with small purple and teal accents. Center icon: two stylised parent figures shaking hands "
                            "over a small child figure with a heart, above a signed agreement document. Large bold text 'CO-PARENTING AGREEMENT' in green in the same typographic style, "
                            "a small dot separator, and the tagline 'Merge Foundations. Build Your Agreement.' below. No other text, square image, badge fully visible with margin."),
                      file_contents=[ImageContent(ref)])
    text, images = await chat.send_message_multimodal_response(msg)
    print((text or "")[:80], len(images or []))
    if images:
        open('/tmp/badge-agreement-raw.png', 'wb').write(base64.b64decode(images[0]['data']))


asyncio.run(main())
