"""Runs with the webhook off: parent IDs are admin-run only, and the old in-app safety assessment works again."""
import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails, _cases = [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    db.users.delete_many({"email": {"$in": _emails}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})


def _user():
    email = f"test_ids_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Ids Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    return db.users.find_one({"email": email})["user_id"], {"Authorization": f"Bearer {r.json()['access_token']}"}


def _case():
    case_id = f"SA-T{uuid.uuid4().hex[:6].upper()}"
    _cases.append(case_id)
    (ua, ha), (ub, hb) = _user(), _user()
    db.joint_alignment_cases.insert_one({"case_id": case_id, "status": "pending",
                                         "parents": [{"parent_slot": "A", "user_id": ua}, {"parent_slot": "B", "user_id": ub}]})
    return case_id, ha, hb


def _admin():
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# An account with no align_ref is NOT written to on lookup (nothing touches live data until an admin runs the backfill).
def test_link_missing_align_ref_no_write_until_admin_backfill():
    case_id, ha, _ = _case()
    uid = db.joint_alignment_cases.find_one({"case_id": case_id})["parents"][0]["user_id"]
    db.users.update_one({"user_id": uid}, {"$unset": {"align_ref": ""}})
    url = f"{API}/family-checkin/link"
    assert httpx.get(url, headers=ha, timeout=20).json() == {"case_id": case_id}
    assert "align_ref" not in db.users.find_one({"user_id": uid})
    _, hp = _user()
    assert httpx.get(f"{API}/admin/align-refs", headers=hp, timeout=20).status_code == 403
    assert httpx.post(f"{API}/admin/align-refs/backfill", headers=hp, timeout=20).status_code == 403
    ha_admin = _admin()
    st = httpx.get(f"{API}/admin/align-refs", headers=ha_admin, timeout=20)
    assert st.status_code == 200 and st.json()["accounts_missing"] >= 1 and "no-store" in st.headers.get("cache-control", "")
    run = httpx.post(f"{API}/admin/align-refs/backfill", headers=ha_admin, timeout=60).json()
    assert run["users"] >= 1 and run["accounts_missing"] == 0 and run["case_entries_missing"] == 0
    ref = db.users.find_one({"user_id": uid})["align_ref"]
    assert httpx.get(url, headers=ha, timeout=20).json() == {"case_id": case_id}
    again = httpx.post(f"{API}/admin/align-refs/backfill", headers=ha_admin, timeout=60).json()
    assert again["users"] == 0 and db.users.find_one({"user_id": uid})["align_ref"] == ref


# The old in-app safety assessment is back: questions load, answers save, results and the PDF read back.
def test_old_safety_assessment_restored():
    uid, h = _user()
    from safety_assessment_routes import SECTION_1_QUESTIONS, SECTION_2_QUESTIONS
    assert httpx.get(f"{API}/safety-assessment/questions", headers=h, timeout=20).status_code == 200
    answers = {"section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
               "section_2": {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in SECTION_2_QUESTIONS}}
    r = httpx.post(f"{API}/safety-assessment", json=answers, headers=h, timeout=30)
    assert r.status_code == 200, r.text
    aid = r.json()["assessment_id"]
    me = httpx.get(f"{API}/safety-assessment/me", headers=h, timeout=20).json()
    assert me["assessment_id"] == aid and me["result"]["level"] == 4
    pdf = httpx.get(f"{API}/safety-assessment/{aid}/pdf", headers=h, timeout=30)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    db.safety_assessments.delete_many({"user_id": uid})
