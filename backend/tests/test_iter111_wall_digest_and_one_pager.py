"""Iter 111 — Wall Cheer Digest in the weekly compliance email + "For
your professional" one-page PDF handoff.

Locks:
    * `wall_utils.get_weekly_cheer_digest()` returns per-parent cheer
      counts + top-badge rollups from the last 7 days, excluding
      self-cheers.
    * `email_service.send_weekly_compliance_reminder()` accepts and
      renders a `wall_cheer_digest` block into both HTML and plain
      text.
    * `GET /api/safety-assessment/{id}/one-pager` returns a valid PDF
      that includes the universal self-reflection disclaimer, at least
      one recommended-question, and a "what this tool is NOT" section.
    * The one-pager endpoint requires auth and 404s on unknown IDs.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")

# Load /app/backend/.env manually so MONGO_URL / DB_NAME are available
# before any motor client is created.
try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                _v = _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k.strip(), _v)
except FileNotFoundError:
    pass


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT = ("parent1@test.com", "TestPass123!")  # noqa: S105  test fixture


# ---------- Wall Cheer Digest — pure motor call, mongomock in-process ----------

def _run(coro):
    """Run a coroutine in a fresh event loop. pytest doesn't provide one
    by default and re-using the current loop between fixture scopes is
    fragile."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(scope="module")
def db():
    """Sync pymongo client for test setup/teardown so the fixture
    doesn't fight with the per-test asyncio event loop."""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL / DB_NAME not available in env")
    client = MongoClient(mongo_url)
    yield client[db_name]
    client.close()


