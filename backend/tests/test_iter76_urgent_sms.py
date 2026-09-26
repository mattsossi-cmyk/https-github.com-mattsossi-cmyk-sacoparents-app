"""Iteration 76: judge mobile number for urgent-safety SMS (fail-soft when Twilio unconfigured)."""
import os

from sms import normalize_mobile
from test_judicial_portal import _flow
from test_legal_report import API


def test_normalize_mobile() -> None:
    assert normalize_mobile("(210) 555-0123") == "+12105550123"
    assert normalize_mobile("+44 20 7946 0958") == "+442079460958"
    assert normalize_mobile("12345") is None


def test_judge_alert_settings_roundtrip() -> None:
    judge, pro, ref, case = _flow()
    s = judge.get(f"{API}/court-dashboard/alert-settings").json()
    assert s["mobile"] == "" and "configured" in s
    assert judge.put(f"{API}/court-dashboard/alert-settings", json={"mobile": "12345"}).status_code == 400
    s = judge.put(f"{API}/court-dashboard/alert-settings", json={"mobile": "210-555-0123", "sms_urgent_alerts": True}).json()
    assert s["mobile"] == "+12105550123" and s["sms_urgent_alerts"] is True
    t = judge.post(f"{API}/court-dashboard/alert-settings/test-sms")
    assert t.status_code == (200 if os.environ.get("TWILIO_ACCOUNT_SID") else 503)
    assert pro.get(f"{API}/court-dashboard/alert-settings").status_code == 403
    s = judge.put(f"{API}/court-dashboard/alert-settings", json={"mobile": "", "sms_urgent_alerts": False}).json()
    assert s["mobile"] == ""
