"""Safety Gate: independent verification against the PUBLIC URL (REACT_APP_BACKEND_URL)."""
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

import requests
import pytest
pytestmark = pytest.mark.skip(reason="Built for the removed auto_red rule (2026-10-19); covered by test_safety_gate.py and test_safety_gate_correction.py.")
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "frontend" / ".env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
SECRET = os.environ.get("ALIGN_WEBHOOK_SECRET")

if not SECRET:
    pytest.skip("ALIGN_WEBHOOK_SECRET is not set: the webhook is off", allow_module_level=True)
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
LIMITED = ("free_form_messaging", "calls_video", "addresses_visible", "gps_checkins")
COOP = {"comm_flexible_dm", "comm_joint_meetings", "ex_flexible_home", "sch_shared_events", "dec_joint_everyday", "sched_flexible"}
BAD = ("safety", "screening", "violence", "abuse", "risk", "reason", "auto_red", "restricted", "dr. ext")
_emails, _cases = [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    ids = [u["user_id"] for u in db.users.find({"email": {"$in": _emails}}, {"user_id": 1})]
    db.users.delete_many({"email": {"$in": _emails}})
    for c in ("privacy_consents", "legal_acknowledgments", "plan_option_picks"):
        db[c].delete_many({"user_id": {"$in": ids}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db.case_safety.delete_many({"case_id": {"$in": _cases}})


def _user():
    email = f"test_ext_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Ext Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    return db.users.find_one({"email": email})["user_id"], {"Authorization": f"Bearer {r.json()['access_token']}"}


def _case():
    cid = f"SA-E{uuid.uuid4().hex[:5].upper()}"
    _cases.append(cid)
    (ua, ha), (ub, hb) = _user(), _user()
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending", "parents": [
        {"parent_slot": "A", "user_id": ua}, {"parent_slot": "B", "user_id": ub}]})
    return cid, ha, hb


def _send(cid, v, mode="standard", set_by="professional", referral="none", offered=True, ts=None, sig="auto"):
    raw = json.dumps({"case_id": cid, "safety_mode": mode, "set_by": set_by, "professional_name": "Dr. Ext",
                      "referral": referral, "screening_offered": offered, "version": v,
                      "timestamp": int(time.time()) if ts is None else ts}).encode()
    h = {"Content-Type": "application/json"}
    if sig == "auto":
        sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if sig is not None:
        h["X-Align-Signature"] = sig
    return requests.post(f"{API}/internal/safety-status", data=raw, headers=h, timeout=20)


def _flags(h):
    r = requests.get(f"{API}/case-settings", headers=h, timeout=20)
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "")
    return r


def _admin():
    r = requests.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# (1)(2) auto_red restricted -> both lose features; byte-identical
def test_restricted_both_parents_identical():
    cid, ha, hb = _case()
    assert _send(cid, 1).status_code == 200
    assert all(_flags(ha).json()["features"][k] for k in LIMITED)
    assert _send(cid, 2, mode="restricted", set_by="auto_red").status_code == 200
    a, b = _flags(ha), _flags(hb)
    assert a.content == b.content
    assert not any(a.json()["features"][k] for k in LIMITED)
    assert a.json()["banner"] == "Some features are set by your professional for this case."
    assert not any(w in a.text.lower() for w in BAD)


# (5) bad signature -> 401, no mutation
@pytest.mark.parametrize("sig", [None, "", "abc123", "sha256=" + "0" * 64])
def test_bad_sig(sig):
    cid, ha, _ = _case()
    assert _send(cid, 1, sig=sig).status_code == 401
    assert db.case_safety.find_one({"case_id": cid}) is None


# (6) old timestamp / version <= stored
def test_stale():
    cid, ha, _ = _case()
    assert _send(cid, 1, ts=int(time.time()) - 400).status_code == 401
    assert db.case_safety.find_one({"case_id": cid}) is None
    assert _send(cid, 5).status_code == 200
    before = db.case_safety.find_one({"case_id": cid}, {"_id": 0})
    assert _send(cid, 5, mode="restricted", set_by="auto_red").status_code == 200
    assert _send(cid, 4, mode="restricted", set_by="auto_red").status_code == 200
    assert db.case_safety.find_one({"case_id": cid}, {"_id": 0}) == before
    assert _flags(ha).json()["features"]["free_form_messaging"] is True


