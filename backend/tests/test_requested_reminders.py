import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

import email_service  # noqa: E402
from court_checklist import progress_rows  # noqa: E402
from requested_reminders import make_unsubscribe_token, read_unsubscribe_token, send_requested_reminders  # noqa: E402

NOW = datetime(2026, 6, 8, 14, tzinfo=timezone.utc)  # a Monday, 9am Central


async def _seed(db):
    await db.users.insert_many([{"user_id": u, "email": f"{u}@example.com", "name": f"{u.title()} Parent"}
                                for u in ("wait2", "done", "flagged", "unsub", "casepar", "codepar")])
    await db.court_requested.insert_many([
        {"user_id": "wait2", "keys": ["coparent", "self"]},
        {"user_id": "done", "keys": ["self"]},
        {"user_id": "flagged", "keys": ["self"]},
        {"user_id": "unsub", "keys": ["self"], "reminders_off": True},
    ])
    await db.self_assessment_history.insert_one({"user_id": "done", "completed_at": "2026-06-01T10:00:00+00:00", "answers": {"q1": 5}})
    await db.portal_state.insert_many([
        {"user_id": "flagged", "safety_ack": {"flagged": True}},
        {"user_id": "codepar", "court_key": "CC-TEST01"},
    ])
    await db.joint_alignment_cases.insert_one({
        "case_id": "SA-TEST01", "status": "in_progress", "assessment_type": "co-parenting",
        "assigned_steps": [{"assessment_type": "medical", "required": True}],
        "parents": [{"user_id": "casepar", "email": "casepar@example.com"}],
    })
    await db.portal_court_keys.insert_one({"case_id": "CC-TEST01", "requested": ["parallel"], "revoked_at": None, "created_by": "pro"})


