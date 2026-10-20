"""Iter116: Align link status (recent_reads), link-codes, safety redaction."""
import os
import time
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
SECRET = os.environ["INTEGRATION_SHARED_SECRET"]
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

PWD = "TestPass123!"


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, (email, r.status_code, r.text)
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


@pytest.fixture(scope="module")
def users(db):
    out = {}
    for em in ("parent1@test.com", "parent2@test.com", "journey6@test.com"):
        u = db.users.find_one({"email": em}, {"user_id": 1})
        assert u, em
        out[em] = u["user_id"]
    return out


def test_align_link_status_authenticated():
    tok = _login("parent2@test.com")
    r = requests.get(f"{BASE_URL}/api/integrations/align-link", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "linked" in data and "recent_reads" in data
    assert isinstance(data["recent_reads"], list)


def test_align_link_status_unauth():
    r = requests.get(f"{BASE_URL}/api/integrations/align-link", timeout=15)
    assert r.status_code in (401, 403)


def test_journey6_without_saved_result_can_mint():
    # No saved result -> never blocked (the old "take the screen first" rule is gone).
    tok = _login("journey6@test.com")
    r = requests.post(f"{BASE_URL}/api/link-codes", json={"context": "account"},
                      headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200, r.text


def test_parent2_mint_verify_link_and_history_cap_at_5(db, users):
    # Ensure parent2 is unlinked to start fresh
    db.align_links.update_many({"user_id": users["parent2@test.com"]},
                               {"$set": {"unlinked_at": __import__("datetime").datetime.utcnow()}})
    db.align_access_log.delete_many({"user_id": users["parent2@test.com"]})
    # Codes this test minted on earlier runs would trip the 5-per-hour limit when the suite is rerun.
    db.link_codes.delete_many({"user_id": users["parent2@test.com"]})

    tok = _login("parent2@test.com")
    # Mint link code
    r = requests.post(f"{BASE_URL}/api/link-codes", json={"context": "account"},
                     headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    assert len(code) == 9  # SA-XXXXXX

    # Verify via server-to-server
    r = requests.post(f"{BASE_URL}/api/integrations/verify-link-code",
                     json={"code": code},
                     headers={"X-Integration-Key": SECRET}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["email"].lower() == "parent2@test.com"

    # Status now linked
    r = requests.get(f"{BASE_URL}/api/integrations/align-link",
                    headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200
    status = r.json()
    assert status["linked"] is True
    assert status["linked_at"]

    # Trigger 6 reads
    for _ in range(6):
        rr = requests.get(f"{BASE_URL}/api/integrations/export-assessments?email=parent2@test.com",
                         headers={"X-Integration-Key": SECRET}, timeout=15)
        assert rr.status_code == 200, rr.text
        time.sleep(0.05)

    # Status returns only 5 reads
    r = requests.get(f"{BASE_URL}/api/integrations/align-link",
                    headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    status = r.json()
    assert len(status["recent_reads"]) == 5
    assert status["last_read_at"]
    for read in status["recent_reads"]:
        assert read["what"] == "Your Situation Snapshot, Foundation Statement and Special Needs summaries"
        assert read["redacted"] is False
    # Ensure newest first
    times = [r["at"] for r in status["recent_reads"]]
    assert times == sorted(times, reverse=True)


def test_parent1_safety_flagged_reads_redacted(db, users):
    # Ensure parent1 is linked
    uid1 = users["parent1@test.com"]
    link = db.align_links.find_one({"user_id": uid1, "unlinked_at": None})
    if not link:
        # Mint & verify
        tok1 = _login("parent1@test.com")
        # parent1 is safety flagged; minting likely blocked. Insert link directly.
        import datetime as dt
        db.align_links.update_one(
            {"user_id": uid1},
            {"$set": {"email": "parent1@test.com", "linked_at": dt.datetime.utcnow(), "unlinked_at": None, "context": "account"}},
            upsert=True,
        )
    db.align_access_log.delete_many({"user_id": uid1})
    # export - should be redacted
    r = requests.get(f"{BASE_URL}/api/integrations/export-assessments?email=parent1@test.com",
                    headers={"X-Integration-Key": SECRET}, timeout=15)
    assert r.status_code == 200, r.text
    assert "redacted_for_safety" not in r.json()

    # PDF - same reply as "nothing saved yet" for a held-back parent
    r = requests.get(f"{BASE_URL}/api/integrations/foundation-statement.pdf?email=parent1@test.com",
                    headers={"X-Integration-Key": SECRET}, timeout=15)
    assert r.status_code == 409, r.text

    tok = _login("parent1@test.com")
    r = requests.get(f"{BASE_URL}/api/integrations/align-link",
                    headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    status = r.json()
    assert status["linked"] is True
    assert len(status["recent_reads"]) >= 2
    # Find labels and notes
    export_r = next(r for r in status["recent_reads"] if r["what"].startswith("Your Situation Snapshot"))
    assert export_r["redacted"] is True
    assert export_r["note"] == "Not shared"
    pdf_r = next(r for r in status["recent_reads"] if r["what"] == "Your Foundation Statement PDF")
    assert pdf_r["redacted"] is True
    assert pdf_r["note"] == "Not shared"


def test_cleanup_leave_parent1_linked_parent2_unlinked(db, users):
    import datetime as dt
    # Unlink parent2
    db.align_links.update_many({"user_id": users["parent2@test.com"], "unlinked_at": None},
                               {"$set": {"unlinked_at": dt.datetime.utcnow()}})
    # Ensure parent1 linked
    db.align_links.update_one(
        {"user_id": users["parent1@test.com"]},
        {"$set": {"email": "parent1@test.com", "linked_at": dt.datetime.utcnow(), "unlinked_at": None}},
        upsert=True,
    )
    p1 = db.align_links.find_one({"user_id": users["parent1@test.com"], "unlinked_at": None})
    p2 = db.align_links.find_one({"user_id": users["parent2@test.com"], "unlinked_at": None})
    assert p1 is not None
    assert p2 is None
