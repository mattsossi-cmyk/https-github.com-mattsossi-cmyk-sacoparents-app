"""Owner 2026-10-21: neutral reminder email, Quick Exit server-side sign-out, /check-in path, safe-contact marker (pro only)."""
import os
import sys

import requests
from dotenv import dotenv_values

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from casekit import completed_case  # noqa: E402

API = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
BANNED = ("safety", "violence", "abuse", "screening", "flagged", "hotline", "911")


def test_reminder_email_is_neutral():
    from safety_screening import CHECKIN_REMINDER_HTML
    html = CHECKIN_REMINDER_HTML.format(name="Pat", link="https://sacoparentsalign.com/check-in?case=SA-1", from_name="SA CoParents").lower()
    assert "a short, private check-in is still waiting for you" in html
    assert "/check-in?case=" in html and "sign in to continue" in html
    assert not any(w in html for w in BANNED)


def test_me_check_in_returns_neutral_path_and_quick_exit_kills_session():
    pro, pa, pb, d, _ = completed_case(API)
    rid = d["id"]
    r = pa.get(f"{API}/me/check-in")
    assert r.status_code == 200 and r.json()["path"] == f"/joint/{rid}/check-in"

    # copy the cookie jar (simulates a stolen cookie), then Quick Exit from the original session
    stolen = requests.Session()
    stolen.cookies.update(pa.cookies)
    assert stolen.get(f"{API}/auth/me").status_code == 200
    assert pa.post(f"{API}/auth/logout", params={"everywhere": "true"}).status_code == 200
    assert stolen.get(f"{API}/auth/me").status_code == 401
    assert stolen.post(f"{API}/auth/refresh").status_code == 401

    # plain logout (no everywhere) does not invalidate other devices
    other = requests.Session(); other.cookies.update(pb.cookies)
    assert pb.post(f"{API}/auth/logout").status_code == 200
    assert other.get(f"{API}/auth/me").status_code == 200


def test_safe_contact_marker_pro_only():
    import fv_screening as fv
    pro, pa, pb, d, _ = completed_case(API)
    rid = d["id"]
    answers = {i["id"]: "No" for i in fv.ITEMS}
    r = pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": answers, "safe_contact": {"method": "Text only", "safe_times": "weekday mornings"}})
    assert r.status_code == 200, r.text
    roles = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]
    assert roles["a"]["has_safe_contact"] is True and roles["b"]["has_safe_contact"] is False
    for s in (pa, pb):
        txt = s.get(f"{API}/joint/reports/{rid}/safety-screening").text
        assert "has_safe_contact" not in txt and "safe_times" not in txt.replace("safe_contact_prompt", "")
    assert "weekday mornings" not in pb.get(f"{API}/joint/reports/{rid}").text
    assert "weekday mornings" not in pa.get(f"{API}/joint/reports/{rid}/report").text
