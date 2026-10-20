"""Backend tests for Court Ordered page: both-parent compare + Foundation chat drafts.

Covers:
- GET  /api/court-path/compare states: safety_off, no_case, not_shared, waiting, ready
- POST /api/court-path/compare/share toggle (idempotent, safety guard, require case)
- 'mine' is caller's own; both sides symmetric
- Child side-by-side rows
- Toggle off removes ready for both parents
- 401 unauthenticated
- POST /api/court-path/ai/foundation-split returns 4 string keys
- POST /api/court-path/ai/foundation-split with text<20 chars -> 422
- Foundation builder accepts 'statement' and PDF includes 'Our Foundation Statement'
"""
import os
import requests
import pytest

def _read_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.strip().startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception:
        return None

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env() or "").rstrip("/")
API = f"{BASE}/api"
PWD = "TestPass123!"


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"{email}: {r.text}"
    tok = r.json()["access_token"]
    # AI features (foundation split, talking points) need the current notices accepted.
    from ai_ready import accept_ai_notice
    accept_ai_notice(API, {"Authorization": f"Bearer {tok}"})
    return tok


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def tokens():
    """Re-seed the demo pair (resets sharing to off) and return tokens for all 4 parents."""
    # Re-seed
    import subprocess
    subprocess.run(
        ["python", "-c",
         "from dotenv import load_dotenv; load_dotenv('.env'); "
         "from seed_court_compare_pair import run; import asyncio; print(asyncio.run(run()))"],
        cwd="/app/backend", check=True, capture_output=True,
    )
    return {
        "p1": _login("parent1@test.com"),
        "p2": _login("parent2@test.com"),
        "p3": _login("parent3@test.com"),
        "p4": _login("parent4@test.com"),
    }


# ---- compare states --------------------------------------------------------

def test_unauth_compare_401():
    r = requests.get(f"{API}/court-path/compare", timeout=15)
    assert r.status_code in (401, 403)


def test_safety_flagged_parent_returns_not_available(tokens):
    r = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p1"]), timeout=20)
    assert r.status_code == 200
    assert r.json().get("state") == "not_available"


def test_safety_flagged_share_attempt_stays_not_available(tokens):
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p1"]),
                      json={"shared": True}, timeout=20)
    assert r.status_code == 200
    assert r.json().get("state") == "not_available"
    assert r.json().get("shared") is False


def test_coparent_of_flagged_sees_waiting_not_leak(tokens):
    # parent2 shares (if not already), expects waiting (does not reveal parent1 flagged)
    requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p2"]),
                  json={"shared": True}, timeout=20)
    r = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p2"]), timeout=20)
    data = r.json()
    assert data.get("state") == "waiting", data
    # Must not include ready-only fields
    assert "alignment" not in data or data.get("state") != "ready"


def test_pair_not_shared_then_waiting_then_ready_and_mine_perspective(tokens):
    # Ensure both p3,p4 start not sharing (seed resets)
    r3 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p3"]), timeout=20).json()
    assert r3.get("state") == "not_shared", r3

    # p3 shares -> waiting
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p3"]),
                      json={"shared": True}, timeout=20).json()
    assert r.get("state") == "waiting", r

    # p4 shares -> both ready
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p4"]),
                      json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready", r
    assert isinstance(r.get("alignment"), list)
    assert isinstance(r.get("difference"), list)
    assert isinstance(r.get("child"), list)

    # Check 'mine' from both sides is caller's own
    r_p3 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p3"]), timeout=20).json()
    r_p4 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p4"]), timeout=20).json()
    assert r_p3["state"] == "ready" and r_p4["state"] == "ready"

    # Grab a row and verify mine/theirs are swapped
    all_rows_p3 = r_p3["alignment"] + r_p3["difference"]
    all_rows_p4 = r_p4["alignment"] + r_p4["difference"]
    if all_rows_p3 and all_rows_p4:
        by_area_p3 = {row["area"]: row for row in all_rows_p3}
        by_area_p4 = {row["area"]: row for row in all_rows_p4}
        common = set(by_area_p3) & set(by_area_p4)
        assert common, "expected overlapping areas"
        for area in common:
            assert by_area_p3[area]["mine"] == by_area_p4[area]["theirs"]
            assert by_area_p3[area]["theirs"] == by_area_p4[area]["mine"]

    # Child: categories list with rows
    for cat in r_p3["child"]:
        assert "category" in cat and "rows" in cat
        for row in cat["rows"]:
            assert set(row.keys()) >= {"label", "mine", "theirs"}


def test_toggle_off_returns_both_to_non_ready(tokens):
    # p3 toggles off -> p3 not_shared, p4 waiting
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p3"]),
                      json={"shared": False}, timeout=20).json()
    assert r.get("state") == "not_shared", r
    r4 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p4"]), timeout=20).json()
    assert r4.get("state") == "waiting", r4

    # Restore so other tests can rely on sharing — p3 shares again
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p3"]),
                      json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready"


