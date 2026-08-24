"""iter121 · Texas HB 300 (Medical Records Privacy Act) compliance endpoints.

Covers:
  * signup auto-writes hb300_ack_version + marketing_opt_in=False
  * GET  /api/me/hb300/status
  * POST /api/me/hb300/acknowledge
  * POST /api/me/hb300/marketing
  * POST /api/me/hb300/access-request  (15-business-day SLA)
  * POST /api/admin/breach-report      (403 for non-admin)
"""
import uuid
from datetime import datetime, timedelta, timezone


def _business_days_between(a: datetime, b: datetime) -> int:
    if b < a:
        a, b = b, a
    days = 0
    cur = a
    while cur.date() < b.date():
        cur = cur + timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def test_signup_captures_hb300_ack(base_url, auth_client, test_user):
    r = auth_client.get(f"{base_url}/api/me/hb300/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["hb300_ack_version"] == "2026-02-21"
    assert body["hb300_ack_at"]
    assert body["marketing_opt_in"] is False
    assert body["pending_access_requests"] == 0


def test_hb300_acknowledge_is_idempotent(base_url, auth_client):
    r1 = auth_client.post(
        f"{base_url}/api/me/hb300/acknowledge",
        json={"notice_version": "2026-02-21"},
    )
    assert r1.status_code == 200
    r2 = auth_client.post(
        f"{base_url}/api/me/hb300/acknowledge",
        json={"notice_version": "2026-02-21"},
    )
    assert r2.status_code == 200
    # Timestamps should update (idempotent write)
    assert r1.json()["notice_version"] == r2.json()["notice_version"]


def test_marketing_opt_in_and_out(base_url, auth_client):
    on = auth_client.post(
        f"{base_url}/api/me/hb300/marketing",
        json={"opt_in": True},
    )
    assert on.status_code == 200
    assert on.json()["opt_in"] is True

    status = auth_client.get(f"{base_url}/api/me/hb300/status").json()
    assert status["marketing_opt_in"] is True

    off = auth_client.post(
        f"{base_url}/api/me/hb300/marketing",
        json={"opt_in": False},
    )
    assert off.status_code == 200
    assert off.json()["opt_in"] is False


def test_access_request_returns_15_business_day_sla(base_url, auth_client):
    r = auth_client.post(
        f"{base_url}/api/me/hb300/access-request",
        json={"reason": "Mediation prep"},
    )
    assert r.status_code == 200
    body = r.json()
    requested = datetime.fromisoformat(body["requested_at"].replace("Z", "+00:00"))
    due = datetime.fromisoformat(body["sla_due_at"].replace("Z", "+00:00"))
    biz_days = _business_days_between(requested, due)
    assert biz_days == 15, f"HB 300 §181.102 requires 15 biz days, got {biz_days}"
    assert body["self_serve_url"] == "/api/me/export"


def test_breach_report_forbidden_for_non_admin(base_url, auth_client):
    r = auth_client.post(
        f"{base_url}/api/admin/breach-report",
        json={
            "summary":                  "x" * 30,
            "discovered_at":            datetime.now(timezone.utc).isoformat(),
            "texas_residents_affected": 5,
            "phi_categories":           "safety_lens",
            "remediation":              "Rotated credentials.",
        },
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin only."
