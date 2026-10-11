"""Retention engine (owner-approved 2026-10-11), GAP-15 redaction, policy routes + robots.txt, invitation disclosure."""
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import retention
from joint_engine import REDACTED, _analyze_answers


class _Cursor:
    def __init__(self, docs): self.docs = docs
    def __aiter__(self): self.i = iter(self.docs); return self
    async def __anext__(self):
        try: return next(self.i)
        except StopIteration: raise StopAsyncIteration


class _Coll:
    def __init__(self, docs=None): self.docs = docs or []; self.ops = []
    def find(self, q=None, proj=None): return _Cursor([d for d in self.docs if _match(d, q or {})])
    async def find_one(self, q=None, proj=None, sort=None): return next((d for d in self.docs if _match(d, q or {})), None)
    async def update_one(self, q, op): self.ops.append(("update_one", q, op)); return None
    async def update_many(self, q, op): self.ops.append(("update_many", q, op)); return None
    async def delete_one(self, q): self.ops.append(("delete_one", q)); return None
    async def delete_many(self, q): self.ops.append(("delete_many", q)); return None
    async def insert_one(self, d): self.ops.append(("insert_one", d)); return None


def _match(d, q):
    for k, v in q.items():
        if k == "$or":
            if not any(_match(d, sub) for sub in v): return False
            continue
        val = d.get(k)
        if isinstance(v, dict):
            if "$exists" in v and (k in d) != v["$exists"]: return False
            if "$lte" in v and not (val is not None and val <= v["$lte"]): return False
            if "$gt" in v and not (val is not None and val > v["$gt"]): return False
            if "$nin" in v and val in v["$nin"]: return False
        elif val != v: return False
    return True


class _DB:
    def __init__(self, **colls):
        for n in ("joint_reports", "court_packets", "court_frozen_pdfs", "court_referrals", "retention_runs"):
            setattr(self, n, colls.get(n, _Coll()))


NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
LOG = logging.getLogger("t")


def test_engine_switched_off_by_default_and_cannot_run():
    import pytest
    assert retention.RETENTION_ENGINE_ENABLED is False
    db = _DB(joint_reports=_Coll([{"id": "r1", "closed_at": "2020-01-01T00:00:00+00:00", "safety_screenings": {"a": {"responses": {"a1": "x"}}}}]),
             court_packets=_Coll([{"id": "p1", "frozen": True, "created_at": "2020-01-01T00:00:00+00:00", "judge_email": "j@x", "opened_count": 0}]))
    async def send_email(**kw): raise AssertionError("must not send")
    for coro in (retention.purge_screening_answers(db, NOW), retention.purge_court_submissions(db, NOW),
                 retention.remind_judges(db, send_email, lambda: "x", "SA", NOW, LOG), retention.run_retention(db, send_email, lambda: "x", "SA", LOG)):
        with pytest.raises(retention.RetentionDisabled):
            asyncio.run(coro)
    assert db.joint_reports.ops == [] and db.court_packets.ops == [] and db.court_frozen_pdfs.ops == [] and db.retention_runs.ops == []
    pv = asyncio.run(retention.preview(db))
    assert pv["enabled"] is False and db.joint_reports.ops == []


def _enabled(monkeypatch):
    monkeypatch.setattr(retention, "RETENTION_ENGINE_ENABLED", True)


def test_constants_match_owner_decisions():
    assert retention.RAW_SCREENING_RETENTION_DAYS == 90 and retention.COURT_SUBMISSION_RETENTION_MONTHS == 6 and retention.JUDGE_REMINDER_LEAD_DAYS == 30
    assert "responses" in retention.PURGED_SCREENING_FIELDS and "flags" in retention.PURGED_SCREENING_FIELDS and "tier" not in retention.PURGED_SCREENING_FIELDS and "version" not in retention.PURGED_SCREENING_FIELDS


