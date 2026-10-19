"""While ALIGN_WEBHOOK_SECRET is unset the Safety Gate webhook is off: every call gets 503 and nothing changes."""
import hashlib
import hmac
import json
import os
import secrets
import time

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
if os.environ.get("ALIGN_WEBHOOK_SECRET"):
    pytest.skip("ALIGN_WEBHOOK_SECRET is set: webhook is on", allow_module_level=True)

API = "http://localhost:8001/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _admin():
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_webhook_refuses_everything_and_changes_nothing():
    before = db["case_safety"].count_documents({})
    case_id = f"SA-OFF{secrets.token_hex(3).upper()}"
    raw = json.dumps({"case_id": case_id, "safety_mode": "restricted", "set_by": "professional", "referral": "none",
                      "screening_offered": True, "version": 1, "timestamp": int(time.time())}).encode()
    random_key = secrets.token_hex(32).encode()
    for sig in (hmac.new(random_key, raw, hashlib.sha256).hexdigest(), ""):
        r = httpx.post(f"{API}/internal/safety-status", content=raw, headers={"Content-Type": "application/json", "X-Align-Signature": sig}, timeout=20)
        assert r.status_code == 503 and case_id not in r.text
    assert db["case_safety"].count_documents({}) == before


def test_admin_panel_reports_webhook_off():
    admin = _admin()
    s = httpx.get(f"{API}/admin/safety-audit-log/align-status", headers=admin, timeout=20).json()
    assert s["webhook_on"] is False and s["rejected_30d"]["webhook_off"] >= 1
    assert httpx.post(f"{API}/admin/safety-audit-log/self-test", headers=admin, timeout=20).json() == {"ok": False, "reason": "not_configured"}
    assert httpx.post(f"{API}/admin/safety-audit-log/align-ping", headers=admin, timeout=20).json() == {"configured": False}


def test_link_health_amber_while_off_and_admin_only():
    admin = _admin()
    r = httpx.get(f"{API}/admin/safety-audit-log/link-health", headers=admin, timeout=20)
    assert r.json() == {"ok": False} and "no-store" in r.headers.get("cache-control", "")
    p = httpx.post(f"{API}/auth/login", json={"email": "parent1@test.com", "password": "TestPass123!"}, timeout=20)
    if p.status_code == 200:
        h = {"Authorization": f"Bearer {p.json()['access_token']}"}
        assert httpx.get(f"{API}/admin/safety-audit-log/link-health", headers=h, timeout=20).status_code == 403

