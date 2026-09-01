"""iter130 - GPT 5.6 Terra alternate for AI executive summary.

Covers:
  1. `ai_summary_gpt.generate_executive_summary_gpt` uses the
     openai/gpt-5.6-terra model via emergentintegrations.
  2. Same signals extraction as `ai_summary.generate_executive_summary`
     so both generators are apples-to-apples.
  3. `/edu-deep/report/regen-summary` accepts a `model="gpt"` param
     and dispatches to the GPT generator; default (`claude` / omitted)
     still uses the Claude generator.
  4. Invalid model values fall back to `claude`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ---------------------------------------------------------------------------
# Module-level tests: the GPT generator hits the right model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gpt_summary_targets_gpt56_terra(monkeypatch):
    """The GPT variant must call the openai/gpt-5.6-terra model."""
    import ai_summary_gpt

    captured = {}

    class _FakeChat:
        def __init__(self, **kw):
            captured["init"] = kw

        def with_model(self, provider, model):
            captured["model"] = (provider, model)
            return self

        async def send_message(self, msg):
            captured["prompt"] = getattr(msg, "text", None)
            return "GPT-generated summary text."

    monkeypatch.setattr(ai_summary_gpt, "LlmChat", _FakeChat)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-test")

    out = await ai_summary_gpt.generate_executive_summary_gpt(
        product_name="Educational Needs Deep Dive",
        report={"summary": {"score_total": 8}, "sections": []},
        length="standard",
    )

    assert out == "GPT-generated summary text."
    assert captured["model"] == ("openai", "gpt-5.6-terra")
    assert "Educational Needs Deep Dive" in (captured["prompt"] or "")


@pytest.mark.asyncio
async def test_gpt_summary_returns_none_without_key(monkeypatch):
    """Absent EMERGENT_LLM_KEY must fail-soft (return None) so the
    Claude fallback still resolves at the endpoint layer."""
    import ai_summary_gpt

    monkeypatch.delenv("EMERGENT_LLM_KEY", raising=False)
    out = await ai_summary_gpt.generate_executive_summary_gpt(
        product_name="X", report={}, length="standard",
    )
    assert out is None


@pytest.mark.asyncio
async def test_gpt_summary_returns_none_on_exception(monkeypatch):
    """LLM SDK exceptions must never propagate."""
    import ai_summary_gpt

    class _BoomChat:
        def __init__(self, **kw):
            pass

        def with_model(self, *a, **kw):
            return self

        async def send_message(self, msg):
            raise RuntimeError("gateway timeout")

    monkeypatch.setattr(ai_summary_gpt, "LlmChat", _BoomChat)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-test")

    out = await ai_summary_gpt.generate_executive_summary_gpt(
        product_name="X", report={}, length="standard",
    )
    assert out is None


# ---------------------------------------------------------------------------
# Route-level: model dispatch on /edu-deep/report/regen-summary
# ---------------------------------------------------------------------------

@pytest.fixture
def edu_client(monkeypatch):
    """FastAPI TestClient wired to `edu_deep_routes` with cached report
    + user overrides so we can hit the regen endpoint without a real DB."""
    from fastapi.testclient import TestClient
    from auth import UserPublic, get_current_user, get_db
    import edu_deep_routes
    from server import app

    fake_user = UserPublic(
        user_id="uA", email="alex@test.local", name="Alex",
        is_guest=False, is_admin=False,
        created_at="2026-02-22T00:00:00+00:00",
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    cached_state = {
        "cached": True,
        "report": {
            "summary": {"score_total": 8, "band": "moderate"},
            "sections": [],
            "ai_summary": "initial claude summary",
        },
        "generated_at": "2026-02-22T00:00:00+00:00",
    }

    class _FakeColl:
        async def update_one(self, filt, update):
            return None

    class _FakeDB:
        def __getitem__(self, name):
            return _FakeColl()

    fake_db = _FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _cached_report(db, user_id):
        return dict(cached_state)

    monkeypatch.setattr(edu_deep_routes, "_cached_report", _cached_report)
    monkeypatch.setattr(edu_deep_routes, "_now_iso",
                        lambda: "2026-02-22T12:00:00+00:00")

    client = TestClient(app)
    try:
        yield client, cached_state
    finally:
        app.dependency_overrides.clear()


def test_regen_summary_defaults_to_claude(edu_client, monkeypatch):
    """Missing `model` param → Claude generator is called."""
    import edu_deep_routes

    claude_mock = AsyncMock(return_value="fresh claude summary")
    gpt_mock = AsyncMock(return_value="fresh GPT summary")
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary", claude_mock)
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary_gpt", gpt_mock)

    client, _ = edu_client
    res = client.post("/api/edu-deep/report/regen-summary", json={})
    assert res.status_code == 200, res.text
    assert claude_mock.await_count == 1
    assert gpt_mock.await_count == 0
    assert res.json()["report"]["ai_summary"] == "fresh claude summary"
    assert res.json()["report"]["ai_summary_model"] == "claude"


def test_regen_summary_model_gpt_dispatches_to_gpt(edu_client, monkeypatch):
    """`model="gpt"` → GPT generator, and the response marks the model."""
    import edu_deep_routes

    claude_mock = AsyncMock(return_value="fresh claude summary")
    gpt_mock = AsyncMock(return_value="fresh GPT summary")
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary", claude_mock)
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary_gpt", gpt_mock)

    client, _ = edu_client
    res = client.post(
        "/api/edu-deep/report/regen-summary",
        json={"length": "standard", "model": "gpt"},
    )
    assert res.status_code == 200, res.text
    assert gpt_mock.await_count == 1
    assert claude_mock.await_count == 0
    body = res.json()
    assert body["report"]["ai_summary"] == "fresh GPT summary"
    assert body["report"]["ai_summary_model"] == "gpt"


def test_regen_summary_invalid_model_falls_back_to_claude(edu_client, monkeypatch):
    """Garbage `model` value → downgraded to claude (never trusts input)."""
    import edu_deep_routes

    claude_mock = AsyncMock(return_value="fresh claude")
    gpt_mock = AsyncMock(return_value="fresh gpt")
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary", claude_mock)
    monkeypatch.setattr(edu_deep_routes, "generate_executive_summary_gpt", gpt_mock)

    client, _ = edu_client
    res = client.post(
        "/api/edu-deep/report/regen-summary",
        json={"model": "hack-the-planet"},
    )
    assert res.status_code == 200, res.text
    assert claude_mock.await_count == 1
    assert gpt_mock.await_count == 0
    assert res.json()["report"]["ai_summary_model"] == "claude"
