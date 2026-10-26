"""SAFE-ND(TM) staff-only reviews (owner 2026-10-24): access gate, encryption at rest, draft/final lifecycle, limits, access record."""
import json
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case  # noqa: E402

API = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
ENV = dotenv_values("/app/backend/.env")
MONGO = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]
R = f"{API}/safe-nd/reviews"
CHILD = "Zq Testchild Unique"


def rid_suffix():
    import uuid
    return uuid.uuid4().hex[:8]


def _data(sig=""):
    return {"case": {"child": CHILD, "reviewDate": "2026-10-24", "reviewer": "Rev One"},
            "referral": {"question": "Transitions", "sources": {"selected": ["Parent A interview"], "other": "Coach"}},
            "require": {"domains": {"communication": {"priority": "H", "notes": "Needs visuals"}, "executive": {"priority": "L", "notes": ""}}},
            "support": {"homes": {"availability": {"a": "Flexible", "b": "Shift work", "plan": "Weekday base at A"}}},
            "disposition": {"next": {"selected": ["Child-protection / safety response required where legally indicated"], "other": ""}, "signature": sig, "signedDate": "2026-10-24" if sig else ""}}


def _admin():
    from casekit import new_user
    s = new_user(API, "professional", "Adm")
    MONGO.users.update_one({"email": s.email}, {"$set": {"role": "admin"}})  # test-only promotion
    return s


def test_safe_nd_access_and_lifecycle():
    pro, pa, pb, d, _ = completed_case(API)
    judge = requests.Session()
    rj = judge.post(f"{API}/auth/register", json={"name": "J", "email": f"t_judge_{rid_suffix()}@example.com", "password": "Password123!", "role": "judge",
                                                 "agreements_accepted": True, "organization": "Bexar County Court"})
    assert rj.status_code == 200, rj.text

    # gate: signed out 401; parent & judge 403 on every route
    assert requests.get(R).status_code == 401
    for s in (pa, judge):
        assert s.get(R).status_code == 403
        assert s.post(R, json={"data": _data()}).status_code == 403
        assert s.get(f"{R}/anything").status_code == 403
        assert s.put(f"{R}/anything", json={"data": {}}).status_code == 403
        assert s.post(f"{R}/anything/finalize").status_code == 403

    # staff: create, list, get, update
    r = pro.post(R, json={"data": _data()}); assert r.status_code == 201, r.text
    rid = r.json()["id"]
    rows = pro.get(R).json()
    row = next(x for x in rows if x["id"] == rid)
    assert row["child"] == CHILD and row["reviewDate"] == "2026-10-24" and row["status"] == "draft" and set(row) == {"id", "child", "reviewDate", "status", "updatedAt"}
    g = pro.get(f"{R}/{rid}").json()
    assert g["status"] == "draft" and g["data"]["require"]["domains"]["communication"]["priority"] == "H" and g["data"]["support"]["homes"]["availability"]["plan"] == "Weekday base at A"
    assert pro.put(f"{R}/{rid}", json={"data": _data()}).status_code == 200

    # encrypted at rest: no plaintext in the stored document; access record has no contents
    raw = MONGO.safe_nd_reviews.find_one({"id": rid})
    assert CHILD not in json.dumps(raw, default=str) and "Needs visuals" not in json.dumps(raw, default=str) and raw["data_enc"]
    assert set(raw) >= {"id", "status", "data_enc", "created_by", "created_at", "updated_at", "finalized_by", "finalized_at"}
    acc = list(MONGO.safe_nd_access.find({"review_id": rid}))
    assert {a["action"] for a in acc} >= {"created", "opened", "saved"} and CHILD not in json.dumps(acc, default=str)

    # limits: JSON only, 500 KB, data must be object
    assert pro.post(R, data="x=1", headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 415
    assert pro.post(R, json={"data": "nope"}).status_code == 400
    assert pro.post(R, data=json.dumps({"data": {"big": "x" * (501 * 1024)}}), headers={"Content-Type": "application/json"}).status_code == 413

    # finalize: signature+date required; then locked (409) forever
    assert pro.post(f"{R}/{rid}/finalize").status_code == 400
    assert pro.put(f"{R}/{rid}", json={"data": _data(sig="Rev One")}).status_code == 200
    assert pro.post(f"{R}/{rid}/finalize").status_code == 200
    assert pro.get(f"{R}/{rid}").json()["status"] == "final"
    assert pro.put(f"{R}/{rid}", json={"data": _data(sig="Rev One")}).status_code == 409
    assert pro.post(f"{R}/{rid}/finalize").status_code == 409
    fin = MONGO.safe_nd_reviews.find_one({"id": rid})
    assert fin["finalized_by"] and fin["finalized_at"]

    # deletion: admin only
    assert pro.delete(f"{R}/{rid}").status_code == 403
    adm = _admin()
    assert adm.get(R).status_code == 200
    assert adm.delete(f"{R}/{rid}").status_code == 200
    assert pro.get(f"{R}/{rid}").status_code == 404
    assert any(a["action"] == "deleted" for a in MONGO.safe_nd_access.find({"review_id": rid}))
