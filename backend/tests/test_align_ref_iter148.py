# align_ref per-parent: creation on every signup path, immutability, backfill, check-in link, and no leaks.
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "frontend" / ".env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
PASSWORD = "Str0ng!Pass99"
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_emails, _uids, _cases = [], [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    db.users.delete_many({"$or": [{"email": {"$in": _emails}}, {"user_id": {"$in": _uids}}]})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db.magic_links.delete_many({"email": {"$in": _emails}})
    db.coparent_invites.delete_many({"invitee_email": {"$in": _emails}})


def _email():
    e = f"test_aref_{uuid.uuid4().hex[:10]}@example.com"
    _emails.append(e)
    return e


def _register(email=None):
    email = email or _email()
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "name": "ARef Test", **CONSENT}, timeout=30)
    assert r.status_code == 200, r.text
    u = db.users.find_one({"email": email})
    _uids.append(u["user_id"])
    return u, {"Authorization": f"Bearer {r.json()['access_token']}"}, r


def _link(h):
    return httpx.get(f"{API}/family-checkin/link", headers=h, timeout=30)


def _insert_case(*uids):
    cid = f"SA-T{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending", "created_at": datetime.now(timezone.utc),
                                         "parents": [{"parent_slot": s, "user_id": u, "align_ref": str(uuid.uuid4())} for s, u in zip("AB", uids)]})
    return cid


# --- creation paths ---
def test_register_creates_uuid4_align_ref_not_in_response():
    u, h, r = _register()
    assert UUID4.match(u["align_ref"])
    assert u["align_ref"] not in r.text and "align_ref" not in r.text


def test_guest_creates_align_ref_and_claim_keeps_it():
    r = httpx.post(f"{API}/auth/guest", json={}, timeout=30)
    assert r.status_code == 200, r.text
    uid = r.json()["user"]["user_id"]
    _uids.append(uid)
    ref = db.users.find_one({"user_id": uid})["align_ref"]
    assert UUID4.match(ref) and ref not in r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    email = _email()
    c = httpx.post(f"{API}/auth/claim", headers=h, json={"email": email, "password": PASSWORD, "name": "Claimed", **CONSENT}, timeout=30)
    assert c.status_code == 200, c.text
    assert db.users.find_one({"user_id": uid})["align_ref"] == ref and ref not in c.text


def test_magic_link_signup_creates_align_ref():
    email = _email()
    tok = uuid.uuid4().hex + uuid.uuid4().hex
    db.magic_links.insert_one({"token": tok, "email": email, "mode": "signup", "used": False,
                               "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
                               "created_at": datetime.now(timezone.utc).isoformat()})
    r = httpx.post(f"{API}/auth/signup-from-token", json={"token": tok, "name": "Magic", "password": PASSWORD, **CONSENT}, timeout=30)
    assert r.status_code == 200, r.text
    u = db.users.find_one({"email": email})
    _uids.append(u["user_id"])
    assert UUID4.match(u["align_ref"]) and u["align_ref"] not in r.text


def test_coparent_invite_acceptance_creates_align_ref():
    inviter, _, _ = _register()
    email = _email()
    tok = uuid.uuid4().hex
    db.coparent_invites.insert_one({"invite_id": uuid.uuid4().hex, "token": tok, "invitee_email": email, "inviter_user_id": inviter["user_id"],
                                    "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
                                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()})
    r = httpx.post(f"{API}/invites/coparent/accept/{tok}", json={"name": "Invitee", "password": PASSWORD, **CONSENT}, timeout=30)
    assert r.status_code == 200, r.text
    u = db.users.find_one({"email": email})
    _uids.append(u["user_id"])
    assert UUID4.match(u["align_ref"]) and u["align_ref"] != inviter["align_ref"] and u["align_ref"] not in r.text


# --- immutability ---
def test_align_ref_unchanged_after_login_and_profile_update():
    u, h, _ = _register()
    ref = u["align_ref"]
    lg = httpx.post(f"{API}/auth/login", json={"email": u["email"], "password": PASSWORD}, timeout=30)
    assert lg.status_code == 200 and ref not in lg.text
    p = httpx.patch(f"{API}/auth/profile", headers=h, json={"name": "Renamed", "custody_situation": "x"}, timeout=30)
    assert p.status_code == 200, p.text
    assert ref not in p.text
    assert db.users.find_one({"user_id": u["user_id"]})["align_ref"] == ref


# --- backfill ---
def test_backfill_state_and_idempotent():
    assert db.users.count_documents({"align_ref": {"$exists": False}}) == 0
    assert db.users.count_documents({"align_ref": None}) == 0
    assert len(db.users.distinct("align_ref")) == db.users.count_documents({})
    idx = db.users.index_information().get("align_ref_1")
    assert idx and idx.get("unique") and idx.get("sparse")
    assert db.joint_alignment_cases.count_documents({"parents": {"$elemMatch": {"align_ref": {"$exists": False}}}}) == 0
    # a fresh legacy-style user + case entry gets filled; existing values kept
    uid = f"test_aref_legacy_{uuid.uuid4().hex[:8]}"
    _uids.append(uid)
    db.users.insert_one({"user_id": uid, "email": _email(), "name": "Legacy"})
    cid = f"SA-T{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    db.joint_alignment_cases.insert_one({"case_id": cid, "parents": [{"parent_slot": "A", "user_id": uid}, {"parent_slot": "B", "align_ref": "keep-me"}]})
    from motor.motor_asyncio import AsyncIOMotorClient
    from align_ref import backfill_align_refs

    async def run():
        mdb = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        a = await backfill_align_refs(mdb)
        b = await backfill_align_refs(mdb)
        return a, b
    a, b = asyncio.run(run())
    assert a["users"] >= 1 and a["case_parents"] >= 1
    ref = db.users.find_one({"user_id": uid})["align_ref"]
    case = db.joint_alignment_cases.find_one({"case_id": cid})
    assert UUID4.match(ref) and UUID4.match(case["parents"][0]["align_ref"]) and case["parents"][1]["align_ref"] == "keep-me"
    assert b == {"users": 0, "case_parents": 0}
    assert db.users.find_one({"user_id": uid})["align_ref"] == ref


