"""Professional profile: report-cover contact details and cover images (headshot / firm logo) in Emergent Object Storage."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from core import db
from storage import APP_NAME, get_object, put_object

SLOTS = ("headshot", "firm_logo", "signature")
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_IMAGE = 2 * 1024 * 1024


class ContactIn(BaseModel):
    phone: str = ""
    organization: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""


def _pro(user):
    if user.get("role") not in ("professional", "admin"):
        raise HTTPException(status_code=403, detail="Professional access required.")


def _slot(slot: str) -> str:
    if slot not in SLOTS:
        raise HTTPException(status_code=404, detail="Unknown image slot")
    return slot


def build_router(get_current_user) -> APIRouter:
    r = APIRouter(prefix="/me/profile")

    @r.put("/contact")
    async def set_contact(body: ContactIn, user=Depends(get_current_user)):
        _pro(user)
        upd = {f"profile.{k}": (v or "").strip()[:200] for k, v in body.model_dump().items()}
        upd["profile.zip"] = upd["profile.zip"][:10]
        await db.users.update_one({"_id": user["_id"]}, {"$set": upd})
        return {k.split(".", 1)[1]: v for k, v in upd.items()}

    @r.post("/image/{slot}")
    async def upload_image(slot: str, file: UploadFile = File(...), user=Depends(get_current_user)):
        _pro(user)
        slot = _slot(slot)
        ext = IMAGE_TYPES.get(file.content_type or "")
        if not ext:
            raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WebP image")
        data = await file.read()
        if len(data) > MAX_IMAGE:
            raise HTTPException(status_code=413, detail="Image must be 2 MB or smaller")
        res = put_object(f"{APP_NAME}/profile/{user['_id']}/{slot}-{uuid.uuid4()}.{ext}", data, file.content_type)
        ref = {"path": res["path"], "content_type": file.content_type, "uploaded_at": datetime.now(timezone.utc).isoformat()}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {f"profile.images.{slot}": ref}})
        return {"slot": slot, "uploaded_at": ref["uploaded_at"]}

    @r.delete("/image/{slot}")
    async def remove_image(slot: str, user=Depends(get_current_user)):
        _pro(user)
        await db.users.update_one({"_id": user["_id"]}, {"$unset": {f"profile.images.{_slot(slot)}": ""}})
        return {"ok": True}

    @r.get("/image/{slot}")
    async def get_image(slot: str, user=Depends(get_current_user)):
        ref = ((user.get("profile") or {}).get("images") or {}).get(_slot(slot))
        if not ref:
            raise HTTPException(status_code=404, detail="No image")
        data, ct = get_object(ref["path"])
        return Response(content=data, media_type=ref.get("content_type") or ct, headers={"Cache-Control": "private, max-age=300"})

    return r
