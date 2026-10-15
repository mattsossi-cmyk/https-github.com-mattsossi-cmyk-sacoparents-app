"""Communication Builder: suggested wording must keep the parent's essentials, or be withheld; sample history purge."""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

import portal_ai  # noqa: E402
from portal_routes import SAMPLE_BIFF_LOGS, SAMPLE_MILESTONES, purge_sample_history, without_samples  # noqa: E402

PICKUP = "You're late AGAIN. Can you pick up Sam at 5 or 6 tomorrow? I can't do Saturday."


def test_missing_facts_flags_dropped_time_question_and_boundary():
    gaps = portal_ai.missing_facts(PICKUP, "Thanks for letting me know. Let's keep the focus on our child...")
    assert "5" in gaps and "6" in gaps and "tomorrow" in gaps and "saturday" in gaps
    assert "the parent's question" in gaps
    assert any(g.startswith("the parent's boundary") for g in gaps)
    assert "a complete message without '...'" in gaps


def test_missing_facts_passes_a_faithful_rewrite():
    good = "Could you pick up Sam at 5 or 6 tomorrow? Saturday doesn't work for me."
    assert portal_ai.missing_facts(PICKUP, good) == []


def test_missing_facts_counts_every_question_and_exact_numbers():
    raw = "Is pickup at 5? And who has the 2 bags?"
    assert portal_ai.missing_facts(raw, "Is pickup at 15? Who has the 2 bags?") == ["5"]
    assert portal_ai.missing_facts(raw, "Please confirm pickup at 5 and the 2 bags?") == ["all 2 of the parent's questions"]


class _FakeChat:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def with_model(self, *_):
        return self

    async def send_message(self, msg):
        self.sent.append(msg.text)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return json.dumps(r)


def _run(monkeypatch, replies):
    chat = _FakeChat(replies)
    monkeypatch.setattr(portal_ai, "LlmChat", lambda **_: chat)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test")
    return asyncio.run(portal_ai.refine_biff(PICKUP)), chat


GOOD = {"biff": "Could you pick up Sam at 5 or 6 tomorrow? Saturday doesn't work for me.", "flags": ["Hostile tone"], "risk": "Escalation Flag"}
BAD = {"biff": "Thanks for the update. Let's keep the focus on our child.", "flags": [], "risk": "Low Risk"}


def test_refine_ok_first_try(monkeypatch):
    out, chat = _run(monkeypatch, [GOOD])
    assert out["status"] == "ok" and out["biff"] == GOOD["biff"] and out["risk"] == "Escalation Flag"
    assert len(chat.sent) == 1


def test_refine_retries_once_then_ok(monkeypatch):
    out, chat = _run(monkeypatch, [BAD, GOOD])
    assert out["status"] == "ok" and out["biff"] == GOOD["biff"]
    assert len(chat.sent) == 2 and "left out" in chat.sent[1]


def test_refine_withholds_draft_and_risk_when_still_missing(monkeypatch):
    out, chat = _run(monkeypatch, [BAD, BAD])
    assert out["status"] == "unavailable"
    assert out["biff"] == "" and out["risk"] is None and out["flags"] == []
    assert out["missing"]
    assert len(chat.sent) == 2


def test_refine_raises_when_provider_down(monkeypatch):
    with pytest.raises(RuntimeError):
        _run(monkeypatch, [RuntimeError("down"), RuntimeError("down")])


def test_without_samples_keeps_parent_entries():
    mine = {"id": 99, "type": "success", "title": "On-Time Handoff Completed", "date": "2026-06-01", "note": "mine"}
    assert without_samples("milestones", SAMPLE_MILESTONES + [mine]) == [mine]
    assert without_samples("biff_logs", SAMPLE_BIFF_LOGS) == []


def test_purge_sample_history_only_removes_exact_samples():
    real_m = {"id": 1718000000000, "type": "friction", "title": "Late reply", "date": "2026-06-02", "note": "real"}
    real_b = {"id": 1718000000001, "timestamp": "2026-06-02 10:00", "category": "BIFF Exchange", "original": "x", "biff": "y"}

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_sample_purge"
        await client.drop_database(name)
        db = client[name]
        try:
            await db.portal_state.insert_many([
                {"user_id": "a", "milestones": SAMPLE_MILESTONES + [real_m], "biff_logs": SAMPLE_BIFF_LOGS + [real_b]},
                {"user_id": "b", "milestones": [real_m], "biff_logs": []},
            ])
            await db.portal_pdf_shares.insert_one({"token": "t", "payload": {"milestones": SAMPLE_MILESTONES, "biff_logs": [real_b]}})
            first = await purge_sample_history(db)
            second = await purge_sample_history(db)
            a = await db.portal_state.find_one({"user_id": "a"})
            b = await db.portal_state.find_one({"user_id": "b"})
            share = await db.portal_pdf_shares.find_one({"token": "t"})
            return first, second, a, b, share
        finally:
            await client.drop_database(name)

    first, second, a, b, share = asyncio.run(run())
    assert first > 0 and second == 0
    assert a["milestones"] == [real_m] and a["biff_logs"] == [real_b]
    assert b["milestones"] == [real_m]
    assert share["payload"]["milestones"] == [] and share["payload"]["biff_logs"] == [real_b]
