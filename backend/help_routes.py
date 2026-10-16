"""Get help: admin-editable local services by state. The public list is never logged per visitor and never cached."""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from analytics_routes import require_admin
from auth import get_db
from case_safety import now_iso
from models import UserPublic

router = APIRouter(tags=["help"])
COLL = "help_local_services"
NO_STORE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}
_FIELDS = {"_id": 0, "id": 1, "state": 1, "name": 1, "phone": 1, "text": 1, "url": 1, "description": 1}

SEED = [
    {"state": "TX", "name": "Family Violence Prevention Services / Battered Women & Children's Shelter", "phone": "210-733-8810",
     "url": "https://fvps.org", "description": "San Antonio's primary domestic violence shelter and crisis hotline. 24/7 emergency shelter, counseling, and legal advocacy."},
    {"state": "TX", "name": "Bexar County Family Justice Center", "phone": "210-631-0100", "url": "https://www.bexar.org/3206/Family-Justice-Center",
     "description": "One-stop center co-locating advocates, law enforcement, prosecutors, and civil legal services for survivors in Bexar County."},
    {"state": "TX", "name": "PEACE Initiative", "phone": "210-533-2729", "url": "https://peaceinitiative.net",
     "description": "Education, advocacy, and survivor-led support groups for women and children affected by domestic violence in San Antonio."},
]


class ServiceIn(BaseModel):
    state: str
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)
    text: Optional[str] = Field(default=None, max_length=120)
    url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=600)

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("Use a two-letter state code.")
        return v

    @field_validator("url")
    @classmethod
    def _url(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^https?://", v.strip()):
            raise ValueError("Links must start with http:// or https://")
        return v.strip() if v else v


async def seed_help_services(db) -> None:
    if await db[COLL].count_documents({}) == 0:
        await db[COLL].insert_many([{**s, "id": uuid.uuid4().hex[:12], "updated_at": now_iso()} for s in SEED])


@router.get("/help/local-services")
async def local_services(db=Depends(get_db)):
    rows = await db[COLL].find({}, _FIELDS).sort([("state", 1), ("name", 1)]).to_list(2000)
    return JSONResponse({"services": rows}, headers=NO_STORE)


@router.get("/admin/help-services")
async def admin_list(_: UserPublic = Depends(require_admin), db=Depends(get_db)):
    return {"services": await db[COLL].find({}, _FIELDS).sort([("state", 1), ("name", 1)]).to_list(2000)}


@router.post("/admin/help-services")
async def admin_create(body: ServiceIn, _: UserPublic = Depends(require_admin), db=Depends(get_db)):
    doc = {**body.model_dump(), "id": uuid.uuid4().hex[:12], "updated_at": now_iso()}
    await db[COLL].insert_one(doc)
    return {k: doc.get(k) for k in _FIELDS if k != "_id"}


@router.put("/admin/help-services/{service_id}")
async def admin_update(service_id: str, body: ServiceIn, _: UserPublic = Depends(require_admin), db=Depends(get_db)):
    res = await db[COLL].update_one({"id": service_id}, {"$set": {**body.model_dump(), "updated_at": now_iso()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"id": service_id, **body.model_dump()}


@router.delete("/admin/help-services/{service_id}")
async def admin_delete(service_id: str, _: UserPublic = Depends(require_admin), db=Depends(get_db)):
    res = await db[COLL].delete_one({"id": service_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"ok": True}