def test_weekly_requested_reminder_sweep(monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_requested_reminder", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_req_reminders"
        await client.drop_database(name)
        db = client[name]
        try:
            await _seed(db)
            first = await send_requested_reminders(db, now=NOW)
            second = await send_requested_reminders(db, now=NOW)
            rows = await progress_rows(db, "done", ["self", "medical"])
            return first, second, rows
        finally:
            await client.drop_database(name)

    first, second, rows = asyncio.run(run())
    by_email = {kw["to_email"]: kw["waiting"] for kw in sent}
    # Parent ticks, joint-case requests and court-code requests all count; finished / flagged / unsubscribed skipped.
    assert by_email == {"wait2@example.com": 2, "casepar@example.com": 1, "codepar@example.com": 1}
    assert first["all_done"] == 1 and first["skipped_safety"] == 1 and first["skipped_unsubscribed"] == 1
    assert all("/api/court-path/reminders/unsubscribe?token=" in kw["unsubscribe_url"] for kw in sent)
    assert second["sent"] == 0 and second["already_sent"] == 3  # once per week
    # Professional view is status-only.
    assert rows == [{"key": "self", "title": "Self-Assessment", "status": "done", "finished_at": "2026-06-01T10:00:00+00:00"},
                    {"key": "medical", "title": "Medical Assessment", "status": "todo", "finished_at": None}]


def test_reminder_email_is_neutral(monkeypatch):
    out = {}
    monkeypatch.setattr(email_service, "_send", lambda **kw: out.update(kw))
    email_service.send_requested_reminder(to_email="a@example.com", waiting=2, cta_url="https://x/login",
                                          unsubscribe_url="https://x/unsub", first_name="Avery")
    body = out["html"] + out["text"] + out["subject"]
    assert "You have 2 assessments waiting for you" in body and "https://x/unsub" in body and "Sign in" in body
    for word in ("Co-Parenting", "Self-Assessment", "Medical", "Educational", "Psychological", "Foundation", "Parallel"):
        assert word not in body


def test_unsubscribe_token_roundtrip():
    assert read_unsubscribe_token(make_unsubscribe_token("u1")) == "u1"
    assert read_unsubscribe_token("garbage") is None


def test_completion_alert_once_per_parent_and_case(monkeypatch):
    import completion_alerts

    sent = []
    monkeypatch.setattr(email_service, "send_completion_alert", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_completion_alerts"
        await client.drop_database(name)
        db = client[name]
        try:
            await db.users.insert_many([{"user_id": "pro", "email": "pro@example.com"}, {"user_id": "pro2", "email": "pro2@example.com"},
                                        {"user_id": "par", "email": "par@example.com"}, {"user_id": "alignpar", "email": "a@example.com"}])
            await db.portal_state.insert_many([{"user_id": "par", "court_key": "CC-T1"}, {"user_id": "alignpar", "court_key": "AL-1"}])
            await db.portal_court_keys.insert_many([
                {"case_id": "CC-T1", "created_by": "pro", "label": "Smith v Smith", "requested": ["self"]},
                {"case_id": "AL-1", "requested": ["self"]},  # Align-made: no professional here
            ])
            await db.joint_alignment_cases.insert_one({"case_id": "SA-T1", "status": "in_progress", "professional_created_by": "pro2",
                                                       "assigned_steps": [{"assessment_type": "medical", "required": True}],
                                                       "parents": [{"user_id": "par"}]})
            assert await completion_alerts.check_and_alert(db, "par") == 0  # nothing finished yet
            await db.self_assessment_history.insert_many([{"user_id": u, "completed_at": "2026-06-01T10:00:00+00:00"} for u in ("par", "alignpar")])
            first = await completion_alerts.check_and_alert(db, "par")
            again = await completion_alerts.check_and_alert(db, "par")
            align = await completion_alerts.check_and_alert(db, "alignpar")
            return first, again, align
        finally:
            await client.drop_database(name)

    first, again, align = asyncio.run(run())
    assert (first, again, align) == (1, 0, 0)  # joint case still waits on Medical
    assert len(sent) == 1 and {k: sent[0][k] for k in ("to_email", "case_ref", "label")} == {
        "to_email": "pro@example.com", "case_ref": "CC-T1", "label": "Smith v Smith"}
    assert sent[0]["cta_url"].endswith("/professional/joint-alignment/mine")


def test_completion_email_names_nobody(monkeypatch):
    out = {}
    monkeypatch.setattr(email_service, "_send", lambda **kw: out.update(kw))
    email_service.send_completion_alert(to_email="p@example.com", case_ref="CC-T1", label="Smith", cta_url="https://x/mine")
    body = out["html"] + out["text"]
    assert "CC-T1 (Smith)" in body and "https://x/mine" in body
    for word in ("Self-Assessment", "Medical", "Co-Parenting Assessment", "answer:"):
        assert word not in body


def test_progress_pdf_status_only():
    from progress_pdf import build_progress_pdf

    pdf = build_progress_pdf({"kind": "Court code", "ref": "CC-T1", "label": "Smith", "state": "Active",
                              "generated_at": "2026-06-08T14:00:00+00:00",
                              "parents": [{"name": "Avery", "assessments": [
                                  {"key": "self", "title": "Self-Assessment", "status": "done", "finished_at": "2026-06-01T10:00:00+00:00"},
                                  {"key": "medical", "title": "Medical Assessment", "status": "todo", "finished_at": None}]},
                                  {"name": "Parent 2", "assessments": None}]})
    assert pdf.startswith(b"%PDF")


def test_completion_alert_respects_professional_opt_out(monkeypatch):
    import completion_alerts

    sent = []
    monkeypatch.setattr(email_service, "send_completion_alert", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_completion_optout"
        await client.drop_database(name)
        db = client[name]
        try:
            await db.users.insert_many([{"user_id": "pro", "email": "pro@example.com"}, {"user_id": "par", "email": "par@example.com"}])
            await db.portal_state.insert_one({"user_id": "par", "court_key": "CC-T2"})
            await db.portal_court_keys.insert_one({"case_id": "CC-T2", "created_by": "pro", "requested": ["self"]})
            await db.professional_prefs.insert_one({"user_id": "pro", "completion_alerts_off": True})
            await db.self_assessment_history.insert_one({"user_id": "par", "completed_at": "2026-06-01T10:00:00+00:00"})
            n = await completion_alerts.check_and_alert(db, "par")
            rec = await db.completion_alerts.find_one({"ref": "CC-T2"}, {"_id": 0, "status": 1})
            return n, rec
        finally:
            await client.drop_database(name)

    n, rec = asyncio.run(run())
    assert n == 0 and sent == [] and rec == {"status": "skipped_opted_out"}


def test_professional_nudge_email_is_neutral(monkeypatch):
    out = {}
    monkeypatch.setattr(email_service, "_send", lambda **kw: out.update(kw))
    email_service.send_requested_reminder(to_email="a@example.com", waiting=3, cta_url="https://x/login",
                                          unsubscribe_url="https://x/unsub", from_professional=True)
    body = out["html"] + out["text"]
    assert "Your professional sent you a gentle reminder: you have 3 assessments waiting for you." in body
    assert "https://x/unsub" in body and out["subject"] == "A gentle reminder from your professional"
    for word in ("Self-Assessment", "Medical", "Educational", "Psychological", "Foundation", "Parallel"):
        assert word not in body


def test_professional_digest_counts_weekly_and_unchanged(monkeypatch):
    import professional_digest

    sent = []
    monkeypatch.setattr(email_service, "send_professional_digest", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_pro_digest"
        await client.drop_database(name)
        db = client[name]
        try:
            await db.users.insert_many([{"user_id": u, "email": f"{u}@example.com", "name": u.title()}
                                        for u in ("pro", "off", "done1", "mid1", "new1", "arch1")])
            await db.portal_court_keys.insert_many([
                {"case_id": "CC-A", "created_by": "pro", "requested": ["self", "medical"], "archived_at": None},
                {"case_id": "CC-ARCH", "created_by": "pro", "requested": ["self"], "archived_at": "2026-06-01T00:00:00+00:00"},
                {"case_id": "CC-OFF", "created_by": "off", "requested": ["self"]},
            ])
            await db.portal_state.insert_many([{"user_id": "done1", "court_key": "CC-A"}, {"user_id": "mid1", "court_key": "CC-A"},
                                               {"user_id": "arch1", "court_key": "CC-ARCH"}, {"user_id": "new1", "court_key": "CC-OFF"}])
            await db.self_assessment_history.insert_many([{"user_id": u, "completed_at": "2026-06-01T10:00:00+00:00"} for u in ("done1", "mid1")])
            await db.child_needs_assessments.insert_one({"user_id": "done1", "completed_at": {"medical": "2026-06-02T10:00:00+00:00"}})
            await db.joint_alignment_cases.insert_one({"case_id": "SA-X", "status": "pending", "professional_created_by": "pro",
                                                       "assessment_type": "co-parenting", "parents": [{"email": "x@example.com"}],
                                                       "created_at": "2099-01-01T00:00:00+00:00", "expires_at": "2099-12-31T00:00:00+00:00"})
            await db.professional_prefs.insert_one({"user_id": "off", "digest_off": True})
            counts = await professional_digest.digest_counts(db, "pro")
            first = await professional_digest.send_professional_digests(db, now=NOW)
            again = await professional_digest.send_professional_digests(db, now=NOW)
            from datetime import timedelta
            nxt = await professional_digest.send_professional_digests(db, now=NOW + timedelta(days=7))
            return counts, first, again, nxt
        finally:
            await client.drop_database(name)

    counts, first, again, nxt = asyncio.run(run())
    assert counts == {"finished": 1, "in_progress": 1, "not_started": 1}  # archived code excluded; unjoined parent = not started
    assert first["sent"] == 1 and first["skipped_off"] == 1
    assert again["already_sent"] == 1 and again["sent"] == 0
    assert nxt["skipped_unchanged"] == 1 and nxt["sent"] == 0
    assert len(sent) == 1 and sent[0]["counts"] == counts and "/api/professional/digest/unsubscribe?token=" in sent[0]["unsubscribe_url"]


def test_professional_digest_email_is_counts_only(monkeypatch):
    out = {}
    monkeypatch.setattr(email_service, "_send", lambda **kw: out.update(kw))
    email_service.send_professional_digest(to_email="p@example.com", counts={"finished": 3, "in_progress": 5, "not_started": 2},
                                           cta_url="https://x/mine", unsubscribe_url="https://x/unsub")
    body = out["html"] + out["text"]
    assert "This week in My cases: 3 parents finished, 5 in progress, 2 not started." in body
    assert "https://x/unsub" in body and "Open My cases" in body