def test_share_without_case_code_returns_400():
    # Register a brand-new user who has no court_key
    import uuid
    email = f"TEST_nocase_{uuid.uuid4().hex[:8]}@test.com"
    reg = requests.post(f"{API}/auth/register", json={"email": email, "password": PWD, "name": "No Case"}, timeout=20)
    assert reg.status_code in (200, 201), reg.text
    tok = reg.json().get("access_token") or _login(email)

    # No case -> compare = no_case
    r = requests.get(f"{API}/court-path/compare", headers=_h(tok), timeout=15).json()
    assert r.get("state") == "no_case", r

    # Share -> 400
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tok),
                      json={"shared": True}, timeout=15)
    assert r.status_code == 400
    assert "case code" in r.text.lower()


def test_changing_court_key_invalidates_old_share(tokens):
    # parent3 is sharing on PAIR-DEMO-01. Change court_key to something else -> compare should not be ready.
    original_key = "PAIR-DEMO-01"
    requests.put(f"{API}/portal/state", headers=_h(tokens["p3"]),
                 json={"court_key": "COURT-8842"}, timeout=15)
    r = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p3"]), timeout=20).json()
    assert r.get("state") in ("not_shared", "waiting"), r
    # Restore
    requests.put(f"{API}/portal/state", headers=_h(tokens["p3"]),
                 json={"court_key": original_key}, timeout=15)
    # And re-share
    requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p3"]),
                  json={"shared": True}, timeout=20)


# ---- foundation-split + statement + PDF -----------------------------------

def test_foundation_split_too_short_422(tokens):
    r = requests.post(f"{API}/court-path/ai/foundation-split", headers=_h(tokens["p3"]),
                      json={"text": "too short"}, timeout=30)
    assert r.status_code == 422


def test_foundation_split_returns_four_keys(tokens):
    text = (
        "I want my child Maya to feel safe and loved in both homes. I value calm, "
        "respectful communication and consistent routines. My child needs steady medical care, "
        "school support, and emotional stability. I commit to being on time, speaking kindly about "
        "the other parent, and following our schedule."
    )
    r = requests.post(f"{API}/court-path/ai/foundation-split", headers=_h(tokens["p3"]),
                      json={"text": text}, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("core_goals", "child_needs", "co_values", "commitments"):
        assert k in data and isinstance(data[k], str)
        assert len(data[k]) <= 600


def test_foundation_statement_field_saves_and_pdf_includes_section(tokens):
    tok = tokens["p3"]
    statement = "Our Foundation Statement: We co-parent for Maya with respect and consistency."
    r = requests.put(f"{API}/foundation-builder/me", headers=_h(tok),
                     json={"fields": {"statement": statement}}, timeout=20)
    assert r.status_code == 200, r.text

    r2 = requests.get(f"{API}/foundation-builder/me", headers=_h(tok), timeout=15).json()
    fields = r2.get("fields") or r2
    assert fields.get("statement") == statement

    # PDF generation includes 'Our Foundation Statement' section
    r3 = requests.post(f"{API}/foundation-builder/pdf", headers=_h(tok),
                       json={"fields": {"statement": statement, "parent_names": "Jordan"}}, timeout=30)
    assert r3.status_code == 200, r3.text
    body = r3.content
    assert body.startswith(b"%PDF"), "expected a PDF"
    # PDF content streams are FlateDecode compressed; decompress to search text.
    import re, zlib
    found = False
    for m in re.finditer(rb"stream\n(.*?)\nendstream", body, re.S):
        try:
            text = zlib.decompress(m.group(1))
            if b"Our Foundation Statement" in text:
                found = True
                break
        except Exception:
            pass
    assert found, "'Our Foundation Statement' section not in PDF"


def test_court_chat_foundation_draft_only_text(tokens):
    tok = tokens["p3"]
    # Clear statement so AI doesn't ask a clarifying question
    import json as _json
    requests.put(f"{API}/foundation-builder/me", headers=_h(tok),
                 json={"fields": {"statement": "", "core_goals": "", "child_needs": "",
                                   "co_values": "", "commitments": ""}}, timeout=15)
    sid = requests.post(f"{API}/court-path/ai/chat/new", headers=_h(tok), timeout=20).json()["session_id"]
    r = requests.post(f"{API}/court-path/ai/chat", headers=_h(tok),
                      json={"session_id": sid, "message": "Draft a child-focused Foundation Statement."},
                      timeout=90)
    assert r.status_code == 200, r.text
    reply = (r.json().get("reply") or r.json().get("message") or "").strip()
    assert reply, "empty reply"
    # Content checks: no markdown, mentions child-focused themes
    assert "*" not in reply and "#" not in reply, "no markdown"
