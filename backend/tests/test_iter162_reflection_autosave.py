"""Iteration 162 — Reflection autosave regression.

Verifies the `/mediation/reflection` PUT endpoint continues to accept
incremental partial saves (which is what the new autosave client fires
every 1.5s while the parent types) — no all-or-nothing validation
regression that would silently drop a lone `child_lens` save if the
other three prompts are empty.
"""
from __future__ import annotations

import sys
import uuid

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def _register(prefix: str):
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"User {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_autosave_accepts_single_prompt_partial_save():
    """A parent types in the first prompt only — an autosave fires
    with `{child_lens: "..."}` and NO other keys. The endpoint must
    accept the partial and NOT wipe the (empty) other prompts."""
    _email, tok = _register("autosave1")
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "kid says handoffs feel rushed"},
        headers=_headers(tok),
        timeout=30,
    )
    assert r.status_code == 200

    got = requests.get(
        f"{BASE_URL}/api/mediation/prep",
        headers=_headers(tok), timeout=30,
    ).json().get("reflection") or {}
    assert got.get("child_lens") == "kid says handoffs feel rushed"


def test_autosave_progressive_writes_accumulate():
    """Simulate the client typing prompts one at a time: each PUT
    should replace the reflection dict with the latest snapshot,
    preserving everything the parent typed so far."""
    _email, tok = _register("autosave2")
    # Autosave 1 — after typing in child_lens
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "one"},
        headers=_headers(tok), timeout=30,
    )
    # Autosave 2 — after typing in own_part (client sends full snapshot)
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "one", "own_part": "two"},
        headers=_headers(tok), timeout=30,
    )
    # Autosave 3 — after typing best_outcome
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "one", "own_part": "two", "best_outcome": "three"},
        headers=_headers(tok), timeout=30,
    )
    got = requests.get(
        f"{BASE_URL}/api/mediation/prep",
        headers=_headers(tok), timeout=30,
    ).json().get("reflection") or {}
    assert got["child_lens"] == "one"
    assert got["own_part"] == "two"
    assert got["best_outcome"] == "three"


def test_autosave_replaces_dict_wholesale():
    """A follow-up save with an EMPTY prompt overwrites the old
    value — matches how the frontend sends the full entries dict on
    every debounce. Ensures a parent editing DOWN (deleting text)
    also autosaves."""
    _email, tok = _register("autosave3")
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "wanted to delete this"},
        headers=_headers(tok), timeout=30,
    )
    # Parent clears the textarea.
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": ""},
        headers=_headers(tok), timeout=30,
    )
    got = requests.get(
        f"{BASE_URL}/api/mediation/prep",
        headers=_headers(tok), timeout=30,
    ).json().get("reflection") or {}
    assert got.get("child_lens") == ""
