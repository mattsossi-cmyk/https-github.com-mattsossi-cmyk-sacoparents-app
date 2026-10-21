"""Blocked Summary / Agreement share links: a clear page in a browser, JSON for scripts. Each reason has its own message."""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from auth import JWT_ALGO, JWT_SECRET, create_share_token  # noqa: E402
from mediation_sharing import OLD_LINK  # noqa: E402
from share_routes import COLLECTION as SHARE_TOKENS  # noqa: E402
from shared_link_page import EXPIRED, GONE, INVALID, SWITCHED_OFF  # noqa: E402
from tests.conftest import BASE_URL  # noqa: E402

API = f"{BASE_URL}/api/mediation/shared"
HTML = {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_jtis: list[str] = []


@pytest.fixture(scope="module")
def uid():
    email = f"test_sharedpage_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "Page Test",
                                                            "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=30)
    assert r.status_code == 200, r.text
    user_id = r.json()["user"]["user_id"]
    yield user_id
    _db.users.delete_many({"user_id": user_id})
    _db[SHARE_TOKENS].delete_many({"jti": {"$in": _jtis}})


def _expired_token(user_id):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    return jwt.encode({"kind": "share", "doc_type": "summary", "doc_id": "sum_x", "sub": user_id, "clean": 1,
                       "iat": past - timedelta(days=7), "exp": past}, JWT_SECRET, algorithm=JWT_ALGO)


def _revoked_token(user_id):
    token = create_share_token("agreement", "agr_x", user_id, extra_claims={"clean": 1})
    jti = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])["jti"]
    _jtis.append(jti)
    _db[SHARE_TOKENS].insert_one({"jti": jti, "user_id": user_id, "revoked_at": datetime.now(timezone.utc)})
    return token


CASES = [
    ("old", lambda u: create_share_token("summary", "sum_x", u), 410, OLD_LINK, "Made before a privacy update"),
    ("expired", _expired_token, 404, EXPIRED, "This link has expired"),
    ("invalid", lambda u: "not-a-real-token", 404, INVALID, "This link isn&#x27;t valid"),
    ("switched_off", _revoked_token, 404, SWITCHED_OFF, "This link was switched off"),
    ("gone", lambda u: create_share_token("summary", f"sum_missing_{uuid.uuid4().hex[:6]}", u, extra_claims={"clean": 1}),
     404, GONE, "No longer available"),
]


@pytest.mark.parametrize("name,make,status,message,title", CASES, ids=[c[0] for c in CASES])
def test_browser_gets_a_clear_page(uid, name, make, status, message, title):
    r = requests.get(f"{API}/{make(uid)}", headers=HTML, timeout=30)
    assert r.status_code == status
    assert r.headers["content-type"].startswith("text/html")
    assert "no-store" in r.headers.get("cache-control", "") and "noindex" in r.headers.get("x-robots-tag", "")
    page = r.text
    assert 'data-testid="shared-link-blocked-page"' in page
    assert f'data-testid="shared-link-blocked-title">{title}<' in page
    assert message.replace("'", "&#x27;") in page
    assert "{" not in page.split("<style>")[0] and "detail" not in page


@pytest.mark.parametrize("name,make,status,message,title", CASES, ids=[c[0] for c in CASES])
def test_scripts_still_get_json(uid, name, make, status, message, title):
    r = requests.get(f"{API}/{make(uid)}", timeout=30)
    assert r.status_code == status
    assert r.json() == {"detail": message}


def test_messages_are_all_different():
    assert len({OLD_LINK, EXPIRED, INVALID, SWITCHED_OFF, GONE}) == 5
