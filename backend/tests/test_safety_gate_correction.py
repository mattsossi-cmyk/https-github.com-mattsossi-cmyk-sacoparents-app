"""Safety Gate correction: no automatic restrictions, only a named professional sets or lifts a limit,
new cases start standard, older auto_red limits stay, admin count. Runs with the webhook OFF (no secret needed):
the signed-body handler is called directly after the signature step."""
import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import case_safety as cs  # noqa: E402
from case_safety_routes import handle_signed  # noqa: E402

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_cases, _emails = [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    db[cs.COLL].delete_many({"case_id": {"$in": _cases}})
    db[cs.AUDIT].delete_many({"case_id": {"$in": _cases}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db.users.delete_many({"email": {"$in": _emails}})


def run(fn):
    async def main():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        try:
            return await fn(client[os.environ["DB_NAME"]])
        finally:
            client.close()
    return asyncio.run(main())


def new_case():
    cid = f"SA-TCOR{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    return cid


def body(cid, version, mode="standard", set_by="professional", name="Dr. Reviewer", offered=True):
    return json.dumps({"case_id": cid, "safety_mode": mode, "set_by": set_by, "professional_name": name,
                       "referral": "none", "screening_offered": offered, "version": version,
                       "timestamp": int(time.time())}).encode()


def send(raw):
    return run(lambda d: handle_signed(d, raw))


def stored(cid):
    doc = db[cs.COLL].find_one({"case_id": cid}, {"_id": 0})
    return (doc, cs.decrypt(doc["enc"])) if doc else (None, None)


def mode(cid):
    return cs.resolve(stored(cid)[1])["mode"]


def seed_auto_red(cid):
    """An older record restricted by auto_red, as written before the mechanism was removed."""
    db[cs.COLL].insert_one({"case_id": cid, "version": 1, "updated_at": cs.now_iso(), "setup_completed_at": None,
                            "enc": cs.encrypt({**cs.DEFAULT, "safety_mode": "restricted", "set_by": "auto_red"})})


def last_reject(reason):
    return db[cs.REJECTS].find_one({"reason": reason}, sort=[("created", -1)])


def refused(raw, reason):
    before = last_reject(reason)
    with pytest.raises(HTTPException) as e:
        send(raw)
    assert e.value.status_code == 422
    after = last_reject(reason)
    assert after and (not before or after["_id"] != before["_id"]), f"{reason} not logged"


def test_new_case_defaults_standard():
    assert cs.DEFAULT["safety_mode"] == "standard"
    assert cs.resolve(None)["mode"] == "standard"
    assert cs.resolve({**cs.DEFAULT, "screening_offered": False})["mode"] == "standard"


def test_auto_red_refused_logged_and_nothing_written():
    cid = new_case()
    refused(body(cid, 1, mode="restricted", set_by="auto_red"), "auto_red_refused")
    assert stored(cid) == (None, None)
    assert run(lambda d: cs.apply_update(d, json.loads(body(cid, 2, mode="restricted", set_by="auto_red")))) == "refused"
    assert stored(cid) == (None, None)
    assert db[cs.AUDIT].find_one({"case_id": cid, "action": "write_refused"})


def test_auto_red_cannot_lift_an_older_auto_red_restriction():
    cid = new_case()
    seed_auto_red(cid)
    refused(body(cid, 5, mode="standard", set_by="auto_red"), "auto_red_refused")
    doc, f = stored(cid)
    assert doc["version"] == 1 and f["set_by"] == "auto_red" and mode(cid) == "restricted"


def test_non_professional_update_cannot_restrict():
    cid = new_case()
    assert send(body(cid, 1, mode="restricted", set_by="default", name=None, offered=False)) == {"ok": True}
    _, f = stored(cid)
    assert f["safety_mode"] == "standard" and f["set_by"] == "default" and mode(cid) == "standard"


def test_non_professional_update_cannot_unrestrict_and_still_updates_checkin():
    cid = new_case()
    send(body(cid, 1, mode="structured", offered=False))
    assert mode(cid) == "structured"
    send(body(cid, 2, mode="standard", set_by="default", name=None, offered=True))
    doc, f = stored(cid)
    assert mode(cid) == "structured" and f["set_by"] == "professional" and f["screening_offered"] is True
    assert doc["setup_completed_at"]
    auto = new_case()
    seed_auto_red(auto)
    send(body(auto, 2, mode="standard", set_by="default", name=None))
    _, f = stored(auto)
    assert f["set_by"] == "auto_red" and mode(auto) == "restricted"


def test_professional_sets_and_lifts_and_each_change_names_who():
    cid = new_case()
    send(body(cid, 1, mode="restricted", name="  Dr. Alpha  "))
    assert mode(cid) == "restricted"
    send(body(cid, 2, mode="standard", name="Dr. Beta"))
    assert mode(cid) == "standard"
    writes = list(db[cs.AUDIT].find({"case_id": cid, "action": "write"}, {"_id": 0}).sort("at", 1))
    assert [(w["actor_type"], w["actor_id"]) for w in writes] == [("professional", "Dr. Alpha"), ("professional", "Dr. Beta")]


def test_professional_lifts_an_older_auto_red_restriction():
    cid = new_case()
    seed_auto_red(cid)
    send(body(cid, 2, mode="standard", name="Dr. Gamma"))
    assert mode(cid) == "standard"


def test_professional_without_a_name_is_refused():
    cid = new_case()
    for name in (None, "   "):
        refused(body(cid, 1, mode="restricted", name=name), "no_professional_name")
    assert stored(cid) == (None, None)


def test_replay_still_refused():
    cid = new_case()
    raw = body(cid, 1, mode="structured")
    send(raw)
    with pytest.raises(HTTPException) as e:
        send(raw)
    assert e.value.status_code == 409


def _admin():
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _parent():
    email = f"test_cor_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Cor Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    return db.users.find_one({"email": email})["user_id"], {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_admin_count_is_a_number_only_and_admin_only():
    url = f"{API}/admin/safety-audit-log/auto-restricted"
    h = _admin()
    first = httpx.get(url, headers=h, timeout=20).json()
    assert list(first) == ["count"] and isinstance(first["count"], int)
    cid = new_case()
    seed_auto_red(cid)
    assert httpx.get(url, headers=h, timeout=20).json() == {"count": first["count"] + 1}
    _, ph = _parent()
    assert httpx.get(url, headers=ph, timeout=20).status_code == 403


def test_new_linked_family_gets_standard_settings():
    cid = new_case()
    (ua, ha), (ub, hb) = _parent(), _parent()
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending", "created_at": cs.now_iso(),
                                         "parents": [{"parent_slot": "A", "user_id": ua}, {"parent_slot": "B", "user_id": ub}]})
    want = cs.payload(cs.resolve(None))
    for h in (ha, hb):
        r = httpx.get(f"{API}/case-settings", headers=h, timeout=20)
        assert r.status_code == 200 and r.json()["features"] == want["features"]
