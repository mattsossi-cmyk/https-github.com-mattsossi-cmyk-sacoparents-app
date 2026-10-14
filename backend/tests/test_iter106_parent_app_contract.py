"""Iter-106: parent-app link contract — every refusal code, flag off/on, scope handling, invite lookup professional_id, UI-safe wording."""
import asyncio
import os
import re

import httpx
import pytest
import requests
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

import parent_app_contract as pac  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
FORBIDDEN = re.compile(r"safety|screening|flag|violence|abuse|secret|key", re.I)


def _fake(status, body=None, capture=None):
    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, method, url, **kw):
            if capture is not None:
                capture.update({"method": method, "url": url, **kw})
            return httpx.Response(status, json=body if body is not None else {})
    return FakeClient


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(pac, "PARENT_APP_LINK_CONTRACT", True)


@pytest.mark.parametrize("status,detail,exp_status,exp_msg", [
    (401, "Invalid key", 502, pac.MSG_CONFIG_ERROR),
    (503, "Not configured", 503, pac.MSG_NOT_CONFIGURED),
    (400, "Missing X-Professional-Id", 502, pac.MSG_CONFIG_ERROR),
    (404, "Not found", 404, pac.MSG_NO_ACCESS),
    (404, "No completed assessments found", 404, pac.MSG_NO_ASSESSMENTS),
    (404, "Invalid or expired link code", 400, pac.MSG_BAD_CODE),
    (500, "boom", 502, pac.MSG_UNREACHABLE),
])
def test_every_refusal_maps_to_neutral_wording(monkeypatch, on, status, detail, exp_status, exp_msg):
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(status, {"detail": detail}))
    with pytest.raises(HTTPException) as ei:
        _run(pac.export_assessments("p@x", "pro1", "case1"))
    assert (ei.value.status_code, ei.value.detail) == (exp_status, exp_msg)
    assert not FORBIDDEN.search(ei.value.detail), ei.value.detail


def test_verify_link_code_contract_body_and_headers(monkeypatch, on):
    cap = {}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, {"email": "Parent@X.com"}, cap))
    assert _run(pac.verify_link_code("ABCD1234", "pro1", "case1")) == "parent@x.com"
    assert cap["url"].endswith("/api/integrations/verify-link-code")
    assert cap["json"] == {"code": "ABCD1234", "professional_id": "pro1", "case_id": "case1"}
    assert cap["headers"]["X-Professional-Id"] == "pro1" and cap["headers"]["X-Case-Id"] == "case1" and "X-Integration-Key" in cap["headers"]
    with pytest.raises(HTTPException) as ei:
        _run(pac.verify_link_code("ABCD1234", None, None))
    assert ei.value.status_code == 400


def test_verify_link_code_flag_off_is_legacy(monkeypatch):
    monkeypatch.setattr(pac, "PARENT_APP_LINK_CONTRACT", False)
    cap = {}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, {"email": "p@x"}, cap))
    _run(pac.verify_link_code("CODE", None, None))
    assert cap["json"] == {"code": "CODE"} and set(cap["headers"]) == {"X-Integration-Key"}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(404, {"detail": "nope"}))
    with pytest.raises(HTTPException) as ei:
        _run(pac.verify_link_code("CODE", None, None))
    assert ei.value.status_code == 400 and ei.value.detail == pac.MSG_BAD_CODE


def test_export_scope_case_keeps_items_legacy_strips_them(monkeypatch, on):
    full = {"access_scope": "case", "assessments": [{"assessment_id": "1", "responses": {"q1": "a"}}], "safety_flags": {"tier": 2}}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, full))
    d = _run(pac.export_assessments("p@x", "pro1", "case1"))
    assert d["assessments"][0]["responses"] == {"q1": "a"} and d["safety_flags"] == {"tier": 2}
    legacy = {"access_scope": "legacy_unscoped", "assessments": [{"assessment_id": "1", "summary": "ok", "responses": {"q1": "leak"}}], "safety_flags": {"tier": 3}}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, legacy))
    d = _run(pac.export_assessments("p@x", "pro1", "case1"))
    assert "responses" not in d["assessments"][0] and d["safety_flags"] is None and d["access_scope"] == "legacy_unscoped"


def test_safe_contact_assign_aggregate_calls(monkeypatch, on):
    cap = {}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, {"access_scope": "case", "safe_contact": {"method": "email"}}, cap))
    assert _run(pac.fetch_safe_contact("p@x", "pro1", "case1")) == {"method": "email"}
    assert cap["url"].endswith("/api/integrations/safe-contact") and cap["params"] == {"email": "p@x"}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, {"ok": True}, cap))
    assert _run(pac.assign_screening_version("p@x", "B", "pro1", "case1")) is True
    assert cap["method"] == "POST" and cap["json"] == {"email": "p@x", "version": "B"}
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(200, {"ratings": {"communication": 3}}, cap))
    assert _run(pac.fetch_aggregate("pro1", "case1"))["ratings"] == {"communication": 3}
    assert cap["params"] == {"case_id": "case1"} and cap["headers"]["X-Professional-Id"] == "pro1" and "X-Case-Id" not in cap["headers"]
    monkeypatch.setattr(pac.httpx, "AsyncClient", _fake(404, {"detail": "Not found"}))
    with pytest.raises(HTTPException) as ei:
        _run(pac.fetch_safe_contact("legacy@x", "pro1", "case1"))
    assert ei.value.status_code == 404 and ei.value.detail == pac.MSG_NO_ACCESS


def test_unreachable_is_neutral(monkeypatch, on):
    class Boom:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, *a, **k): raise httpx.ConnectError("down")
    monkeypatch.setattr(pac.httpx, "AsyncClient", Boom)
    with pytest.raises(HTTPException) as ei:
        _run(pac.fetch_aggregate("pro1", "case1"))
    assert ei.value.status_code == 502 and ei.value.detail == pac.MSG_UNREACHABLE


def test_invite_lookup_returns_professional_id_and_bridge_routes_hidden_when_flag_off():
    from casekit import completed_case
    pro, _a, _b, d, _ = completed_case(API)
    rid = d["id"]
    inv = requests.get(f"{API}/joint/reports/{rid}", cookies=pro.cookies).json()
    token = (inv.get("invitations") or [{}])[0].get("token")
    if token:
        r = requests.get(f"{API}/integrations/case-invite/{token}", headers={"X-Integration-Key": os.environ["INTEGRATION_SHARED_SECRET"]})
        assert r.status_code == 200 and r.json()["professional_id"], r.text
    assert requests.get(f"{API}/integrations/case-invite/x", headers={"X-Integration-Key": "wrong"}).status_code == 401
    r = pro.get(f"{API}/joint/reports/{rid}/bridge/safe-contact/a")
    assert r.status_code == 404 and r.json()["detail"] == "Not available"
    assert pro.get(f"{API}/joint/reports/{rid}/bridge/aggregate").status_code == 404