def test_court_purge_at_month_math():
    assert retention.court_purge_at("2026-01-31T10:00:00+00:00") == datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    assert retention.court_purge_at("2026-08-31T00:00:00Z") == datetime(2027, 2, 28, 0, 0, tzinfo=timezone.utc)
    assert retention.court_purge_at("garbage") is None


def test_screening_purge_keeps_tier_version_receipt(monkeypatch):
    _enabled(monkeypatch)
    old = (NOW - timedelta(days=91)).isoformat()
    recent = (NOW - timedelta(days=10)).isoformat()
    db = _DB(joint_reports=_Coll([
        {"id": "r1", "closed_at": old, "safety_screenings": {"a": {"responses": {"a1": "x"}, "flags": {"coerciveControl": True}, "tier": 2, "version": "A", "completed_at": "2026-05-01"}, "b": {"tier": 1, "version": "B"}}},
        {"id": "r2", "closed_at": recent, "safety_screenings": {"a": {"responses": {"a1": "x"}}}},
        {"id": "r3", "safety_screenings": {"a": {"responses": {"a1": "x"}}}},
    ]))
    n = asyncio.run(retention.purge_screening_answers(db, NOW))
    assert n == 1 and len(db.joint_reports.ops) == 1
    _, q, op = db.joint_reports.ops[0]
    assert q == {"id": "r1"}
    assert set(op["$unset"]) == {f"safety_screenings.a.{f}" for f in retention.PURGED_SCREENING_FIELDS}
    assert "safety_screenings.a.tier" not in op["$unset"] and "safety_screenings.a.version" not in op["$unset"] and "safety_screenings.a.completed_at" not in op["$unset"]
    assert op["$set"] == {"safety_screenings.a.purged_at": NOW.isoformat()}


def test_court_submission_deleted_entirely_after_six_months(monkeypatch):
    _enabled(monkeypatch)
    due = (NOW - timedelta(days=200)).isoformat()
    fresh = (NOW - timedelta(days=100)).isoformat()
    db = _DB(court_packets=_Coll([{"id": "p1", "frozen": True, "created_at": due, "report_id": "r1", "court_referral_id": "ref1"},
                                  {"id": "p2", "frozen": True, "created_at": fresh, "report_id": "r1"}]))
    n = asyncio.run(retention.purge_court_submissions(db, NOW))
    assert n == 1
    assert ("delete_many", {"packet_id": "p1"}) in db.court_frozen_pdfs.ops and ("delete_one", {"id": "p1"}) in db.court_packets.ops
    assert db.joint_reports.ops[0][2]["$pull"] == {"court_submissions": {"packet_id": "p1"}}
    assert db.court_referrals.ops[0][2]["$set"]["status"] == "expired"
    assert not any(o[1] == {"id": "p2"} for o in db.court_packets.ops)


def test_judge_reminder_30_days_before_only_if_unopened_once(monkeypatch):
    _enabled(monkeypatch)
    soon = (NOW - timedelta(days=183) + timedelta(days=20)).isoformat()   # purges in ~20 days (≈6 months - 20d)
    far = (NOW - timedelta(days=90)).isoformat()
    db = _DB(court_packets=_Coll([
        {"id": "p1", "frozen": True, "created_at": soon, "judge_email": "j@court.gov", "judge_name": "Judge Rivera", "opened_count": 0, "cause_number": "2026-CI-001"},
        {"id": "p2", "frozen": True, "created_at": soon, "judge_email": "j@court.gov", "opened_count": 3},
        {"id": "p3", "frozen": True, "created_at": far, "judge_email": "j@court.gov", "opened_count": 0},
        {"id": "p4", "frozen": True, "created_at": soon, "judge_email": "j@court.gov", "opened_count": 0, "purge_reminder_sent_at": "x"},
    ]))
    sent = []
    async def send_email(**kw): sent.append(kw)
    n = asyncio.run(retention.remind_judges(db, send_email, lambda: "https://x", "SA CoParents Align", NOW, LOG))
    assert n == 1 and len(sent) == 1 and sent[0]["to"] == "j@court.gov" and "2026-CI-001" in sent[0]["subject"] and "deleted" in sent[0]["html"]
    assert "a1" not in sent[0]["html"] and db.court_packets.ops[0][1] == {"id": "p1"}


