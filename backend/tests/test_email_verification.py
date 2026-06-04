"""Backend tests for email verification (soft-nudge) flow.

Covers:
- Register sets email_verified=false and issues a magic_links row mode=verify
- UserPublic.email_verified field on TokenResponse and /me
- POST /verify-email/send requires auth, rate-limit, already-verified shortcut, guest reject
- POST /verify-email/confirm valid / used / bogus / wrong-mode handling
- Auto-verification via magic-link consume and password-reset confirm
"""
import os
import re
import uuid
import time
import pytest
import requests
import subprocess

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _mongo():
    """Direct mongo access for assertions / cleanup."""
    from pymongo import MongoClient
    mongo_url = "mongodb://localhost:27017"
    db_name = "test_database"
    with open("/app/backend/.env") as f:
        for line in f:
            line = line.strip()
            if line.startswith("MONGO_URL="):
                mongo_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("DB_NAME="):
                db_name = line.split("=", 1)[1].strip().strip('"').strip("'")
    c = MongoClient(mongo_url)
    return c[db_name]


def _register_unverified():
    """Create a fresh unverified user. Returns (email, token, user, user_id)."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_verify_{suffix}@test.com"
    payload = {"email": email, "password": "TestPass123!", "name": "Verify Tester"}
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return email, data["access_token"], data["user"], data["user"]["user_id"]


def _grep_token_for(email, mode="verify"):
    """Extract latest verification/magic-link/reset token from backend logs."""
    out = subprocess.run(
        ["bash", "-c",
         "tail -n 600 /var/log/supervisor/backend.err.log /var/log/supervisor/backend.out.log 2>/dev/null"],
        capture_output=True, text=True
    ).stdout
    if mode == "verify":
        # message includes: "Verification link generated but SMTP not configured. Link for <email>: <url>"
        pattern = r"Verification link generated.*?Link for " + re.escape(email) + r": \S*/verify-email\?token=(\S+)"
    elif mode == "magic":
        pattern = r"Magic link generated.*?Link for " + re.escape(email) + r": \S*token=(\S+)"
    elif mode == "reset":
        pattern = r"Password reset.*?Link for " + re.escape(email) + r": \S*token=(\S+)"
    else:
        return None
    matches = re.findall(pattern, out)
    return matches[-1] if matches else None


@pytest.fixture
def cleanup_users():
    created = []
    yield created
    db = _mongo()
    for u in created:
        db.users.delete_many({"email": u})
        db.magic_links.delete_many({"email": u})


class TestRegisterAndVerifiedField:
    def test_register_sets_email_verified_false_and_creates_verify_link(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # UserPublic returns email_verified=false
        assert user["email_verified"] is False, user
        # magic_links row with mode=verify created
        db = _mongo()
        row = db.magic_links.find_one({"user_id": user_id, "mode": "verify"})
        assert row is not None, "No magic_links row with mode=verify"
        assert row["used"] is False
        assert row["email"] == email.lower()

    def test_me_returns_email_verified_field(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        # `/me` returns the user object directly (not wrapped in token)
        u = data.get("user", data)
        assert "email_verified" in u
        assert u["email_verified"] is False


class TestVerifyEmailSendEndpoint:
    def test_send_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/auth/verify-email/send", timeout=15)
        assert r.status_code == 401, r.text

    def test_send_unverified_user_returns_ok_and_creates_row(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # Wipe pre-existing rows so we can detect the new one
        _mongo().magic_links.delete_many({"user_id": user_id})
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/send",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert "sent" in body
        assert isinstance(body["sent"], bool)
        assert "message" in body
        row = _mongo().magic_links.find_one({"user_id": user_id, "mode": "verify"})
        assert row is not None

    def test_send_already_verified_returns_already_verified(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # Flip flag directly
        _mongo().users.update_one(
            {"user_id": user_id}, {"$set": {"email_verified": True}}
        )
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/send",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body.get("already_verified") is True

    def test_send_rate_limit_4th_call(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # Already 1 row exists from register. Call 3 more times = 4 in last hour.
        # Spec says rate limit is 3/hour -> 4th call 429.
        last_status = None
        last_body = None
        for i in range(4):
            r = requests.post(
                f"{BASE_URL}/api/auth/verify-email/send",
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            )
            last_status = r.status_code
            last_body = r.text
        assert last_status == 429, f"Expected 429 on 4th call, got {last_status}: {last_body}"
        assert "Too many" in last_body

    def test_send_guest_returns_400(self, cleanup_users):
        # Create a guest session
        r = requests.post(f"{BASE_URL}/api/auth/guest", timeout=15)
        assert r.status_code == 200, r.text
        guest = r.json()
        guest_token = guest["access_token"]
        cleanup_users.append(guest["user"]["email"])
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/send",
            headers={"Authorization": f"Bearer {guest_token}"},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "Guest" in r.text


class TestVerifyEmailConfirmEndpoint:
    def test_confirm_valid_token_marks_verified(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # Read latest mode=verify token directly from DB to avoid log races
        row = _mongo().magic_links.find_one(
            {"user_id": user_id, "mode": "verify", "used": False},
            sort=[("created_at", -1)],
        )
        assert row, "no verify token in DB after register"
        raw_token = row["token"]
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/confirm",
            json={"token": raw_token}, timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body.get("email") == email.lower()
        # Persisted
        u = _mongo().users.find_one({"user_id": user_id})
        assert u["email_verified"] is True
        assert "email_verified_at" in u

    def test_confirm_used_token_idempotent(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        row = _mongo().magic_links.find_one(
            {"user_id": user_id, "mode": "verify"}, sort=[("created_at", -1)]
        )
        raw_token = row["token"]
        # First consume
        r1 = requests.post(
            f"{BASE_URL}/api/auth/verify-email/confirm",
            json={"token": raw_token}, timeout=20,
        )
        assert r1.status_code == 200
        # Second consume
        r2 = requests.post(
            f"{BASE_URL}/api/auth/verify-email/confirm",
            json={"token": raw_token}, timeout=20,
        )
        assert r2.status_code == 200, r2.text
        assert r2.json().get("already_used") is True

    def test_confirm_bogus_token_returns_400(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/confirm",
            json={"token": "totally-bogus-token-" + uuid.uuid4().hex},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "Invalid" in r.text or "expired" in r.text

    def test_confirm_wrong_mode_token_returns_400(self, cleanup_users):
        # Request a password reset to mint a reset token, then try to consume it as verify
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        rr = requests.post(
            f"{BASE_URL}/api/auth/password-reset/request",
            json={"email": email}, timeout=20,
        )
        assert rr.status_code == 200
        # Grab the freshest mode=reset token
        # the reset endpoint stores its rows under collection magic_links or its own col
        # locate by user_id and mode
        reset_row = _mongo().magic_links.find_one(
            {"user_id": user_id, "mode": {"$in": ["reset", "password_reset"]}},
            sort=[("created_at", -1)],
        )
        if not reset_row:
            pytest.skip("Password-reset doesn't use magic_links collection; skip wrong-mode test.")
        r = requests.post(
            f"{BASE_URL}/api/auth/verify-email/confirm",
            json={"token": reset_row["token"]}, timeout=15,
        )
        assert r.status_code == 400


class TestAutoVerification:
    def test_password_reset_confirm_sets_email_verified_true(self, cleanup_users):
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        # request reset
        rr = requests.post(
            f"{BASE_URL}/api/auth/password-reset/request",
            json={"email": email}, timeout=20,
        )
        assert rr.status_code == 200
        reset_row = _mongo().magic_links.find_one(
            {"user_id": user_id, "mode": {"$in": ["reset", "password_reset"]}},
            sort=[("created_at", -1)],
        )
        if not reset_row:
            pytest.skip("Password-reset not in magic_links collection; cannot test auto-verify here.")
        rc = requests.post(
            f"{BASE_URL}/api/auth/password-reset/confirm",
            json={"token": reset_row["token"], "password": "NewPass123!"},
            timeout=20,
        )
        assert rc.status_code == 200, rc.text
        u = _mongo().users.find_one({"user_id": user_id})
        assert u.get("email_verified") is True, "password reset should auto-verify email"

    def test_magic_link_consume_sets_email_verified_true(self, cleanup_users):
        """Direct DB-insert path: magic-link/request can return 503 when SMTP isn't configured,
        so we insert a magic_links row directly to exercise the consume endpoint's
        auto-verification side-effect."""
        from datetime import datetime, timezone, timedelta
        import secrets as _secrets
        email, token, user, user_id = _register_unverified()
        cleanup_users.append(email)
        db = _mongo()
        db.users.update_one({"user_id": user_id}, {"$set": {"email_verified": False}})
        # Insert magic-link row directly. Try several plausible mode values.
        raw = _secrets.token_urlsafe(32)
        for mode_value in ("magic", "login", "signin", "magic_link"):
            db.magic_links.delete_many({"token": raw})
            db.magic_links.insert_one({
                "token": raw,
                "email": email.lower(),
                "user_id": user_id,
                "mode": mode_value,
                "used": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            })
            rc = requests.post(
                f"{BASE_URL}/api/auth/magic-link/consume",
                json={"token": raw}, timeout=20,
            )
            if rc.status_code == 200:
                body = rc.json()
                assert body["user"]["email_verified"] is True
                u = db.users.find_one({"user_id": user_id})
                assert u["email_verified"] is True
                return
        pytest.fail(
            f"magic-link/consume rejected token under all tried modes. Last response: {rc.status_code} {rc.text}"
        )
