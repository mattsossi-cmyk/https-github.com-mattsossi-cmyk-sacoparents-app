# AI notice ack requires current privacy consent (guest session), via the public URL
import os
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}


def test_guest_ack_409_until_consent():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/guest")
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    me = s.get(f"{BASE_URL}/api/auth/me").json()
    assert me["consent_current"] is False
    r = s.post(f"{BASE_URL}/api/ai-notice/ack")
    assert r.status_code == 409
    assert "Before you continue" in r.json()["detail"]
    assert s.post(f"{BASE_URL}/api/privacy-consent", json=CONSENT).status_code == 200
    r = s.post(f"{BASE_URL}/api/ai-notice/ack")
    assert r.status_code == 200 and r.json()["ok"] is True
    me = s.get(f"{BASE_URL}/api/auth/me").json()
    assert me["consent_current"] is True and me["ai_notice_current"] is True
