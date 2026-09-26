"""OpenAI TTS (tts-1, via Emergent key) — cached in object storage; read-aloud for guides, samples and Foundation prompts."""
import hashlib
import logging
import os
import re
from datetime import datetime, timezone

import emoji
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from storage import APP_NAME, get_object, put_object

logger = logging.getLogger("tts")
VOICES = {"sage", "coral", "alloy", "echo", "nova", "shimmer"}


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str = "sage"


def clean_for_tts(text: str) -> str:
    text = emoji.replace_emoji(text, replace="")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#>~|`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def cache_key(text: str, voice: str) -> str:
    return hashlib.sha256(f"{text}|{voice}|1.0|tts-1|mp3".encode()).hexdigest()[:40]


def build_router(db) -> APIRouter:
    r = APIRouter()

    @r.post("/tts")
    async def make(body: TtsIn):
        voice = body.voice if body.voice in VOICES else "sage"
        text = clean_for_tts(body.text)
        if not text:
            raise HTTPException(status_code=400, detail="Nothing to read")
        key = cache_key(text, voice)
        if await db.tts_cache.find_one({"key": key}, {"_id": 1}):
            return {"key": key, "url": f"/api/tts/{key}.mp3", "cached": True}
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="Text-to-speech is not configured")
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            audio = await OpenAITextToSpeech(api_key=api_key).generate_speech(text=text, model="tts-1", voice=voice)
            path = put_object(f"{APP_NAME}/tts/{key}.mp3", audio, "audio/mpeg")["path"]
        except Exception as exc:
            logger.warning("tts failed: %s", exc)
            raise HTTPException(status_code=502, detail="Text-to-speech is unavailable right now")
        await db.tts_cache.insert_one({"key": key, "storage_path": path, "voice": voice, "chars": len(text), "created_at": datetime.now(timezone.utc).isoformat()})
        return {"key": key, "url": f"/api/tts/{key}.mp3", "cached": False}

    @r.get("/tts/{key}.mp3")
    async def audio(key: str):
        rec = await db.tts_cache.find_one({"key": key}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Audio not found")
        data, _ = get_object(rec["storage_path"])
        return Response(content=data, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=31536000"})

    return r