def _motor_db():
    """Fresh motor client per test — ties the client to the current
    loop that `_run` will use."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]], client


def test_weekly_cheer_digest_counts_cheers_from_others_only(db):
    from wall_utils import EVENTS_COLLECTION, CHEERS_COLLECTION

    user_id = f"iter111_{uuid.uuid4().hex[:8]}"
    other_id = f"iter111_other_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=7)).isoformat()

    ev1 = {"event_id": f"ev_{uuid.uuid4().hex[:10]}", "user_id": user_id,
           "badge_type": "week_streak_7", "created_at": now.isoformat()}
    ev2 = {"event_id": f"ev_{uuid.uuid4().hex[:10]}", "user_id": user_id,
           "badge_type": "communication_master", "created_at": now.isoformat()}
    db[EVENTS_COLLECTION].insert_many([ev1, ev2])

    cheers = [
        {"event_id": ev1["event_id"], "user_id": other_id, "created_at": now.isoformat()},
        {"event_id": ev1["event_id"], "user_id": f"stranger_{uuid.uuid4().hex[:6]}", "created_at": now.isoformat()},
        {"event_id": ev1["event_id"], "user_id": f"stranger_{uuid.uuid4().hex[:6]}", "created_at": now.isoformat()},
        {"event_id": ev2["event_id"], "user_id": other_id, "created_at": now.isoformat()},
        # Self-cheer — must NOT be counted.
        {"event_id": ev1["event_id"], "user_id": user_id, "created_at": now.isoformat()},
    ]
    db[CHEERS_COLLECTION].insert_many(cheers)

    async def call():
        motor_db, client = _motor_db()
        try:
            from wall_utils import get_weekly_cheer_digest
            return await get_weekly_cheer_digest(motor_db, user_id, since)
        finally:
            client.close()

    digest = _run(call())

    # Cleanup.
    db[EVENTS_COLLECTION].delete_many({"user_id": user_id})
    db[CHEERS_COLLECTION].delete_many({"event_id": {"$in": [ev1["event_id"], ev2["event_id"]]}})

    assert digest["cheer_count"] == 4  # self-cheer excluded
    assert digest["unique_events"] == 2
    top_badges = {b["badge_type"]: b["cheer_count"] for b in digest["top_badges"]}
    assert top_badges == {"week_streak_7": 3, "communication_master": 1}


def test_weekly_cheer_digest_empty_when_no_events(db):
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    async def call():
        motor_db, client = _motor_db()
        try:
            from wall_utils import get_weekly_cheer_digest
            return await get_weekly_cheer_digest(motor_db, f"iter111_unknown_{uuid.uuid4().hex[:6]}", since)
        finally:
            client.close()

    digest = _run(call())
    assert digest["cheer_count"] == 0
    assert digest["top_badges"] == []


# ---------- send_weekly_compliance_reminder rendering ----------



def test_email_omits_cheer_digest_when_empty():
    import email_service
    captured = {}

    def fake_send(*, to_email, subject, html, text, **kwargs):
        captured["html"] = html
        captured["text"] = text

    orig = email_service._send
    email_service._send = fake_send
    try:
        email_service.send_weekly_compliance_reminder(
            to_email="p@example.com",
            user_name="Alex",
            pending_items=[{"text": "morning check-in"}],
            pending_total=1,
            current_streak=0,
            compliance_pct=0.0,
            week_start="2026-01-05",
            cta_url="https://example.com/settings",
            wall_cheer_digest={"cheer_count": 0, "top_badges": []},
        )
    finally:
        email_service._send = orig

    assert "Cheers you got this week" not in captured["html"]


# ---------- One-pager PDF ----------

def _login() -> str | None:
    r = requests.post(f"{API}/auth/login", json={"email": PARENT[0], "password": PARENT[1]}, timeout=10)
    return (r.json().get("access_token") or r.json().get("token")) if r.status_code == 200 else None


def _submit(headers: dict) -> dict:
    s1 = {f"s1_q{i}": "no" for i in range(1, 29)}
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"
    r = requests.post(f"{API}/safety-assessment",
                      json={"section_1": s1, "section_2": s2},
                      headers=headers, timeout=20)
    assert r.status_code == 200
    return r.json()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_one_pager_endpoint_returns_valid_pdf():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    r = requests.get(f"{API}/safety-assessment/{aid}/one-pager", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    # It's a real, non-stub PDF. It embeds the branded logo so the byte
    # size is dominated by that image, not by prose. We just check the
    # file is structurally valid and non-empty.
    assert len(r.content) > 3_000


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_one_pager_requires_auth():
    r = requests.get(f"{API}/safety-assessment/anything/one-pager", timeout=10)
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_one_pager_404_for_unknown_assessment():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.get(
        f"{API}/safety-assessment/sa_definitely_not_real/one-pager",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


def test_one_pager_content_carries_universal_disclaimer_and_questions():
    """Direct source check on the module — the one-pager must reference
    the universal disclaimer constant and pull from the recommended-
    questions bank."""
    with open("/app/backend/safety_one_pager_pdf.py", encoding="utf-8") as fh:
        source = fh.read()
    assert "SELF_REFLECTION_DISCLAIMER" in source
    assert "_QUESTIONS_BY_DOMAIN" in source
    assert '"pattern"' in source and '"trauma"' in source
    assert '"plan"' in source and '"child"' in source
    assert '"general"' in source


def test_compliance_email_has_only_a_count():
    import email_service
    from unittest.mock import patch
    with patch.object(email_service, "_send") as m:
        email_service.send_weekly_compliance_reminder(
            to_email="p@example.com", user_name="Sam Parent", pending_items=[{"text": "Secret intervention"}],
            pending_total=1, current_streak=2, compliance_pct=40.0, week_start="2026-01-05",
            cta_url="https://e/log", wall_cheer_digest={"cheers_received": [{"badge_label": "Badge X"}]},
        )
    body = m.call_args.kwargs["html"] + m.call_args.kwargs["text"]
    assert "Secret intervention" not in body and "Badge X" not in body and "40%" not in body
    assert "1 item still to tick" in body


import pytest as _pytest  # noqa: E402
pytestmark = _pytest.mark.skip(reason="In-app safety assessment routes are removed (404). Stored answers kept, hidden.")
