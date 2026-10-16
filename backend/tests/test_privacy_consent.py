"""Privacy Notice consent: required at every account-creation endpoint, recorded per user, re-asked on version change."""
import hashlib
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from privacy_consent import PRIVACY_NOTICE_TEXT_SHA256, PRIVACY_NOTICE_VERSION, has_current_consent  # noqa: E402

API = "http://localhost:8001/api"
NOTICE_FILE = ROOT.parent / "frontend/src/pages/privacyNotice/PrivacyNoticeContent.jsx"
BOTH = {"ack_privacy_notice": True, "consent_sensitive_info": True}
FIELDS = ("ack_privacy_notice", "consent_sensitive_info", "privacy_notice_version", "consent_at")

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails = []


def _email(tag):
    e = f"test_consent_{tag}_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(e)
    return e


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    ids = [u["user_id"] for u in db.users.find({"email": {"$in": _emails}}, {"user_id": 1})]
    db.users.delete_many({"email": {"$in": _emails}})
    db.privacy_consents.delete_many({"user_id": {"$in": ids}})
    db.legal_acknowledgments.delete_many({"user_id": {"$in": ids}})
    db.magic_links.delete_many({"email": {"$in": _emails}})
    db.coparent_invites.delete_many({"invitee_email": {"$in": _emails}})


def _register(email, **extra):
    return httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Consent Test", **extra}, timeout=20)


def _assert_saved(email, before):
    doc = db.users.find_one({"email": email})
    assert all(k in doc for k in FIELDS)
    assert doc["ack_privacy_notice"] is True and doc["consent_sensitive_info"] is True
    assert doc["privacy_notice_version"] == PRIVACY_NOTICE_VERSION
    at = datetime.fromisoformat(doc["consent_at"])
    assert at.tzinfo is not None and before - timedelta(seconds=5) <= at <= datetime.now(timezone.utc) + timedelta(seconds=5)
    return doc


@pytest.mark.parametrize("extra", [{}, {"ack_privacy_notice": True}, {"consent_sensitive_info": True}, {"ack_privacy_notice": False, "consent_sensitive_info": False}])
def test_register_rejected_without_both_boxes(extra):
    email = _email("reject")
    r = _register(email, **extra)
    assert r.status_code == 422
    assert db.users.find_one({"email": email}) is None


def test_register_with_both_saves_four_fields_and_ignores_client_timestamp():
    email = _email("ok")
    before = datetime.now(timezone.utc)
    r = _register(email, **BOTH, consent_at="1999-01-01T00:00:00+00:00", privacy_notice_version="old")
    assert r.status_code == 200, r.text
    assert r.json()["user"]["consent_current"] is True
    doc = _assert_saved(email, before)
    assert db.privacy_consents.count_documents({"user_id": doc["user_id"], "source": "register"}) == 1
    assert db.legal_acknowledgments.count_documents({"user_id": doc["user_id"], "version": "v1"}) == 1


def test_guest_claim_requires_both_then_saves():
    s = httpx.Client(timeout=20)
    g = s.post(f"{API}/auth/guest", json={})
    assert g.status_code == 200
    assert g.json()["user"]["consent_current"] is False
    hdr = {"Authorization": f"Bearer {g.json()['access_token']}"}
    email = _email("claim")
    base = {"email": email, "password": "Str0ng!Pass99", "name": "Claim Test"}
    assert s.post(f"{API}/auth/claim", json={**base, "ack_privacy_notice": True}, headers=hdr).status_code == 422
    before = datetime.now(timezone.utc)
    r = s.post(f"{API}/auth/claim", json={**base, **BOTH}, headers=hdr)
    assert r.status_code == 200, r.text
    _assert_saved(email, before)


def test_signup_from_token_requires_both():
    email = _email("magic")
    token = uuid.uuid4().hex
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db.magic_links.insert_one({"token": token, "email": email, "mode": "signup", "expires_at": exp})
    body = {"token": token, "name": "Magic Test", "password": "Str0ng!Pass99"}
    assert httpx.post(f"{API}/auth/signup-from-token", json=body, timeout=20).status_code == 422
    assert db.users.find_one({"email": email}) is None
    before = datetime.now(timezone.utc)
    r = httpx.post(f"{API}/auth/signup-from-token", json={**body, **BOTH}, timeout=20)
    assert r.status_code == 200, r.text
    _assert_saved(email, before)


def test_coparent_invite_accept_requires_both():
    email = _email("invite")
    token = uuid.uuid4().hex
    exp = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    db.coparent_invites.insert_one({"token": token, "invitee_email": email, "expires_at": exp, "status": "pending", "inviter_user_id": "test_inviter"})
    body = {"name": "Invite Test", "password": "Str0ng!Pass99"}
    assert httpx.post(f"{API}/invites/coparent/accept/{token}", json={**body, "consent_sensitive_info": True}, timeout=20).status_code == 422
    assert db.users.find_one({"email": email}) is None
    before = datetime.now(timezone.utc)
    r = httpx.post(f"{API}/invites/coparent/accept/{token}", json={**body, **BOTH}, timeout=20)
    assert r.status_code == 200, r.text
    _assert_saved(email, before)


def test_existing_user_reconsent_keeps_data():
    email = _email("existing")
    uid = f"user_test_{uuid.uuid4().hex[:10]}"
    original = {"user_id": uid, "email": email, "name": "Existing", "hashed_password": None, "auth_method": "jwt",
                "children": [{"name": "A", "age": "7"}], "custody_situation": "50/50", "created_at": "2026-01-01T00:00:00+00:00"}
    db.users.insert_one(dict(original))
    import jwt  # noqa: PLC0415
    token = jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, os.environ["JWT_SECRET"], algorithm=os.environ.get("JWT_ALGORITHM", "HS256"))
    hdr = {"Authorization": f"Bearer {token}"}
    assert httpx.get(f"{API}/auth/me", headers=hdr, timeout=20).json()["consent_current"] is False
    assert httpx.post(f"{API}/privacy-consent", json={"ack_privacy_notice": True}, headers=hdr, timeout=20).status_code == 422
    assert httpx.post(f"{API}/privacy-consent", json={}, timeout=20).status_code == 401
    before = datetime.now(timezone.utc)
    r = httpx.post(f"{API}/privacy-consent", json=BOTH, headers=hdr, timeout=20)
    assert r.status_code == 200, r.text
    doc = _assert_saved(email, before)
    assert all(doc[k] == v for k, v in original.items())
    assert httpx.get(f"{API}/auth/me", headers=hdr, timeout=20).json()["consent_current"] is True


def test_version_change_asks_again():
    ok = {"ack_privacy_notice": True, "consent_sensitive_info": True, "privacy_notice_version": PRIVACY_NOTICE_VERSION}
    assert has_current_consent(ok)
    assert not has_current_consent({**ok, "privacy_notice_version": "2026-01-01-v0"})
    assert not has_current_consent({})


def test_notice_text_change_requires_version_bump():
    digest = hashlib.sha256(NOTICE_FILE.read_bytes()).hexdigest()
    assert digest == PRIVACY_NOTICE_TEXT_SHA256, (
        "Privacy Notice text changed: bump PRIVACY_NOTICE_VERSION and update PRIVACY_NOTICE_TEXT_SHA256 in backend/privacy_consent.py"
    )