# (7) parallel referral -> no cooperative templates for either parent
def test_referral_plan_options():
    cid, ha, hb = _case()
    assert _send(cid, 1, mode="structured", referral="parallel_parenting").status_code == 200
    ra = requests.get(f"{API}/plan-options", headers=ha, timeout=20)
    rb = requests.get(f"{API}/plan-options", headers=hb, timeout=20)
    assert ra.status_code == 200 and ra.content == rb.content
    ids = {o["id"] for c in ra.json()["categories"] for o in c["options"]}
    assert ids and not (ids & COOP)
    assert _flags(ha).json()["plan_options"] is True and _flags(hb).json()["plan_options"] is True
    assert not any(w in ra.text.lower() for w in ("safety", "screening", "violence", "abuse"))


# (8) templates in every mode
def test_templates_every_mode():
    cid, ha, _ = _case()
    for v, m in ((1, "standard"), (2, "structured"), (3, "restricted")):
        _send(cid, v, mode=m)
        b = _flags(ha).json()
        assert b["features"]["template_messages"] is True
        assert b["template_categories"] == ["schedule", "health", "school", "expenses"]


# (11) new case structured
def test_new_case_structured():
    cid, ha, hb = _case()
    b = _flags(ha).json()
    assert b["features"]["free_form_messaging"] is False
    assert b["banner"] == "Some features are limited until your case setup is complete."
    assert _flags(ha).content == _flags(hb).content


# openapi hidden, support mode only, admin endpoints
def test_openapi_hidden():
    for url in (f"{API}/openapi.json", f"{BASE}/openapi.json"):
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            assert "internal" not in json.dumps(r.json().get("paths", {}))


def test_support_and_admin():
    cid, ha, _ = _case()
    _send(cid, 1, mode="restricted", set_by="auto_red", referral="parallel_parenting")
    adm = _admin()
    assert requests.get(f"{API}/support/case-settings/{cid}", headers=ha, timeout=20).status_code == 403
    s = requests.get(f"{API}/support/case-settings/{cid}", headers=adm, timeout=20)
    assert s.json() == {"case_id": cid, "safety_mode": "restricted"}
    for p in ("export", "daily-counts"):
        assert requests.get(f"{API}/admin/safety-audit-log/{p}", headers=ha, timeout=20).status_code == 403
        assert requests.get(f"{API}/admin/safety-audit-log/{p}", timeout=20).status_code in (401, 403)
        r = requests.get(f"{API}/admin/safety-audit-log/{p}", headers=adm, timeout=30)
        assert r.status_code == 200 and "no-store" in r.headers.get("cache-control", "")


def test_daily_counts_increment():
    adm = _admin()
    url = f"{API}/admin/safety-audit-log/daily-counts"
    b = requests.get(url, headers=adm, timeout=20).json()["days"][0]
    cid, _, _ = _case()
    _send(cid, 1)
    _send(cid, 2)
    _send(cid, 1, mode="structured")
    requests.get(f"{API}/admin/safety-audit-log/export", headers=adm, timeout=30)
    r = requests.get(url, headers=adm, timeout=20)
    a = r.json()["days"][0]
    assert (a["applied"] - b["applied"], a["ignored"] - b["ignored"], a["downloads"] - b["downloads"]) == (2, 1, 1)
    assert "SA-" not in r.text and len(r.json()["days"]) == 30


# (10) parent-visible exports clean
def test_parent_exports_clean():
    cid, ha, _ = _case()
    _send(cid, 1, mode="restricted", set_by="auto_red", referral="parallel_parenting")
    requests.get(f"{API}/help/local-services", timeout=20)
    for p in ("/me/export", "/me/access-log", "/portal/state", "/plan-options/picks", "/notifications"):
        r = requests.get(f"{API}{p}", headers=ha, timeout=30)
        t = r.text.lower()
        assert cid.lower() not in t and "safety_mode" not in t and "parallel_parenting" not in t and "help_local" not in t, p
