"""iter132 - Extend GPT 5.6 Terra dispatch to Med + Psych deep dive.

Locks down that both `med-deep` and `psych-deep` regen endpoints now
honour a `model` param and dispatch through the same
`ai_summary.generate_executive_summary` / `ai_summary_gpt.generate_executive_summary_gpt`
pair as `edu-deep`.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture
def make_client(monkeypatch):
    from fastapi.testclient import TestClient
    from auth import UserPublic, get_current_user, get_db
    from server import app

    fake_user = UserPublic(
        user_id="uA", email="a@x.com", name="Alex",
        is_guest=False, is_admin=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        consent_current=True, ai_notice_current=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    class _FakeColl:
        async def update_one(self, filt, update):
            return None

    class _FakeDB:
        def __getitem__(self, name):
            return _FakeColl()

    fake_db = _FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db

    def _factory(module_path, module_name, cached_getter="_cached"):
        module = __import__(module_path)
        monkeypatch.setattr(
            module, cached_getter,
            AsyncMock(return_value={
                "cached": True,
                "report": {
                    "summary": {"score_total": 5},
                    "sections": [],
                    "ai_summary": "prior",
                },
                "generated_at": "2026-02-22T00:00:00+00:00",
            }),
        )
        monkeypatch.setattr(module, "_now_iso",
                            lambda: "2026-02-22T12:00:00+00:00")
        return TestClient(app), module

    yield _factory
    app.dependency_overrides.clear()


def _install_generators(monkeypatch, module):
    claude = AsyncMock(return_value="fresh claude")
    gpt = AsyncMock(return_value="fresh gpt")
    monkeypatch.setattr(module, "generate_executive_summary", claude)
    monkeypatch.setattr(module, "generate_executive_summary_gpt", gpt)
    return claude, gpt


@pytest.mark.parametrize("route_prefix, module_path", [
    ("/api/med-deep",   "med_deep_routes"),
    ("/api/psych-deep", "psych_deep_routes"),
])
def test_regen_defaults_to_claude(make_client, monkeypatch,
                                  route_prefix, module_path):
    client, module = make_client(module_path, module_path)
    claude, gpt = _install_generators(monkeypatch, module)
    res = client.post(f"{route_prefix}/report/regen-summary", json={})
    assert res.status_code == 200, res.text
    assert claude.await_count == 1
    assert gpt.await_count == 0
    assert res.json()["report"]["ai_summary_model"] == "claude"


@pytest.mark.parametrize("route_prefix, module_path", [
    ("/api/med-deep",   "med_deep_routes"),
    ("/api/psych-deep", "psych_deep_routes"),
])
def test_regen_model_gpt_dispatches_to_gpt(make_client, monkeypatch,
                                           route_prefix, module_path):
    client, module = make_client(module_path, module_path)
    claude, gpt = _install_generators(monkeypatch, module)
    res = client.post(
        f"{route_prefix}/report/regen-summary",
        json={"length": "standard", "model": "gpt"},
    )
    assert res.status_code == 200, res.text
    assert gpt.await_count == 1
    assert claude.await_count == 0
    body = res.json()
    assert body["report"]["ai_summary"] == "fresh gpt"
    assert body["report"]["ai_summary_model"] == "gpt"


@pytest.mark.parametrize("route_prefix, module_path", [
    ("/api/med-deep",   "med_deep_routes"),
    ("/api/psych-deep", "psych_deep_routes"),
])
def test_regen_invalid_model_falls_back_to_claude(make_client, monkeypatch,
                                                  route_prefix, module_path):
    client, module = make_client(module_path, module_path)
    claude, gpt = _install_generators(monkeypatch, module)
    res = client.post(
        f"{route_prefix}/report/regen-summary",
        json={"model": "definitely-not-a-model"},
    )
    assert res.status_code == 200, res.text
    assert claude.await_count == 1
    assert gpt.await_count == 0
    assert res.json()["report"]["ai_summary_model"] == "claude"
