"""Admin-maintained resource provider directory (collection: providers) feeding the Legal Lens resource checklists."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

LISTS = ("individual", "joint")
SEED = [
    {"name": "Kelly Bernstein", "degrees": "MS, LCDC, LPC", "specialty": "Child-Focused Options Provider", "organization": "", "phone": "(210) 265-1952", "email": "", "website": "https://www.kellybernsteinlpc.com/", "lists": ["individual", "joint"]},
    {"name": "Kassandra Levay", "degrees": "", "specialty": "Education Specialist", "organization": "", "phone": "(210) 379-8692", "email": "levaykord@gmail.com", "website": "", "lists": ["individual", "joint"]},
    {"name": "Brad Craig", "degrees": "", "specialty": "Children in the Middle", "organization": "", "phone": "Toll-Free (800) 239-3971 · Local (817) 658-6013", "email": "brad@betweentwohomes.com", "website": "https://www.betweentwohomes.com/", "lists": ["joint"]},
]


class ProviderIn(BaseModel):
    name: str
    specialty: str = ""
    organization: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    degrees: str = ""
    lists: list[str] = ["individual", "joint"]
    active: bool = True


def label(p: dict) -> str:
    base = f"{p['name']}, {p['degrees']}" if p.get("degrees") else p["name"]
    return f"{base} — {p['specialty']}" if p.get("specialty") else base


def contact(p: dict) -> str:
    return " · ".join(x for x in (p.get("organization"), p.get("phone"), p.get("email"), p.get("website")) if x)


def public(p: dict) -> dict:
    return {"id": p["id"], "label": label(p), "name": f"{p['name']}, {p['degrees']}" if p.get("degrees") else p["name"], "specialty": p.get("specialty", ""), "contact": contact(p), "lists": p.get("lists") or []}


async def seed_providers(db) -> None:
    if await db.providers.count_documents({}) == 0:
        now = datetime.now(timezone.utc).isoformat()
        await db.providers.insert_many([{"id": str(uuid.uuid4()), **s, "active": True, "created_at": now, "updated_at": now} for s in SEED])


async def active_providers(db) -> list[dict]:
    return [public(p) for p in await db.providers.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(200)]


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    def admin(user: dict) -> None:
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")

    def clean(body: ProviderIn) -> dict:
        d = body.model_dump()
        d["name"] = d["name"].strip()[:120]
        if not d["name"]:
            raise HTTPException(status_code=400, detail="Provider name is required")
        d["lists"] = [x for x in d["lists"] if x in LISTS] or ["individual", "joint"]
        return {k: (v.strip()[:300] if isinstance(v, str) else v) for k, v in d.items()}

    @r.get("/providers")
    async def list_active(user=Depends(get_current_user)):
        if user.get("role") not in ("professional", "admin"):
            raise HTTPException(status_code=403, detail="Professional access required")
        return await active_providers(db)

    @r.get("/admin/providers")
    async def list_all(user=Depends(get_current_user)):
        admin(user)
        return await db.providers.find({}, {"_id": 0}).sort("name", 1).to_list(500)

    @r.post("/admin/providers")
    async def create(body: ProviderIn, user=Depends(get_current_user)):
        admin(user)
        now = datetime.now(timezone.utc).isoformat()
        doc = {"id": str(uuid.uuid4()), **clean(body), "created_at": now, "updated_at": now}
        await db.providers.insert_one({**doc})
        return doc

    @r.put("/admin/providers/{pid}")
    async def update(pid: str, body: ProviderIn, user=Depends(get_current_user)):
        admin(user)
        upd = {**clean(body), "updated_at": datetime.now(timezone.utc).isoformat()}
        res = await db.providers.update_one({"id": pid}, {"$set": upd})
        if not res.matched_count:
            raise HTTPException(status_code=404, detail="Provider not found")
        return await db.providers.find_one({"id": pid}, {"_id": 0})

    @r.delete("/admin/providers/{pid}")
    async def delete(pid: str, user=Depends(get_current_user)):
        admin(user)
        res = await db.providers.delete_one({"id": pid})
        if not res.deleted_count:
            raise HTTPException(status_code=404, detail="Provider not found")
        return {"ok": True}

    return r
