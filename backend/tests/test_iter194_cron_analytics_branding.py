"""Iter 194 — Cron scheduler + reminder analytics + sample personalisation.

Locks:
  * Reminder scheduler loop function is import-safe and idle when
    `ALIGNMENT_REFLECTION_REMINDER_ENABLED` is not set (deploy safety).
  * Tracker endpoints (open pixel + click redirect) mark the
    corresponding fields on the reminder row and are idempotent
    (second call never overwrites first-touch attribution).
  * Admin analytics aggregation returns per-subject open/click rates.
  * Sample PDF route honours `?firm=` and `?primary_color=` query
    params, renders the firm name on the cover page, and rejects
    malformed colour strings silently.
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe_reminders():
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            await c[DB_NAME].alignment_reflection_reminders.delete_many(
                {"target_email": {"$regex": "iter194"}},
            )
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_run())
    loop.close()
    yield


# ---------------------------------------------------------------------------
# Scheduler loop — import-safe, idle when env flag is off.
# ---------------------------------------------------------------------------

def test_scheduler_loop_is_import_safe_and_idle_by_default():
    """The scheduler MUST import cleanly and MUST idle when the env
    flag is unset — otherwise every dev environment fires reminder
    emails on backend restart."""
    import importlib
    mod = importlib.import_module("alignment_reflection_reminder")
    # Env flag is not set in the test env — `_enabled()` returns False.
    os.environ.pop("ALIGNMENT_REFLECTION_REMINDER_ENABLED", None)
    assert mod._enabled() is False
    assert callable(mod.alignment_reflection_reminder_loop)


def test_scheduler_registered_in_server_startup():
    """The startup handler in server.py must register the loop task."""
    import server
    src = open(server.__file__).read()
    assert "alignment_reflection_reminder_loop" in src
    assert "asyncio.create_task(alignment_reflection_reminder_loop" in src


# ---------------------------------------------------------------------------
# Tracker endpoints.
# ---------------------------------------------------------------------------

def _seed_reminder_row() -> str:
    """Insert a placeholder reminder row and return its ObjectId as
    a hex string suitable for the tracker URLs."""
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            res = await db.alignment_reflection_reminders.insert_one({
                "target_user_id":   "user_iter194",
                "target_email":     "iter194_target@test.local",
                "coparent_user_id": "user_iter194_a",
                "subject":          "co_parenting",
                "sent_at":          datetime.now(timezone.utc),
            })
            return str(res.inserted_id)
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    rid = loop.run_until_complete(_run())
    loop.close()
    return rid


async def _fetch_reminder(rid: str):
    c = AsyncIOMotorClient(MONGO_URL)
    try:
        return await c[DB_NAME].alignment_reflection_reminders.find_one(
            {"_id": ObjectId(rid)},
        )
    finally:
        c.close()


def test_tracker_pixel_marks_opened_and_returns_gif(client):
    rid = _seed_reminder_row()
    r = client.get(f"/api/insights/track/reminder-open/{rid}.gif")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/gif"
    # 1x1 GIF starts with GIF89a magic bytes.
    assert r.content[:6] == b"GIF89a"

    loop = asyncio.get_event_loop_policy().new_event_loop()
    doc = loop.run_until_complete(_fetch_reminder(rid))
    loop.close()
    assert doc.get("opened_at") is not None


def test_tracker_pixel_is_first_touch_only(client):
    """A second open must not overwrite the first — clients like
    Gmail preview + real inbox open would otherwise double-count."""
    rid = _seed_reminder_row()
    client.get(f"/api/insights/track/reminder-open/{rid}.gif")
    loop1 = asyncio.get_event_loop_policy().new_event_loop()
    first = loop1.run_until_complete(_fetch_reminder(rid))
    loop1.close()
    first_at = first["opened_at"]

    # Sleep briefly so a second write would produce a distinguishable ts.
    import time
    time.sleep(0.05)
    client.get(f"/api/insights/track/reminder-open/{rid}.gif")
    loop2 = asyncio.get_event_loop_policy().new_event_loop()
    second = loop2.run_until_complete(_fetch_reminder(rid))
    loop2.close()
    assert second["opened_at"] == first_at


def test_tracker_click_redirects_and_marks_clicked(client):
    rid = _seed_reminder_row()
    r = client.get(
        f"/api/insights/track/reminder-click/{rid}",
        follow_redirects=False,
    )
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.endswith("/alignment/reflect/co_parenting")

    loop = asyncio.get_event_loop_policy().new_event_loop()
    doc = loop.run_until_complete(_fetch_reminder(rid))
    loop.close()
    assert doc.get("clicked_at") is not None


def test_tracker_endpoints_never_leak_row_details_on_bad_rid(client):
    """Unknown / malformed rid MUST return the 1x1 gif or redirect
    to a safe fallback — never a 4xx or a 500 that would break an
    email preview."""
    r_gif = client.get("/api/insights/track/reminder-open/notavalidobjectid.gif")
    assert r_gif.status_code == 200
    assert r_gif.headers["content-type"] == "image/gif"

    r_click = client.get(
        "/api/insights/track/reminder-click/notavalidobjectid",
        follow_redirects=False,
    )
    assert r_click.status_code == 302
    # Falls back to the subject picker so a stale email link is still useful.
    assert r_click.headers["location"].endswith("/alignment/subjects")


# ---------------------------------------------------------------------------
# Analytics aggregation.
# ---------------------------------------------------------------------------

def test_analytics_aggregation_computes_per_subject_rates():
    from alignment_reflection_analytics import compute_reminder_analytics

    async def _seed_and_compute():
        c = AsyncIOMotorClient(MONGO_URL)
        scratch = f"{DB_NAME}_t194_analytics"
        try:
            # Own scratch database, so rows from other suites can't change the counts.
            db = c[scratch]
            # 4 sent, 2 opened, 1 clicked.
            base_email = "iter194_analytics@test.local"
            docs = [
                {"target_email": base_email, "subject": "co_parenting",
                 "opened_at": datetime.now(timezone.utc),
                 "clicked_at": datetime.now(timezone.utc)},
                {"target_email": base_email, "subject": "co_parenting",
                 "opened_at": datetime.now(timezone.utc)},
                {"target_email": base_email, "subject": "co_parenting"},
                {"target_email": base_email, "subject": "communication"},
            ]
            for d in docs:
                d["sent_at"] = datetime.now(timezone.utc)
            await db.alignment_reflection_reminders.insert_many(docs)
            return await compute_reminder_analytics(db)
        finally:
            await c.drop_database(scratch)
            c.close()

    loop = asyncio.get_event_loop_policy().new_event_loop()
    result = loop.run_until_complete(_seed_and_compute())
    loop.close()
    by = {s["subject"]: s for s in result["subjects"]}
    cp = by["co_parenting"]
    assert cp["sent"] == 3
    assert cp["opened"] == 2
    assert cp["clicked"] == 1
    assert cp["open_rate"] == 66.7  # 2/3
    assert cp["click_rate"] == 33.3  # 1/3
    # Total row sums correctly across subjects.
    assert result["total"]["sent"] == 4


# ---------------------------------------------------------------------------
# Sample PDF personalisation.
# ---------------------------------------------------------------------------

def test_sample_pdf_renders_firm_branding_on_cover():
    from coparenting_alignment_sample import build_sample_pdf_bytes
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    pdf = build_sample_pdf_bytes(firm="Acme Family Mediation LLP")
    r = PdfReader(io.BytesIO(pdf))
    cover_text = r.pages[0].extract_text() or ""
    assert "PREPARED FOR" in cover_text
    assert "Acme Family Mediation LLP" in cover_text


def test_sample_pdf_ignores_invalid_primary_color():
    """A bad colour must not blow up the PDF — the branding block
    still renders with the default SA CoParents purple."""
    from coparenting_alignment_sample import build_sample_pdf_bytes
    pdf = build_sample_pdf_bytes(
        firm="Acme Family Mediation LLP", primary_color="not-a-real-hex",
    )
    assert pdf[:5] == b"%PDF-"


def test_sample_pdf_unbranded_variant_has_no_prepared_for_block():
    from coparenting_alignment_sample import build_sample_pdf_bytes
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    pdf = build_sample_pdf_bytes()  # no branding
    r = PdfReader(io.BytesIO(pdf))
    cover_text = r.pages[0].extract_text() or ""
    assert "PREPARED FOR" not in cover_text


def test_sample_pdf_route_honours_branding_query_params(client):
    r = client.get(
        "/api/insights/samples/co-parenting-alignment-report.pdf"
        "?firm=Acme+Family+Mediation+LLP&primary_color=%23AA0033"
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # Branded variant must NOT be cached — a mediator tweaking the
    # URL should see updates instantly.
    assert "no-store" in r.headers.get("cache-control", "")
    assert 'branded-sample.pdf' in r.headers.get("content-disposition", "")


def test_sample_pdf_route_unbranded_still_cached(client):
    r = client.get(
        "/api/insights/samples/co-parenting-alignment-report.pdf"
    )
    assert r.status_code == 200
    assert "max-age" in r.headers.get("cache-control", "")


# ---------------------------------------------------------------------------
# Reminder module — tracked URLs land in the email body.
# ---------------------------------------------------------------------------

def test_reminder_email_html_includes_pixel_and_click_wrapper():
    from alignment_reflection_reminder import _reflection_reminder_email_html
    html = _reflection_reminder_email_html(
        coparent_display="Alex R.",
        subject_label="General Co-Parenting",
        click_url="https://sacoparents.com/api/insights/track/reminder-click/aa",
        open_pixel_url="https://sacoparents.com/api/insights/track/reminder-open/aa.gif",
    )
    assert "track/reminder-click/aa" in html
    assert "track/reminder-open/aa.gif" in html
    # The tracking pixel must be a real <img>, not a stray URL.
    assert '<img src="https://sacoparents.com/api/insights/track/reminder-open/aa.gif"' in html
