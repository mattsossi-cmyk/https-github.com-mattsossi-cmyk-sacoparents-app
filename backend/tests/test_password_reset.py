"""Password reset flow tests (forgot-password + reset-password)."""
import os
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

KNOWN_CODE = "654321"
KNOWN_CODE_HASH = hashlib.sha256(KNOWN_CODE.encode()).hexdigest()


@pytest.fixture(scope="module")
def mongo_db():
    client = pymongo.MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _register_user(email=None, password=None):
    email = email or f"pwreset_{uuid.uuid4().hex[:8]}@example.com"
    password = password or f"Pw!{uuid.uuid4().hex[:12]}"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": "Reset User", "email": email, "password": password, "role": "professional"
    })
    assert r.status_code == 200, r.text
    return email, password


def _set_known_code(db, email, expires_at=None):
    expires = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=10))
    db.password_resets.update_one(
        {"email": email.lower()},
        {"$set": {
            "email": email.lower(),
            "code_hash": KNOWN_CODE_HASH,
            "expires_at": expires,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


class TestForgotPassword:
    def test_forgot_password_registered_email_returns_ok(self, mongo_db):
        email, _ = _register_user()
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        assert r.json().get("ok")
        # code hash stored
        doc = mongo_db.password_resets.find_one({"email": email.lower()})
        assert doc is not None
        assert "code_hash" in doc

    def test_forgot_password_unknown_email_no_enumeration(self) -> None:
        unknown = f"noone_{uuid.uuid4().hex[:8]}@nowhere.example"
        r = requests.post(f"{API}/auth/forgot-password", json={"email": unknown})
        assert r.status_code == 200
        assert r.json().get("ok")


class TestResetPassword:
    def test_reset_happy_path_and_login_with_new_password(self, mongo_db):
        email, _ = _register_user()
        # Kick off forgot to ensure doc created path exercised, then overwrite hash
        requests.post(f"{API}/auth/forgot-password", json={"email": email})
        _set_known_code(mongo_db, email)

        new_pw = "NewPass1234!"
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": new_pw})
        assert r.status_code == 200, r.text

        # Login with new password
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pw})
        assert r.status_code == 200

        # Code is single-use: reuse fails
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": "AnotherPw123"})
        assert r.status_code == 400

    def test_reset_wrong_code_returns_400(self, mongo_db):
        email, _ = _register_user()
        _set_known_code(mongo_db, email)
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": "000000", "new_password": "SomePass123"})
        assert r.status_code == 400

    def test_reset_expired_code_returns_400(self, mongo_db):
        email, _ = _register_user()
        _set_known_code(mongo_db, email, expires_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": "SomePass123"})
        assert r.status_code == 400

    def test_reset_short_password_returns_400(self, mongo_db):
        email, _ = _register_user()
        _set_known_code(mongo_db, email)
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": "short"})
        assert r.status_code == 400

    def test_reset_no_code_document_returns_400(self, mongo_db):
        email, _ = _register_user()
        # Ensure no doc
        mongo_db.password_resets.delete_many({"email": email.lower()})
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": "SomePass123"})
        assert r.status_code == 400

    def test_reset_clears_login_lockout(self, mongo_db):
        email, orig_pw = _register_user()
        # Trigger 5 failed logins to cause lockout
        for _ in range(6):
            requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong-pass!"})
        # Now reset password
        _set_known_code(mongo_db, email)
        new_pw = "FreshPass987"
        r = requests.post(f"{API}/auth/reset-password",
                          json={"email": email, "code": KNOWN_CODE, "new_password": new_pw})
        assert r.status_code == 200
        # Login should succeed (lockout cleared)
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pw})
        assert r.status_code == 200
