"""Iteration 80: opt-in public 'Find a Professional' listing."""
import os
import uuid

import pymongo
import requests

from casekit import new_user
from test_judicial_portal import API


def test_public_listing_opt_in_and_public_directory() -> None:
    pro = new_user(API, "professional", "Listed Pro")
    me = pro.get(f"{API}/auth/me").json()
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.users.update_one({"_id": me["id"]}, {"$set": {"profile.city": "San Antonio", "profile.state": "TX"}})

    st = pro.get(f"{API}/me/public-listing").json()
    assert st["listed"] is False and st["card"]["name"] == "Listed Pro"

    tag = uuid.uuid4().hex[:6]
    r = pro.put(f"{API}/me/public-listing", json={"listed": True, "bio": f"Mediation for separated parents {tag}", "website": "example.org", "phone": "210-555-0100", "zip": "78201"})
    assert r.status_code == 200, r.text
    assert r.json()["listed"] is True and r.json()["card"]["website"] == "https://example.org" and r.json()["card"]["zip"] == "78201"

    anon = requests.get(f"{API}/public/professionals", params={"q": tag, "zip": "78205"})
    assert anon.status_code == 200
    body = anon.json()
    assert body["count"] == 1 and "endorsement" in body["note"]
    card = body["professionals"][0]
    assert card["id"] == me["id"] and card["distance_miles"] is not None and "email" not in card
    assert {"name", "pro_role", "organization", "city", "state", "zip", "bio", "phone", "website", "credentials_verified"} <= set(card)

    assert pro.put(f"{API}/me/public-listing", json={"listed": False}).json()["listed"] is False
    assert requests.get(f"{API}/public/professionals", params={"q": tag}).json()["count"] == 0

    from test_judicial_portal import _judge
    assert _judge().put(f"{API}/me/public-listing", json={"listed": True}).status_code == 403
    unapproved = requests.Session()
    e = f"t_unl_{uuid.uuid4().hex[:8]}@example.com"
    assert unapproved.post(f"{API}/auth/register", json={"name": "Unapproved", "email": e, "password": "testpass123", "role": "professional", "agreements_accepted": True, "organization": "Org", "pro_role": "Mediator"}).status_code == 200
    assert unapproved.put(f"{API}/me/public-listing", json={"listed": True}).status_code == 403
