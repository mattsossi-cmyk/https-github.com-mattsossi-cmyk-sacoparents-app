"""Iteration 166 — Directory API swap (env-gated httpx + fallback).

Covers `professional_directory._fetch_directory()`:
  * env vars unset → returns the hardcoded _MOCK_DIRECTORY
  * env vars set + happy path → returns sibling rows
  * env vars set + row validation → drops rows missing required fields
  * env vars set + 502 → falls back to _MOCK_DIRECTORY (no cache)
  * env vars set + timeout → falls back to _MOCK_DIRECTORY
  * env vars set + non-JSON body → falls back
  * env vars set + missing `professionals` key → falls back
  * env vars set + every row invalid → falls back
  * 60s cache lives across two consecutive successful calls
  * cache does NOT poison a subsequent success after a failure
"""
from __future__ import annotations

import asyncio
import sys
from typing import Any, Dict, List, Optional

import httpx
import pytest

sys.path.insert(0, "/app/backend")

import professional_directory as pd  # noqa: E402


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _reset_env(monkeypatch, *, base=None, key=None) -> None:
    if base is None:
        monkeypatch.delenv("SACOPARENTSALIGN_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("SACOPARENTSALIGN_BASE_URL", base)
    if key is None:
        monkeypatch.delenv("SACOPARENTSALIGN_API_KEY", raising=False)
    else:
        monkeypatch.setenv("SACOPARENTSALIGN_API_KEY", key)
    pd._clear_directory_cache()


class _FakeAsyncClient:
    """Minimal drop-in for httpx.AsyncClient used in tests. Records
    every GET call so assertions can check the URL and headers.

    Instantiate with `response=` (an httpx.Response) or `raise_exc=`
    (an exception instance) to control behavior."""

    def __init__(self, *args, **kwargs):
        self._timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, headers=None):
        _FakeAsyncClient.last_url = url
        _FakeAsyncClient.last_headers = dict(headers or {})
        if _FakeAsyncClient.raise_exc:
            raise _FakeAsyncClient.raise_exc
        return _FakeAsyncClient.response


def _patch_httpx(monkeypatch, *, response=None, raise_exc=None) -> None:
    _FakeAsyncClient.response = response
    _FakeAsyncClient.raise_exc = raise_exc
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_headers = None
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


def _resp(status: int, json_body: Any = None, *, raw_body: Optional[bytes] = None) -> httpx.Response:
    """Build a real httpx.Response so status_code + json() + text work."""
    if raw_body is not None:
        return httpx.Response(status, content=raw_body)
    return httpx.Response(status, json=json_body)


# A valid sibling payload for happy-path tests.
def _valid_payload() -> Dict[str, Any]:
    return {
        "professionals": [
            {
                "id": "sib-001",
                "name": "Thabo Nkosi",
                "title": "Family Attorney",
                "city": "Cape Town",
                "specialties": ["family law"],
                "bio": "20 years family law",
                "contact_email": "thabo@sacoparentsalign.com",
                "photo_url": None,
            },
            {
                "id": "sib-002",
                "name": "Lerato Mokoena",
                "title": "Divorce Mediator",
                "city": "Pretoria",
                "specialties": ["mediation"],
                "bio": "12 years mediation",
                "contact_email": "lerato@sacoparentsalign.com",
                "photo_url": None,
            },
        ],
    }


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_fetch_directory_returns_mock_when_env_missing(monkeypatch):
    _reset_env(monkeypatch)
    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY
    assert len(rows) >= 5


def test_fetch_directory_hits_sibling_when_env_set(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(200, _valid_payload()))
    rows = asyncio.run(pd._fetch_directory())
    assert len(rows) == 2
    assert rows[0]["id"] == "sib-001"
    assert _FakeAsyncClient.last_url == (
        "https://align.example.com/api/directory/professionals"
    )
    assert _FakeAsyncClient.last_headers.get("Authorization") == "Bearer secret-abc"


def test_fetch_directory_drops_invalid_rows(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(200, {
        "professionals": [
            {"id": "ok", "name": "Valid Row", "contact_email": "ok@x.com"},
            {"id": "", "name": "Bad", "contact_email": "b@x.com"},  # empty id
            {"name": "Missing Id", "contact_email": "b@x.com"},      # no id
            {"id": "no-email", "name": "No Email"},                  # no contact_email
            "not a dict",                                             # wrong type
        ],
    }))
    rows = asyncio.run(pd._fetch_directory())
    assert len(rows) == 1
    assert rows[0]["id"] == "ok"


def test_fetch_directory_falls_back_on_502(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(502, {"error": "bad gateway"}))
    rows = asyncio.run(pd._fetch_directory())
    # → mock roster
    assert rows == pd._MOCK_DIRECTORY


def test_fetch_directory_falls_back_on_timeout(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, raise_exc=httpx.ConnectTimeout("boom"))
    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY


def test_fetch_directory_falls_back_on_bad_json(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(200, raw_body=b"not json at all"))
    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY


def test_fetch_directory_falls_back_when_professionals_missing(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(200, {"other": "shape"}))
    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY


def test_fetch_directory_falls_back_when_all_rows_invalid(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    _patch_httpx(monkeypatch, response=_resp(200, {"professionals": [{"foo": "bar"}]}))
    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY


def test_fetch_directory_uses_cache_on_second_call(monkeypatch):
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    call_count = {"n": 0}

    async def _wrapped(base, key):
        call_count["n"] += 1
        return [{
            "id": "sib-cached", "name": "Cached", "contact_email": "c@x.com",
        }]
    monkeypatch.setattr(pd, "_fetch_directory_from_sibling", _wrapped)

    r1 = asyncio.run(pd._fetch_directory())
    r2 = asyncio.run(pd._fetch_directory())
    assert r1 == r2 == [{"id": "sib-cached", "name": "Cached", "contact_email": "c@x.com"}]
    assert call_count["n"] == 1  # cache hit on 2nd call


def test_fetch_directory_does_not_cache_fallback(monkeypatch):
    """A failure should NOT poison the cache with the mock — the very
    next call must retry the sibling. Otherwise a brief outage would
    trap the app in mock-mode for 60 seconds."""
    _reset_env(
        monkeypatch,
        base="https://align.example.com",
        key="secret-abc",
    )
    call_count = {"n": 0}

    async def _wrapped(base, key):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # fail
        return [{"id": "sib-recovered", "name": "R", "contact_email": "r@x.com"}]
    monkeypatch.setattr(pd, "_fetch_directory_from_sibling", _wrapped)

    r1 = asyncio.run(pd._fetch_directory())
    assert r1 == pd._MOCK_DIRECTORY  # fallback
    r2 = asyncio.run(pd._fetch_directory())
    assert r2 == [{"id": "sib-recovered", "name": "R", "contact_email": "r@x.com"}]
    assert call_count["n"] == 2  # retried immediately, no cache poison


def test_fetch_directory_skips_network_when_only_one_env_set(monkeypatch):
    """Both vars must be present — a half-configured env goes to mock."""
    _reset_env(monkeypatch, base="https://align.example.com", key=None)
    called = {"n": 0}

    async def _wrapped(base, key):
        called["n"] += 1
        return []
    monkeypatch.setattr(pd, "_fetch_directory_from_sibling", _wrapped)

    rows = asyncio.run(pd._fetch_directory())
    assert rows == pd._MOCK_DIRECTORY
    assert called["n"] == 0
