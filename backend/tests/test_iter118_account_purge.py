"""Iter 118 backend tests: account purge, court-keys integration, auto-tick, checklist PDF."""
from __future__ import annotations

import io
import os
import subprocess
import uuid
import secrets
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET", "")

PASSWORD = "TestPass123!"


def _mk_email() -> str:
    return f"iter118_{uuid.uuid4().hex[:10]}@example.com"


def _register(email: str) -> dict:
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "name": "Iter 118"})
    assert r.status_code == 200, r.text
    data = r.json()
    return {"token": data["access_token"], "user_id": data["user"]["user_id"], "email": email}


def _auth(h):
    return {"Authorization": f"Bearer {h['token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    import asyncio
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------- Feature 1: Account Purge ---------- #
class TestAccountPurge:
    def test_full_purge_and_shared_scrub(self, db):
        user = _register(_mk_email())
        other = _register(_mk_email())
        uid = user["user_id"]
        other_uid = other["user_id"]
        email = user["email"]

        # Seed various owned data via API
        r = requests.put(f"{API}/portal/state", headers=_auth(user),
                         json={"court_key": "", "court_legal_name": "Test Parent"})
        assert r.status_code == 200
        r = requests.put(f"{API}/court-path/requested", headers=_auth(user), json={"keys": ["self", "foundation"]})
        assert r.status_code == 200

        # Insert joint case and court agreement directly in Mongo
        case_id = f"TEST-CASE-{uuid.uuid4().hex[:8]}"
        _run_async(db.joint_alignment_cases.insert_one({
            "case_id": case_id,
            "status": "active",
            "parents": [
                {"user_id": uid, "email": email, "name": "Iter 118", "invitation_token": "tok-a",
                 "assessment_ref": "ref", "step_completions": [{"foo": 1}]},
                {"user_id": other_uid, "email": other["email"], "name": "Other", "invitation_token": "tok-b"},
            ],
            "professional": {"id": None, "email": "", "name": ""},
            "assessment_type": "co-parenting",
            "assigned_steps": [],
        }))
        agreement_id = f"TEST-AGR-{uuid.uuid4().hex[:8]}"
        _run_async(db.court_agreements.insert_one({
            "agreement_id": agreement_id,
            "marked_by": [uid, other_uid],
            "agreed_at": "now",
        }))

        # Insert a compliance log doc with name/email/user_id
        _run_async(db.phi_access_log.insert_one({
            "user_id": uid, "email": email, "name": "Iter 118",
            "ip": "1.2.3.4", "user_agent": "test", "at": "now",
        }))

        # Insert a sent secure document
        from bson.objectid import ObjectId
        file_id = ObjectId()
        # Insert a fake GridFS file (manually via files collection; chunk omitted for test)
        _run_async(db["secure_doc_files.files"].insert_one({"_id": file_id, "filename": "x.pdf", "length": 0, "chunkSize": 1, "uploadDate": datetime.now(timezone.utc)}))
        _run_async(db.secure_documents.insert_one({
            "doc_id": "doc-" + uuid.uuid4().hex[:8],
            "sender_user_id": uid,
            "recipient_email": "x@y.com",
            "token": "tok-" + uuid.uuid4().hex[:8],
            "files": [{"file_id": file_id, "filename": "x.pdf"}],
            "created_at": "now",
        }))

        # Delete account
        r = requests.delete(f"{API}/auth/account", headers=_auth(user))
        assert r.status_code == 200, r.text
        resp = r.json()
        assert resp.get("ok") is True
        assert "deleted" in resp

        # Login must fail
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 401

        # Scan all collections for leftover identifiers
        collections = _run_async(db.list_collection_names())
        compliance = {"phi_access_log", "legal_acknowledgments", "hb300_acknowledgements", "hb300_access_requests"}
        leaks = []
        for coll in collections:
            if coll.startswith("system.") or coll in compliance:
                continue
            # Shared-scrub collections may still contain docs but not this uid
            # or the email as the owner. joint_alignment_cases keeps the doc but scrubs the slot.
            if coll in {"joint_alignment_cases", "court_agreements"}:
                continue
            found = _run_async(db[coll].count_documents({"$or": [
                {"user_id": uid}, {"parent_id": uid}, {"sender_user_id": uid},
                {"creator_user_id": uid}, {"email": email}
            ]}))
            if found:
                leaks.append((coll, found))
        assert not leaks, f"Leftover docs after purge: {leaks}"

        # Joint case: the deleting parent's slot is anonymised
        case = _run_async(db.joint_alignment_cases.find_one({"case_id": case_id}))
        assert case is not None, "joint case should still exist"
        parents_by_name = {p.get("name"): p for p in case["parents"]}
        assert "A parent deleted their account" in parents_by_name, parents_by_name.keys()
        del_slot = parents_by_name["A parent deleted their account"]
        assert del_slot["user_id"] is None
        assert del_slot["email"] == ""
        assert del_slot["invitation_token"] is None
        # Other parent untouched
        other_slot = next(p for p in case["parents"] if p.get("user_id") == other_uid)
        assert other_slot["email"] == other["email"]

        # Court agreement: marked_by keeps only the other id
        agr = _run_async(db.court_agreements.find_one({"agreement_id": agreement_id}))
        assert agr["marked_by"] == [other_uid]

        # Compliance: anonymised, not deleted
        from account_purge import anon_id as _anon_fn
        expected_anon = _anon_fn(uid)
        anon_hash = _run_async(db.phi_access_log.find_one({"user_id": expected_anon}))
        assert anon_hash is not None, "compliance log should still exist with anonymised id"
        assert anon_hash.get("email") is None
        assert "name" not in anon_hash
        assert "ip" not in anon_hash

        # account_deletions record created, no PII
        ad = _run_async(db.account_deletions.find_one({"anon_id": expected_anon}))
        assert ad is not None
        assert "email" not in ad
        assert "name" not in ad
        assert "deleted_at" in ad

        # Secure doc + GridFS files removed
        docs_left = _run_async(db.secure_documents.count_documents({"sender_user_id": uid}))
        assert docs_left == 0
        gridfs_left = _run_async(db["secure_doc_files.files"].count_documents({"_id": file_id}))
        assert gridfs_left == 0

        # Cleanup other user and joint/agr docs
        _run_async(db.joint_alignment_cases.delete_one({"case_id": case_id}))
        _run_async(db.court_agreements.delete_one({"agreement_id": agreement_id}))
        _run_async(db.phi_access_log.delete_many({"user_id": expected_anon}))
        _run_async(db.account_deletions.delete_many({"anon_id": expected_anon}))
        requests.delete(f"{API}/auth/account", headers=_auth(other))


# ---------- Feature 2: court-keys integration ---------- #
class TestCourtKeysIntegration:
    def test_requires_integration_key(self):
        r = requests.post(f"{API}/integrations/court-keys", json={
            "key": "testkey_" + uuid.uuid4().hex[:6], "case_id": "C1", "mediator_name": "M", "requested": []
        })
        assert r.status_code == 401

    def test_invalid_requested_value(self):
        r = requests.post(f"{API}/integrations/court-keys",
                          headers={"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"},
                          json={"key": "k_" + uuid.uuid4().hex[:6], "case_id": "C1", "mediator_name": "M",
                                "requested": ["bogus"]})
        assert r.status_code == 422

    def test_upsert_and_autotick(self, db):
        user = _register(_mk_email())
        case_id = f"IT118-COURT-{uuid.uuid4().hex[:6]}"
        key_plain = "sa_" + uuid.uuid4().hex[:10]
        # Parent sets portal_state.court_key = case_id
        r = requests.put(f"{API}/portal/state", headers=_auth(user),
                         json={"court_key": case_id, "court_legal_name": "Testy"})
        assert r.status_code == 200
        # Insert court key via integration endpoint
        r = requests.post(f"{API}/integrations/court-keys",
                          headers={"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"},
                          json={"key": key_plain, "case_id": case_id, "mediator_name": "Jane Mediator",
                                "requested": ["medical", "self", "educational"]})
        assert r.status_code == 200, r.text

        # GET /api/court-path/requested -> auto-ticked
        r = requests.get(f"{API}/court-path/requested", headers=_auth(user))
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(data["keys"]) == {"medical", "self", "educational"}
        assert set(data["professional_keys"]) == {"medical", "self", "educational"}
        assert data["professional_name"] == "Jane Mediator"

        # Untick one -> stays unticked (source applied once)
        r = requests.put(f"{API}/court-path/requested", headers=_auth(user),
                         json={"keys": ["medical", "educational"]})
        assert r.status_code == 200
        r = requests.get(f"{API}/court-path/requested", headers=_auth(user))
        data = r.json()
        assert set(data["keys"]) == {"medical", "educational"}, data
        assert set(data["professional_keys"]) == {"medical", "self", "educational"}

        # Cleanup
        _run_async(db.portal_court_keys.delete_many({"case_id": case_id}))
        requests.delete(f"{API}/auth/account", headers=_auth(user))


# ---------- Feature 2b: joint-case auto-tick ---------- #
class TestJointCaseAutotick:
    def test_assigned_steps_required_only(self, db):
        user = _register(_mk_email())
        case_id = f"IT118-JOINT-{uuid.uuid4().hex[:6]}"
        _run_async(db.joint_alignment_cases.insert_one({
            "case_id": case_id,
            "status": "active",
            "parents": [{"user_id": user["user_id"], "email": user["email"], "name": "P"}],
            "professional": {"name": "Dr Pro"},
            "assessment_type": "co-parenting",
            "assigned_steps": [
                {"assessment_type": "medical", "required": True},
                {"assessment_type": "communication", "required": True},
                {"assessment_type": "educational", "required": False},
            ],
        }))
        r = requests.get(f"{API}/court-path/requested", headers=_auth(user))
        assert r.status_code == 200
        data = r.json()
        assert set(data["keys"]) == {"self", "medical"}, data
        assert data["professional_name"] == "Dr Pro"

        _run_async(db.joint_alignment_cases.delete_one({"case_id": case_id}))
        requests.delete(f"{API}/auth/account", headers=_auth(user))

    def test_fallback_to_assessment_type(self, db):
        user = _register(_mk_email())
        case_id = f"IT118-JOINT-{uuid.uuid4().hex[:6]}"
        _run_async(db.joint_alignment_cases.insert_one({
            "case_id": case_id, "status": "active",
            "parents": [{"user_id": user["user_id"], "email": user["email"], "name": "P"}],
            "professional": {"name": "Dr Pro"},
            "assessment_type": "psychological",
            "assigned_steps": [],
        }))
        r = requests.get(f"{API}/court-path/requested", headers=_auth(user))
        data = r.json()
        assert set(data["keys"]) == {"psychological"}, data

        _run_async(db.joint_alignment_cases.delete_one({"case_id": case_id}))
        requests.delete(f"{API}/auth/account", headers=_auth(user))


# ---------- Feature 3: Requested checklist PDF ---------- #
class TestChecklistPDF:
    def _pdftext(self, blob: bytes) -> str:
        p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=blob, capture_output=True)
        return p.stdout.decode("utf-8", errors="replace")

    def test_pdf_with_ticks_shows_only_requested(self, db):
        user = _register(_mk_email())
        requests.put(f"{API}/court-path/requested", headers=_auth(user), json={"keys": ["medical", "self", "parallel"]})
        r = requests.post(f"{API}/court-path/checklist/pdf", headers=_auth(user), json={"modules": {}})
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = self._pdftext(r.content)
        assert "Case code verified" in text
        assert "Safety check" in text
        assert "asked for" in text  # from the italic note
        assert "Module A" not in text and "Module B" not in text and "Module C" not in text
        assert "BIFF" not in text
        assert "Medical" in text
        assert "Self-Assessment" in text
        assert "Parallel Parenting Plan" in text
        requests.delete(f"{API}/auth/account", headers=_auth(user))

    def test_pdf_without_ticks_shows_full_list(self, db):
        user = _register(_mk_email())
        # No ticks + wipe any auto-tick (no case assigned)
        r = requests.put(f"{API}/court-path/requested", headers=_auth(user), json={"keys": []})
        assert r.status_code == 200
        r = requests.post(f"{API}/court-path/checklist/pdf", headers=_auth(user),
                         json={"modules": {"foundation": "not_yet", "coparenting": "not_yet", "safety": "not_yet"}})
        assert r.status_code == 200
        text = self._pdftext(r.content)
        assert "Module A" in text
        assert "Module B" in text
        assert "Module C" in text
        assert "Self-Assessment" in text
        assert "BIFF" in text
        requests.delete(f"{API}/auth/account", headers=_auth(user))

    def test_checklist_json_card_unchanged(self):
        user = _register(_mk_email())
        r = requests.post(f"{API}/court-path/checklist", headers=_auth(user),
                         json={"modules": {"foundation": "not_yet", "coparenting": "not_yet", "safety": "not_yet"}})
        assert r.status_code == 200
        data = r.json()
        keys = {i["key"] for i in data["items"]}
        for k in ("card1", "card2", "card3", "card4"):
            assert k in keys, f"missing {k}"
        requests.delete(f"{API}/auth/account", headers=_auth(user))
