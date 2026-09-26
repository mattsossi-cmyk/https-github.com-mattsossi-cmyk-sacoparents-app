"""Iteration 79: judge nearby-professional picker — ZIP-ranked referable professionals + parties_zip on referral."""
import os
import uuid

import pymongo

from casekit import new_user
from test_judicial_portal import API, _judge


def _pro_with_zip(z: str, name: str):
    s = new_user(API, "professional", name)
    uid = s.get(f"{API}/auth/me").json()["id"]
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"_id": uid}, {"$set": {"profile.zip": z, "profile.city": "San Antonio", "profile.state": "TX"}})
    return uid


def test_zip_ranked_professionals_and_referral_stores_zip() -> None:
    judge = _judge()
    exact = _pro_with_zip("78201", "Exact Zip Pro")
    area = _pro_with_zip("78250", "Area Zip Pro")
    far = _pro_with_zip("75001", "Far Zip Pro")
    none = new_user(API, "professional", "No Zip Pro").get(f"{API}/auth/me").json()["id"]

    r = judge.get(f"{API}/court-dashboard/professionals", params={"zip": "78201"})
    assert r.status_code == 200, r.text
    rows = {x["id"]: x for x in r.json()}
    assert rows[exact]["match"] == "nearby" and rows[exact]["zip"] == "78201"
    assert rows[area]["match"] == "same_area"
    assert rows[far]["match"] == "" and rows[none]["match"] == ""
    order = [x["id"] for x in r.json()]
    assert order.index(exact) < order.index(area) < order.index(far) < order.index(none)

    plain = judge.get(f"{API}/court-dashboard/professionals").json()
    assert all(x["match"] == "" for x in plain) and {"zip", "city", "state", "distance_miles"} <= set(plain[0])

    # radius: 78201 (San Antonio) -> 78130 (New Braunfels, ~30 mi) is outside same-area but within 50 mi
    nb = _pro_with_zip("78130", "Radius Pro")
    r50 = {x["id"]: x for x in judge.get(f"{API}/court-dashboard/professionals", params={"zip": "78201", "radius": 50}).json()}
    assert r50[nb]["match"] == "within_radius" and 20 < r50[nb]["distance_miles"] < 45
    assert r50[far]["match"] == "" and r50[far]["distance_miles"] > 200
    r10 = {x["id"]: x for x in judge.get(f"{API}/court-dashboard/professionals", params={"zip": "78201", "radius": 10}).json()}
    assert r10[nb]["match"] == ""
    order50 = [x["id"] for x in judge.get(f"{API}/court-dashboard/professionals", params={"zip": "78201", "radius": 50}).json()]
    assert order50.index(area) < order50.index(nb) < order50.index(far)

    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": far, "cause_number": f"2026-CI-Z{uuid.uuid4().hex[:4]}", "requested_reports": ["co_parenting"], "parties_zip": " 78201 "})
    assert ref.status_code == 200, ref.text
    assert ref.json()["parties_zip"] == "78201"
    assert new_user(API, "professional", "Not Judge").get(f"{API}/court-dashboard/professionals", params={"zip": "78201"}).status_code == 403
