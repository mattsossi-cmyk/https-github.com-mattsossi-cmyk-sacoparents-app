"""AI endpoints need a signed-in parent who accepted the AI notice. Each module also gets its own client address,
so the shared per-address AI quota used by one test file doesn't spill into the next."""
import os
import sys
import uuid
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_notice import AI_NOTICE_VERSION  # noqa: E402


def ai_headers(api: str, email: str = "parent1@test.com", password: str = "TestPass123!") -> dict:
    r = requests.post(f"{api}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    accept_ai_notice(api, h)
    return {**h, **client_address()}


def accept_ai_notice(api: str, h: dict) -> None:
    """Current Privacy Notice consent first (the AI notice needs it), then the AI notice."""
    c = requests.post(f"{api}/privacy-consent", headers=h, json={"ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=30)
    assert c.status_code == 200, c.text[:200]
    ack = requests.post(f"{api}/ai-notice/ack", headers=h, timeout=30,
                        json={"ai_notice_version": AI_NOTICE_VERSION, "ai_notice_ack_at": datetime.now(timezone.utc).isoformat()})
    assert ack.status_code == 200, ack.text[:200]


def client_address() -> dict:
    n = uuid.uuid4().int
    return {"X-Forwarded-For": f"10.{n % 250}.{(n >> 8) % 250}.{(n >> 16) % 250}"}
