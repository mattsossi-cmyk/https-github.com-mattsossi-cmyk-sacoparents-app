"""iter129 - Silent-Reviewer Nudge sweep.

Covers:
  1. A share_tokens row that was created 4 days ago, has an
     "Emailed to ..." label, and no external-read audit rows is
     picked up and nudged. `nudged_at` is stamped so it's skipped on
     future sweeps.
  2. A row that has already been opened is marked `already_opened`
     and never sends an email (also stamped as nudged so we don't
     re-check the audit log every sweep).
  3. A revoked or expired row is never nudged.
  4. A row minted via the "Get shareable link" dialog (no
     "Emailed to " label prefix) is never nudged.
  5. `dry_run=True` reports what would fire without sending or
     stamping.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class _FakeShareColl:
    def __init__(self):
        self.rows: list[dict] = []

    def find(self, filt, proj=None):  # noqa: ARG002
        def _matches(row):
            for key, spec in filt.items():
                val = row.get(key)
                if isinstance(spec, dict):
                    if "$in" in spec and val not in spec["$in"]:
                        return False
                    if "$lte" in spec and (val is None or val > spec["$lte"]):
                        return False
                    if "$regex" in spec:
                        import re
                        if not isinstance(val, str) or not re.search(spec["$regex"], val):
                            return False
                else:
                    if val != spec:
                        return False
            return True

        matched = [dict(r) for r in self.rows if _matches(r)]

        class _Cursor:
            def __init__(self, rows):
                self._rows = rows

            def __aiter__(self):
                self._it = iter(self._rows)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        return _Cursor(matched)

    async def update_one(self, filt, update):
        for r in self.rows:
            if all(r.get(k) == v for k, v in filt.items()):
                r.update(update.get("$set") or {})
                return None
        return None


class _FakeUsers:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, filt, proj=None):  # noqa: ARG002
        for r in self.rows:
            if all(r.get(k) == v for k, v in filt.items()):
                return dict(r)
        return None


class _FakeEmailsColl:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, filt, proj=None, sort=None):  # noqa: ARG002
        matched = [r for r in self.rows
                   if all(r.get(k) == v for k, v in filt.items())]
        if sort:
            key, direction = sort[0]
            matched.sort(key=lambda r: r.get(key) or "",
                         reverse=direction < 0)
        return dict(matched[0]) if matched else None


class _FakePhi:
    def __init__(self):
        self.rows: list[dict] = []

    async def find_one(self, filt, proj=None):  # noqa: ARG002
        for r in self.rows:
            if all(r.get(k) == v for k, v in filt.items()):
                return dict(r)
        return None

    async def insert_one(self, doc):
        self.rows.append(dict(doc))


@pytest.fixture
def fake_db():
    class _FakeDB:
        def __init__(self):
            self.share_tokens = _FakeShareColl()
            self.phi_access_log = _FakePhi()
            self.joint_report_emails = _FakeEmailsColl([])
            self.joint_agreement_emails = _FakeEmailsColl([])
            self.users = _FakeUsers([])

        def __getitem__(self, name):
            return getattr(self, name)
    return _FakeDB()


def _now():
    return datetime.now(timezone.utc)


def _seed_token(fake_db, *, jti, created_days_ago, doc_type="joint_report",
                revoked=False, expired=False, label="Emailed to sam@x.com",
                nudged=False):
    now = _now()
    created = now - timedelta(days=created_days_ago)
    expires = now - timedelta(days=1) if expired else now + timedelta(days=7)
    fake_db.share_tokens.rows.append({
        "jti": jti,
        "user_id": "uA",
        "doc_type": doc_type,
        "doc_id": "sh_1",
        "label": label,
        "note": None,
        "token": f"tok_{jti}",
        "created_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked_at": now.isoformat() if revoked else None,
        "nudged_at": now.isoformat() if nudged else None,
    })


@pytest.mark.asyncio
async def test_ripe_unopened_share_is_nudged(fake_db, monkeypatch):
    """A share emailed 4 days ago that no one has opened should
    trigger a nudge to the parent, and the row should be stamped."""
    import email_service
    import silent_reviewer_nudge

    _seed_token(fake_db, jti="jti_1", created_days_ago=4)
    fake_db.users.rows.append({
        "user_id": "uA", "email": "alex@example.com", "name": "Alex Parent",
    })
    fake_db.joint_report_emails = _FakeEmailsColl([{
        "user_id": "uA", "share_id": "sh_1", "preview_jti": "jti_1",
        "to_email": "sam@x.com", "recipient_name": "Sam Neutral",
        "recipient_role": "mediator", "audience": "Mediator",
        "sent_at": (_now() - timedelta(days=4)).isoformat(),
    }])

    sent = []
    monkeypatch.setattr(
        email_service, "send_silent_reviewer_nudge",
        lambda **kw: sent.append(kw),
    )

    results = await silent_reviewer_nudge.send_silent_reviewer_nudges(fake_db)

    assert len(sent) == 1, f"expected 1 nudge, got {len(sent)}: {sent}"
    kw = sent[0]
    assert kw["to_email"] == "alex@example.com"
    assert "Sam Neutral" in kw["recipient_display"]
    assert kw["artefact_label"].startswith("Joint Co-Parenting Summary")
    assert kw["days_since_sent"] >= 3
    # Row got nudged_at stamped.
    row = fake_db.share_tokens.rows[0]
    assert row["nudged_at"] is not None
    # Audit log rec captured.
    assert any(r["action"] == "silent_reviewer_nudge"
               for r in fake_db.phi_access_log.rows)
    assert any(r["status"] == "nudged" for r in results)


@pytest.mark.asyncio
async def test_already_opened_share_is_marked_not_nudged(fake_db, monkeypatch):
    import email_service
    import silent_reviewer_nudge

    _seed_token(fake_db, jti="jti_2", created_days_ago=5)
    fake_db.users.rows.append({
        "user_id": "uA", "email": "alex@example.com", "name": "Alex",
    })
    # Audit log carries a read event → share was opened.
    fake_db.phi_access_log.rows.append({
        "jti": "jti_2", "action": "external_read_via_share_link",
    })

    sent = []
    monkeypatch.setattr(email_service, "send_silent_reviewer_nudge",
                        lambda **kw: sent.append(kw))

    results = await silent_reviewer_nudge.send_silent_reviewer_nudges(fake_db)

    assert sent == [], "should not nudge an opened share"
    # nudged_at is stamped as a "we saw it, don't check again" flag.
    row = next(r for r in fake_db.share_tokens.rows if r["jti"] == "jti_2")
    assert row["nudged_at"] is not None
    assert any(r["status"] == "already_opened" for r in results)


@pytest.mark.asyncio
async def test_revoked_expired_and_manual_links_are_skipped(fake_db, monkeypatch):
    """Revoked, expired, or manually-minted (non-emailed) links are
    all excluded from the sweep."""
    import email_service
    import silent_reviewer_nudge

    _seed_token(fake_db, jti="jti_revoked", created_days_ago=5, revoked=True)
    _seed_token(fake_db, jti="jti_expired", created_days_ago=5, expired=True)
    _seed_token(fake_db, jti="jti_manual",  created_days_ago=5,
                label="For Sam attorney")  # no "Emailed to " prefix
    fake_db.users.rows.append({
        "user_id": "uA", "email": "alex@example.com", "name": "Alex",
    })

    sent = []
    monkeypatch.setattr(email_service, "send_silent_reviewer_nudge",
                        lambda **kw: sent.append(kw))

    await silent_reviewer_nudge.send_silent_reviewer_nudges(fake_db)
    assert sent == [], "no candidates should have qualified"


@pytest.mark.asyncio
async def test_dry_run_reports_without_sending(fake_db, monkeypatch):
    import email_service
    import silent_reviewer_nudge

    _seed_token(fake_db, jti="jti_dry", created_days_ago=4)
    fake_db.users.rows.append({
        "user_id": "uA", "email": "alex@example.com", "name": "Alex",
    })
    sent = []
    monkeypatch.setattr(email_service, "send_silent_reviewer_nudge",
                        lambda **kw: sent.append(kw))

    results = await silent_reviewer_nudge.send_silent_reviewer_nudges(
        fake_db, dry_run=True,
    )

    assert sent == [], "dry_run must not fire real sends"
    row = next(r for r in fake_db.share_tokens.rows if r["jti"] == "jti_dry")
    assert row["nudged_at"] is None, "dry_run must not stamp nudged_at"
    assert any(r["status"] == "would_send" for r in results)


@pytest.mark.asyncio
async def test_recent_share_below_threshold_is_not_nudged(fake_db, monkeypatch):
    """A share created only 1 day ago (below default 3-day threshold)
    must not be nudged."""
    import email_service
    import silent_reviewer_nudge

    _seed_token(fake_db, jti="jti_young", created_days_ago=1)
    fake_db.users.rows.append({
        "user_id": "uA", "email": "alex@example.com", "name": "Alex",
    })

    sent = []
    monkeypatch.setattr(email_service, "send_silent_reviewer_nudge",
                        lambda **kw: sent.append(kw))

    await silent_reviewer_nudge.send_silent_reviewer_nudges(fake_db)
    assert sent == [], "too-recent share was still nudged"