def test_run_and_preview_record_results(monkeypatch):
    _enabled(monkeypatch)
    db = _DB()
    async def send_email(**kw): pass
    out = asyncio.run(retention.run_retention(db, send_email, lambda: "https://x", "SA", LOG))
    assert out["screening_slots_purged"] == 0 and out["court_submissions_deleted"] == 0 and db.retention_runs.ops[0][0] == "insert_one"
    pv = asyncio.run(retention.preview(db))
    assert pv["rules"]["judge_reminder_lead_days"] == 30 and pv["due_now"] == {"screening_slots": 0, "court_submissions": 0, "judge_reminders": 0}


def test_retention_engine_not_scheduled_and_no_admin_trigger():
    cron = open("/app/backend/cron_jobs.py", encoding="utf-8").read()
    assert "create_task(run_retention(" not in cron
    assert "retention" not in open("/app/.emergent/crons.yml", encoding="utf-8").read().lower()
    import glob
    for f in glob.glob("/app/backend/*.py"):
        if f.endswith("retention.py"): continue
        src = open(f, encoding="utf-8").read()
        assert "run_retention(" not in src and "purge_screening_answers(" not in src and "purge_court_submissions(" not in src and "/admin/retention" not in src.replace("# Retention admin preview route intentionally removed", ""), f


def test_redaction_replaces_only_marked_answer():
    ra = {"routines": "Bedtime at 8", "communication": "She never answers"}
    rb = {"routines": "Flexible evenings", "communication": "He texts too much"}
    _rows, _st, diffs = _analyze_answers(ra, rb, "Ava", {"a": ["communication"]})
    d = {x["key"]: x for x in diffs}
    if "communication" in d:
        assert d["communication"]["parent_a"] == REDACTED and d["communication"]["parent_b"] == "He texts too much" and d["communication"]["redacted"] == {"a": True, "b": False}
    assert all("key" in x for x in diffs)
    assert '"/joint/reports/{rid}/redactions"' in open("/app/backend/safety_screening.py", encoding="utf-8").read()
    jr = open("/app/frontend/src/pages/JointReport.jsx", encoding="utf-8").read()
    assert "Redact before release" in jr and "detail.is_creator" in jr


def test_invitation_and_consent_references_removed():
    jh = open("/app/backend/joint_helpers.py", encoding="utf-8").read()
    assert "side by side" not in jh and "redact a passage" not in jh
    import json
    P = json.load(open("/app/frontend/src/content/policies.json", encoding="utf-8"))
    t = " ".join(p for s in P["sharing-consent"]["sections"] for p in s.get("paragraphs", []))
    assert "side by side" not in t and "redact" not in t


def test_policy_pages_not_routed_and_unlinked():
    import os
    app = open("/app/frontend/src/App.js", encoding="utf-8").read()
    for slug in ("privacy", "confidentiality", "sharing-consent", "security-practices"):
        assert f'path="/{slug}"' not in app
    assert "<PolicyPage" not in app and not os.path.exists("/app/frontend/public/robots.txt")
    import os
    hits = []
    for root, _d, files in os.walk("/app/frontend/src"):
        for f in files:
            if f.endswith((".js", ".jsx")) and f not in ("App.js", "PolicyPage.jsx"):
                src = open(os.path.join(root, f), encoding="utf-8").read()
                hits += [(f, s) for s in ("/privacy", "/confidentiality", "/sharing-consent", "/security-practices") if re.search(rf'(to|href)=["\']{re.escape(s)}["\']', src)]
    assert hits == []