# --- professional / integration case creation (in-process; invitation email patched out) ---
def test_case_creation_paths_give_each_parent_entry_align_ref(monkeypatch):
    import email_service
    import joint_alignment_routes as jar
    from motor.motor_asyncio import AsyncIOMotorClient
    monkeypatch.setattr(email_service, "send_joint_alignment_invitation", lambda **k: None, raising=False)
    ua, ha, _ = _register()
    ub, hb, _ = _register()
    pro, _, _ = _register()
    current = SimpleNamespace(user_id=pro["user_id"], name="Pro Tester", email=pro["email"])

    async def run():
        mdb = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        body = jar.ProfessionalCreateCaseRequest(assessment_type="co-parenting", parents=[{"email": ua["email"], "name": "A"}, {"email": ub["email"], "name": "B"}])
        res = await jar._create_and_invite_case(body=body, current=current, db=mdb)
        res2 = None
        key = os.environ.get("INTEGRATION_SHARED_SECRET")
        if key:
            body2 = jar.CreateCaseRequest(assessment_type="co-parenting", professional={"id": "pro_test_aref", "name": "Int Pro", "email": "intpro@example.com"},
                                          parents=[{"email": ua["email"]}, {"email": ub["email"]}])
            res2 = await jar.integration_create_case(body=body2, x_integration_key=key, db=mdb)
        return res, res2
    res, res2 = asyncio.run(run())
    for r in (res, res2):
        if r is None:
            continue
        _cases.append(r.case_id)
        assert "align_ref" not in r.model_dump_json()
        doc = db.joint_alignment_cases.find_one({"case_id": r.case_id})
        refs = [p["align_ref"] for p in doc["parents"]]
        assert all(UUID4.match(x) for x in refs) and refs[0] != refs[1]
    # Parent A accepts via HTTP; link then returns the ACCOUNT align_ref (not the case-entry one)
    doc = db.joint_alignment_cases.find_one({"case_id": res.case_id})
    tok = doc["parents"][0]["invitation_token"]
    acc = httpx.post(f"{API}/joint-alignment/invitation/{tok}/accept", headers=ha, timeout=30)
    assert acc.status_code == 200, acc.text
    entry_ref = doc["parents"][0]["align_ref"]
    assert entry_ref not in acc.text and ua["align_ref"] not in acc.text
    after = db.joint_alignment_cases.find_one({"case_id": res.case_id})["parents"][0]["align_ref"]
    assert after == entry_ref
    assert _link(ha).json()["align_ref"] == ua["align_ref"]
    mine = httpx.get(f"{API}/joint-alignment/mine", headers=ha, timeout=30)
    assert entry_ref not in mine.text and ua["align_ref"] not in mine.text


# --- link endpoint ---
def test_link_endpoint_linked_unlinked_two_cases_and_auth():
    ua, ha, _ = _register()
    ub, hb, _ = _register()
    uc, hc, _ = _register()
    unl = _link(hc)
    assert unl.status_code == 200 and unl.json() == {"align_ref": None}
    _insert_case(ua["user_id"], ub["user_id"])
    a, b = _link(ha), _link(hb)
    assert a.json()["align_ref"] == ua["align_ref"] and b.json()["align_ref"] == ub["align_ref"]
    assert ua["align_ref"] != ub["align_ref"]
    assert "no-store" in a.headers.get("cache-control", "")
    _insert_case(ua["user_id"], uc["user_id"])
    assert _link(ha).json()["align_ref"] == ua["align_ref"]
    assert _link(hc).json()["align_ref"] == uc["align_ref"]
    assert httpx.get(f"{API}/family-checkin/link", timeout=30).status_code == 401


# --- no leaks ---
def test_align_ref_not_in_parent_endpoints():
    ua, ha, _ = _register()
    ub, _, _ = _register()
    cid = _insert_case(ua["user_id"], ub["user_id"])
    entry_refs = [p["align_ref"] for p in db.joint_alignment_cases.find_one({"case_id": cid})["parents"]]
    secrets_ = [ua["align_ref"], ub["align_ref"], *entry_refs]
    for path in ("/auth/me", "/case-settings", f"/case-settings?case_id={cid}", "/me/export", "/joint-alignment/mine",
                 "/family-checkin/status", "/family-checkin/reminder", f"/joint-alignment/case/{cid}"):
        r = httpx.get(f"{API}{path}", headers=ha, timeout=30)
        for s in secrets_:
            assert s not in r.text, f"{path} leaks align_ref"
        if path != "/family-checkin/link":
            assert "align_ref" not in r.text, f"{path} has align_ref key"


def test_align_ref_not_in_admin_user_data():
    u, _, _ = _register()
    lg = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=30)
    if lg.status_code != 200:
        pytest.skip(f"admin login failed {lg.status_code}")
    h = {"Authorization": f"Bearer {lg.json()['access_token']}"}
    lst = httpx.get(f"{API}/analytics/admin/users", headers=h, params={"q": u["email"]}, timeout=30)
    assert lst.status_code == 200 and u["email"] in lst.text
    det = httpx.get(f"{API}/analytics/admin/users/{u['user_id']}", headers=h, timeout=30)
    assert det.status_code == 200
    for r in (lst, det):
        assert u["align_ref"] not in r.text and "align_ref" not in r.text
