"""The old inbound webhooks stay off (503) whatever secrets are stored, unless WEBHOOKS_ENABLED is exactly "true"."""
from __future__ import annotations

import os
import sys

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from server import app  # noqa: E402

SAFETY = "/api/internal/safety-status"
INVITE = "/api/professional/directory/invite/accept-webhook"


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    with TestClient(app) as c:
        yield c


@pytest.fixture
def stored_secrets(monkeypatch):
    monkeypatch.setenv("ALIGN_WEBHOOK_SECRET", "stored-old-value")
    monkeypatch.setenv("SACOPARENTSALIGN_WEBHOOK_SECRET", "stored-old-value")


@pytest.mark.parametrize("flag", [None, "", "false", "TRUE", "yes", "1"])
def test_stored_secrets_alone_never_switch_the_webhooks_on(client, stored_secrets, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("WEBHOOKS_ENABLED", raising=False)
    else:
        monkeypatch.setenv("WEBHOOKS_ENABLED", flag)
    assert client.post(SAFETY, json={}).status_code == 503
    assert client.post(INVITE, json={}).status_code == 503


def test_enabled_flag_plus_secret_turns_them_back_on(client, stored_secrets, monkeypatch):
    monkeypatch.setenv("WEBHOOKS_ENABLED", "true")
    assert client.post(SAFETY, json={}).status_code == 401
    assert client.post(INVITE, json={}).status_code == 401


def test_enabled_flag_without_a_secret_stays_off(client, monkeypatch):
    monkeypatch.setenv("WEBHOOKS_ENABLED", "true")
    monkeypatch.delenv("ALIGN_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("SACOPARENTSALIGN_WEBHOOK_SECRET", raising=False)
    assert client.post(SAFETY, json={}).status_code == 503
    assert client.post(INVITE, json={}).status_code == 503
