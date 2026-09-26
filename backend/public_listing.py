"""Public 'Find a Professional' directory: opt-in listing for approved professionals."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from geo import zip_distance_miles

PUBLIC_FIELDS = ("name", "pro_role", "organization", "city", "state", "zip", "bio", "phone", "website", "credentials_verified", "listed_at")


class ListingIn(BaseModel):
    listed: bool = True
    bio: str = Field("", max_length=600)
    phone: str = Field("", max_length=40)
    website: str = Field("", max_length=200)
    zip: str = Field("", max_length=10)


def _clean_site(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url[:200]


def public_card(u: dict) -> dict:
    p, listing = u.get("profile") or {}, u.get("public_listing") or {}
    return {"id": u["_id"], "name": u.get("name", ""), "pro_role": p.get("pro_role", ""), "organization": p.get("organization", ""),
            "city": p.get("city", ""), "state": p.get("state", ""), "zip": (p.get("zip") or "")[:10],
            "bio": listing.get("bio", ""), "phone": listing.get("phone", ""), "website": listing.get("website", ""),
            "credentials_verified": u.get("verification_level") == "credentials_verified", "listed_at": listing.get("listed_at")}


def _require_listable(user: dict) -> None:
    if user.get("role") != "professional" or not user.get("approved"):
        raise HTTPException(status_code=403, detail="Only approved professionals can be listed publicly")


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/me/public-listing")
    async def my_listing(user=Depends(get_current_user)):
        _require_listable(user)
        listing = user.get("public_listing") or {}
        return {"listed": bool(listing.get("listed")), "hidden": bool(listing.get("hidden")), "hidden_reason": listing.get("hidden_reason", ""), "card": public_card(user)}

    @r.put("/me/public-listing")
    async def set_listing(body: ListingIn, user=Depends(get_current_user)):
        _require_listable(user)
        prev = user.get("public_listing") or {}
        listing = {"listed": body.listed, "bio": body.bio.strip(), "phone": body.phone.strip(), "website": _clean_site(body.website), "hidden": bool(prev.get("hidden")), "hidden_reason": prev.get("hidden_reason", ""),
                   "listed_at": prev.get("listed_at") if prev.get("listed") else datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
        update = {"public_listing": listing}
        if body.zip.strip():
            update["profile.zip"] = body.zip.strip()[:10]
        await db.users.update_one({"_id": user["_id"]}, {"$set": update})
        fresh = await db.users.find_one({"_id": user["_id"]}, {"password_hash": 0})
        return {"listed": body.listed, "hidden": listing["hidden"], "hidden_reason": listing["hidden_reason"], "card": public_card(fresh)}

    @r.get("/public/professionals")
    async def public_directory(zip: str = "", q: str = ""):
        docs = await db.users.find({"role": "professional", "approved": True, "public_listing.listed": True, "public_listing.hidden": {"$ne": True}},
                                   {"name": 1, "profile": 1, "public_listing": 1, "verification_level": 1}).sort("name", 1).to_list(2000)
        cards = [public_card(d) for d in docs]
        if q.strip():
            needle = q.strip().lower()
            cards = [c for c in cards if needle in f"{c['name']} {c['pro_role']} {c['organization']} {c['city']} {c['state']} {c['bio']}".lower()]
        for c in cards:
            c["distance_miles"] = zip_distance_miles(c["zip"], zip) if zip.strip() else None
        if zip.strip():
            cards.sort(key=lambda c: (c["distance_miles"] if c["distance_miles"] is not None else 99999, c["name"].lower()))
        return {"professionals": cards, "count": len(cards),
                "note": "Listing on SA CoParents Align is voluntary and indicates an approved account; it is not an endorsement, referral, or recommendation."}

    @r.get("/public/professionals/{pro_id}")
    async def public_card_one(pro_id: str):
        d = await db.users.find_one({"_id": pro_id, "role": "professional", "approved": True, "public_listing.listed": True, "public_listing.hidden": {"$ne": True}},
                                    {"name": 1, "profile": 1, "public_listing": 1, "verification_level": 1})
        if not d:
            raise HTTPException(status_code=404, detail="This professional is not currently listed")
        return public_card(d)

    @r.get("/admin/public-listings")
    async def admin_listings(user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        docs = await db.users.find({"role": "professional", "public_listing.listed": True}, {"name": 1, "email": 1, "profile": 1, "public_listing": 1, "verification_level": 1, "approved": 1}).sort("name", 1).to_list(2000)
        return [{**public_card(d), "email": d["email"], "approved": bool(d.get("approved")), "hidden": bool((d.get("public_listing") or {}).get("hidden")),
                 "hidden_reason": (d.get("public_listing") or {}).get("hidden_reason", "")} for d in docs]

    class HideIn(BaseModel):
        hidden: bool
        reason: str = Field("", max_length=400)

    @r.post("/admin/public-listings/{pro_id}/hide")
    async def admin_hide(pro_id: str, body: HideIn, user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        res = await db.users.update_one({"_id": pro_id, "public_listing.listed": True},
                                        {"$set": {"public_listing.hidden": body.hidden, "public_listing.hidden_reason": body.reason.strip() if body.hidden else "",
                                                  "public_listing.hidden_at": datetime.now(timezone.utc).isoformat() if body.hidden else None, "public_listing.hidden_by": user["_id"] if body.hidden else None}})
        if not res.matched_count:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {"id": pro_id, "hidden": body.hidden}

    return r
