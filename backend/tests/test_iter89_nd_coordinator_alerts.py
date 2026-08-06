"""Iter 89 — Coordinator alerts for High / Critical ND Risk Assessment.

Covers:
  * `_should_fire` dedupe logic — first-time hit, tier escalation, same-
    tier re-hit inside 24h (suppressed), same-tier re-hit after 24h.
  * `maybe_fire_coordinator_alert` no-ops for non-alert tiers.
  * `maybe_fire_coordinator_alert` no-ops when OPERATOR_EMAIL is unset.
  * End-to-end: submitting a high-tier assessment writes an
    `nd_coordinator_alerts` row (email send is monkey-patched so the
    test doesn't need a working Resend key).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

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


from nd_coordinator_alerts import (  # noqa: E402
    _should_fire, maybe_fire_coordinator_alert, ALERT_TIERS,
)


def _now_iso(**delta):
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


# --------------------------------------------------------------------- #
# _should_fire
# --------------------------------------------------------------------- #

def test_should_fire_low_tier_never_fires():
    assert _should_fire(None, "low") is None
    assert _should_fire({"tier": "high", "sent_at": _now_iso()}, "low") is None


def test_should_fire_medium_tier_never_fires():
    assert _should_fire(None, "medium") is None


def test_should_fire_first_high_hit_fires():
    assert _should_fire(None, "high") == "hit"


def test_should_fire_first_critical_hit_fires():
    assert _should_fire(None, "critical") == "hit"


def test_should_fire_escalation_high_to_critical_fires_immediately():
    prior = {"tier": "high", "sent_at": _now_iso(minutes=5)}  # 5 min ago
    assert _should_fire(prior, "critical") == "escalated"


def test_should_fire_same_tier_within_24h_suppressed():
    prior = {"tier": "high", "sent_at": _now_iso(hours=1)}
    assert _should_fire(prior, "high") is None


def test_should_fire_same_tier_past_24h_re_fires():
    prior = {"tier": "high", "sent_at": _now_iso(hours=25)}
    assert _should_fire(prior, "high") == "re_hit"


def test_should_fire_critical_same_tier_within_24h_suppressed():
    """Even 'critical' still respects the 24h window — a parent
    re-submitting the same assessment should not spam the operator."""
    prior = {"tier": "critical", "sent_at": _now_iso(hours=2)}
    assert _should_fire(prior, "critical") is None


def test_should_fire_bad_prior_timestamp_re_fires():
    """Corrupt prior row shouldn't accidentally suppress a real alert."""
    assert _should_fire({"tier": "high"}, "high") == "re_hit"


def test_alert_tiers_are_exactly_high_and_critical():
    assert ALERT_TIERS == frozenset({"high", "critical"})


# --------------------------------------------------------------------- #
# maybe_fire_coordinator_alert
# --------------------------------------------------------------------- #

class _FakeCollection:
    def __init__(self):
        self.rows: list[dict] = []

    async def insert_one(self, doc):
        self.rows.append(doc)
        return type("R", (), {"inserted_id": "x"})()

    async def find_one(self, query, projection=None, sort=None):
        rows = [r for r in self.rows if r.get("user_id") == query.get("user_id")]
        if sort:
            for key, direction in sort:
                rows.sort(key=lambda r: r.get(key) or "", reverse=(direction < 0))
        return rows[0] if rows else None


class _FakeDB:
    def __init__(self):
        self.nd_coordinator_alerts = _FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_maybe_fire_low_tier_is_noop():
    db = _FakeDB()
    result = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a1",
        tier="low",
        tier_label="Low",
        total_score=2,
        target_name="Sam",
        coparent_name="Jamie",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result == {"fired": False, "reason": "not_alerting_tier"}
    assert db.nd_coordinator_alerts.rows == []


def test_maybe_fire_no_operator_email_env_is_noop(monkeypatch):
    monkeypatch.setenv("OPERATOR_EMAIL", "")
    db = _FakeDB()
    result = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a1",
        tier="high",
        tier_label="High",
        total_score=10,
        target_name="Sam",
        coparent_name="Jamie",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result == {"fired": False, "reason": "no_operator_email"}
    assert db.nd_coordinator_alerts.rows == []


def test_maybe_fire_records_row_even_when_email_fails(monkeypatch):
    """A broken email provider must NOT leave the dedupe collection empty —
    otherwise every submission re-tries a broken send."""
    monkeypatch.setenv("OPERATOR_EMAIL", "ops@example.test")

    def _boom(**kwargs):
        raise RuntimeError("resend is down")

    import email_service
    monkeypatch.setattr(email_service, "send_coordinator_nd_alert", _boom)

    db = _FakeDB()
    result = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a1",
        tier="critical",
        tier_label="Critical",
        total_score=15,
        target_name="Sam",
        coparent_name="Jamie",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result["fired"] is False
    assert result["email_ok"] is False
    assert result["reason"] == "hit"
    # Row IS recorded so the next submit within 24h is deduped rather
    # than re-attempting a broken send.
    assert len(db.nd_coordinator_alerts.rows) == 1
    row = db.nd_coordinator_alerts.rows[0]
    assert row["email_ok"] is False
    assert row["email_error"] == "resend is down"
    assert row["tier"] == "critical"


def test_maybe_fire_happy_path_records_row(monkeypatch):
    monkeypatch.setenv("OPERATOR_EMAIL", "ops@example.test")
    sent = []

    def _capture(**kwargs):
        sent.append(kwargs)

    import email_service
    monkeypatch.setattr(email_service, "send_coordinator_nd_alert", _capture)

    db = _FakeDB()
    result = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a1",
        tier="high",
        tier_label="High",
        total_score=10,
        target_name="Sam Parent",
        coparent_name="Jamie CoParent",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result == {"fired": True, "reason": "hit", "email_ok": True}
    assert len(sent) == 1
    assert sent[0]["to_email"] == "ops@example.test"
    assert sent[0]["tier"] == "high"
    assert sent[0]["reason"] == "hit"
    assert sent[0]["target_name"] == "Sam Parent"
    assert sent[0]["coparent_name"] == "Jamie CoParent"
    # Second attempt inside 24h → deduped (no new send).
    result2 = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a2",
        tier="high",
        tier_label="High",
        total_score=11,
        target_name="Sam Parent",
        coparent_name="Jamie CoParent",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result2 == {"fired": False, "reason": "deduped"}
    assert len(sent) == 1  # NOT 2 — deduped


def test_maybe_fire_escalation_bypasses_dedupe(monkeypatch):
    monkeypatch.setenv("OPERATOR_EMAIL", "ops@example.test")
    sent = []

    def _capture(**kwargs):
        sent.append(kwargs)

    import email_service
    monkeypatch.setattr(email_service, "send_coordinator_nd_alert", _capture)

    db = _FakeDB()
    _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a1",
        tier="high",
        tier_label="High",
        total_score=10,
        target_name="Sam",
        coparent_name="Jamie",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    # Escalation two minutes later → immediate re-fire.
    result = _run(maybe_fire_coordinator_alert(
        db,  # type: ignore[arg-type]
        user_id="u1",
        assessment_id="a2",
        tier="critical",
        tier_label="Critical",
        total_score=14,
        target_name="Sam",
        coparent_name="Jamie",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    ))
    assert result["fired"] is True
    assert result["reason"] == "escalated"
    assert len(sent) == 2
    assert sent[-1]["reason"] == "escalated"
