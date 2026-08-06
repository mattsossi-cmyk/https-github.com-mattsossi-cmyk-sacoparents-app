"""Iter 90 — Weekly Compliance Reminder (Monday nudge email).

Covers:
  * Send window gate — only Monday 08:00-22:00 UTC unless `force_window`
  * Preferences round-trip (default opt-in, opt-out sticks)
  * Suppression rules — no email, opted out, inactive, already sent,
    high-enough %, no checklist
  * Happy path — records the send row + fires the email
  * Email-provider failure still records the audit row (so a broken
    Resend doesn't cause a re-attempt storm)
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
except FileNotFoundError:
    pass


import weekly_compliance_reminder as wcr  # noqa: E402


# ---------------------------------------------------------------------------
# Fake DB with just enough surface for the reminder module.
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = rows

    def __aiter__(self):
        self._it = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration as e:
            raise StopAsyncIteration from e


class _FakeCollection:
    def __init__(self):
        self.rows: List[Dict[str, Any]] = []

    async def insert_one(self, doc):
        self.rows.append(doc)
        return type("R", (), {"inserted_id": "x"})()

    async def find_one(self, query, projection=None, sort=None):
        for r in list(reversed(self.rows)) if sort else self.rows:
            if all(r.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                return r
        return None

    def find(self, query=None, projection=None):
        matching = [r for r in self.rows if _match(r, query or {})]
        return _FakeCursor(matching)

    async def update_one(self, query, update, upsert=False):
        for r in self.rows:
            if all(r.get(k) == v for k, v in query.items()):
                r.update(update.get("$set", {}))
                return
        if upsert:
            new_row = {**query, **update.get("$set", {})}
            self.rows.append(new_row)

    async def distinct(self, field, query=None):
        matching = [r for r in self.rows if _match(r, query or {})]
        return list({r[field] for r in matching if field in r})


def _match(row, query):
    for k, v in query.items():
        if isinstance(v, dict):
            for op, val in v.items():
                if op == "$gte" and (row.get(k) is None or row.get(k) < val):
                    return False
                if op == "$lte" and (row.get(k) is None or row.get(k) > val):
                    return False
        elif row.get(k) != v:
            return False
    return True


class _FakeDB:
    def __init__(self):
        self.intervention_reminder_prefs = _FakeCollection()
        self.weekly_compliance_reminder_sends = _FakeCollection()
        self.intervention_compliance = _FakeCollection()
        self.users = _FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Send window
# ---------------------------------------------------------------------------

def _monday_at(hour: int) -> datetime:
    # Feb 23 2026 is a Monday.
    return datetime(2026, 2, 23, hour, 0, 0, tzinfo=timezone.utc)


def _tuesday_at(hour: int) -> datetime:
    return datetime(2026, 2, 24, hour, 0, 0, tzinfo=timezone.utc)


def test_in_send_window_monday_10am_utc_is_open():
    assert wcr._in_send_window(_monday_at(10)) is True


def test_in_send_window_monday_7am_utc_is_closed():
    """Send window starts at 08:00 UTC by default."""
    assert wcr._in_send_window(_monday_at(7)) is False


def test_in_send_window_monday_23_utc_is_closed():
    """Send window ends at 22:00 UTC by default."""
    assert wcr._in_send_window(_monday_at(23)) is False


def test_in_send_window_tuesday_10am_is_closed():
    assert wcr._in_send_window(_tuesday_at(10)) is False


def test_sweep_outside_window_short_circuits():
    db = _FakeDB()
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=True, now=_tuesday_at(10),  # type: ignore[arg-type]
    ))
    assert result["skipped"] == "outside_send_window"
    assert result["results"] == []


# ---------------------------------------------------------------------------
# Preferences default
# ---------------------------------------------------------------------------

def test_get_reminder_pref_defaults_to_opted_in():
    db = _FakeDB()
    p = _run(wcr.get_reminder_pref(db, "u1"))  # type: ignore[arg-type]
    assert p == {"opted_in": True, "updated_at": None}


def test_set_reminder_pref_persists_opt_out():
    db = _FakeDB()
    _run(wcr.set_reminder_pref(db, "u1", False))  # type: ignore[arg-type]
    p = _run(wcr.get_reminder_pref(db, "u1"))  # type: ignore[arg-type]
    assert p["opted_in"] is False
    assert p["updated_at"] is not None


# ---------------------------------------------------------------------------
# Full sweep — suppression matrix
# ---------------------------------------------------------------------------

def _seed_active_user(
    db: _FakeDB, uid: str, email: str = "sam@example.test",
) -> None:
    """Give this user a users row + a compliance-log row inside the
    inactivity window."""
    now = datetime.now(timezone.utc).isoformat()
    db.users.rows.append({"user_id": uid, "email": email, "name": "Sam"})
    db.intervention_compliance.rows.append({
        "user_id": uid, "week_start": wcr._week_start(),
        "intervention_key": "k1", "followed": False,
        "updated_at": now,
    })


def _stub_helpers(monkeypatch, *, pending_items, streak=0, total=None):
    """Force _current_week_summary + _current_streak so the tests don't need
    real assessment data."""
    total = total if total is not None else (
        len(pending_items) or 1
    )
    async def fake_summary(db, user_id):
        return {
            "week_start":     wcr._week_start(),
            "total":          total,
            "followed":       total - len(pending_items),
            "compliance_pct": round(
                ((total - len(pending_items)) / total) * 100, 1
            ) if total else 0.0,
            "pending_items":  pending_items,
        }
    async def fake_streak(db, user_id):
        return streak
    monkeypatch.setattr(wcr, "_current_week_summary", fake_summary)
    monkeypatch.setattr(wcr, "_current_streak", fake_streak)


def test_sweep_dispatches_active_user_happy_path(monkeypatch):
    monkeypatch.setenv("OPERATOR_EMAIL", "ops@example.test")
    sent = []
    import email_service
    monkeypatch.setattr(
        email_service, "send_weekly_compliance_reminder",
        lambda **kw: sent.append(kw),
    )
    _stub_helpers(
        monkeypatch,
        pending_items=[{"text": "Send weekly summary", "source": "safety", "group": "A"}],
        streak=3,
        total=3,
    )
    db = _FakeDB()
    _seed_active_user(db, "u1")
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10),  # type: ignore[arg-type]
        force_window=True,
    ))
    r = result["results"][0]
    assert r["sent"] is True
    assert r["reason"] == "delivered"
    assert r["pending_count"] == 1
    assert r["current_streak"] == 3
    assert len(sent) == 1
    assert sent[0]["to_email"] == "sam@example.test"
    assert sent[0]["current_streak"] == 3
    # Audit row written.
    assert len(db.weekly_compliance_reminder_sends.rows) == 1
    audit = db.weekly_compliance_reminder_sends.rows[0]
    assert audit["email_ok"] is True


def test_sweep_dry_run_never_sends(monkeypatch):
    sent = []
    import email_service
    monkeypatch.setattr(
        email_service, "send_weekly_compliance_reminder",
        lambda **kw: sent.append(kw),
    )
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=1, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1")
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=True, now=_monday_at(10),  # type: ignore[arg-type]
        force_window=True,
    ))
    r = result["results"][0]
    assert r["sent"] is False
    assert r["reason"] == "dry_run"
    assert sent == []
    assert db.weekly_compliance_reminder_sends.rows == []


def test_sweep_suppresses_opted_out_user(monkeypatch):
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=0, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1")
    _run(wcr.set_reminder_pref(db, "u1", False))  # type: ignore[arg-type]
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10),  # type: ignore[arg-type]
        force_window=True,
    ))
    assert result["results"][0]["reason"] == "opted_out"


def test_sweep_suppresses_inactive_user(monkeypatch):
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=0, total=3)
    db = _FakeDB()
    long_ago = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    db.users.rows.append({"user_id": "u1", "email": "sam@example.test", "name": "Sam"})
    db.intervention_compliance.rows.append({
        "user_id": "u1", "week_start": "2025-08-01",
        "intervention_key": "k1", "followed": False,
        "updated_at": long_ago,
    })
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10),  # type: ignore[arg-type]
        force_window=True,
    ))
    # No candidate → no results (distinct query filters by updated_at cutoff)
    assert result["results"] == []


def test_sweep_suppresses_high_enough_pct(monkeypatch):
    _stub_helpers(monkeypatch, pending_items=[], streak=3, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1")
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10),  # type: ignore[arg-type]
        force_window=True,
    ))
    assert result["results"][0]["reason"] == "already_high_enough"


def test_sweep_suppresses_second_send_same_week(monkeypatch):
    monkeypatch.setenv("OPERATOR_EMAIL", "ops@example.test")
    import email_service
    monkeypatch.setattr(
        email_service, "send_weekly_compliance_reminder", lambda **kw: None,
    )
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=1, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1")
    # First sweep: sends.
    r1 = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10), force_window=True,  # type: ignore[arg-type]
    ))
    assert r1["results"][0]["reason"] == "delivered"
    # Second sweep same week: deduped.
    r2 = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(11), force_window=True,  # type: ignore[arg-type]
    ))
    assert r2["results"][0]["reason"] == "already_sent_this_week"
    assert len(db.weekly_compliance_reminder_sends.rows) == 1


def test_sweep_suppresses_demo_email(monkeypatch):
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=0, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1", email="guest@demo.local")
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10), force_window=True,  # type: ignore[arg-type]
    ))
    assert result["results"][0]["reason"] == "no_or_demo_email"


def test_sweep_records_audit_row_when_email_fails(monkeypatch):
    """A broken Resend must NOT leave the dedupe empty — otherwise the
    next sweep re-attempts and hits the same failure."""
    import email_service

    def _boom(**kw):
        raise RuntimeError("resend is down")

    monkeypatch.setattr(email_service, "send_weekly_compliance_reminder", _boom)
    _stub_helpers(monkeypatch, pending_items=[{"text": "x", "source": "safety", "group": "A"}], streak=1, total=3)
    db = _FakeDB()
    _seed_active_user(db, "u1")
    result = _run(wcr.send_weekly_compliance_reminders(
        db, dry_run=False, now=_monday_at(10), force_window=True,  # type: ignore[arg-type]
    ))
    assert result["results"][0]["sent"] is False
    assert result["results"][0]["reason"] == "email_error"
    audit = db.weekly_compliance_reminder_sends.rows[0]
    assert audit["email_ok"] is False
    assert "resend is down" in (audit["email_error"] or "")
