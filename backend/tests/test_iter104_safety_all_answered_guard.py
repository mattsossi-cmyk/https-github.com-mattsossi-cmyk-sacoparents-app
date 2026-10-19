"""Iter 104 — Server-side "all questions answered" guard on Safety
Assessment submission.

Locks the contract of `POST /api/safety-assessment`:
    * A submission with any missing / invalid answer in Section 1 or
      Section 2 returns 400 with a structured `detail` payload:

        { "message": "Please answer every question…",
          "missing": { "section_1": [...], "section_2": [...] } }

      This lets the frontend highlight the exact rows to answer.
    * A submission that answers every question in both sections
      returns 200 and inserts a real assessment doc.
    * Case-insensitive answer values are accepted ("Yes" / "YES" / "yes").
    * Unknown values (e.g. "maybe") are treated as missing.

These tests hit the live backend via HTTP with the parent1 fixture
account. Skipped gracefully when credentials aren't available.
"""
import pytest
pytest.skip("In-app safety screen turned off (2026-10); screening now happens on SACOparentsAlign.", allow_module_level=True)

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT_EMAIL = "parent1@test.com"
PARENT_PASSWORD = "TestPass123!"  # noqa: S105  test fixture


def _login() -> str | None:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": PARENT_EMAIL, "password": PARENT_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    return r.json().get("access_token") or r.json().get("token")


def _fetch_question_ids() -> tuple[list[str], list[str]] | None:
    """Pull the live question list from /questions so the test doesn't
    silently drift when the assessment shape changes."""
    r = requests.get(f"{API}/safety-assessment/questions", timeout=10)
    if r.status_code != 200:
        return None
    data = r.json() or {}
    s1 = [q["id"] for q in (data.get("section_1") or [])]
    s2 = [q["id"] for q in (data.get("section_2") or [])]
    return s1, s2


# ---------- Rejection paths ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_empty_submission_returns_400_with_all_ids_missing():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    ids = _fetch_question_ids()
    if not ids:
        pytest.skip("questions endpoint unavailable")
    s1_ids, s2_ids = ids

    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": {}, "section_2": {}},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 400
    detail = r.json().get("detail")
    assert isinstance(detail, dict), detail
    assert "message" in detail
    missing = detail.get("missing") or {}
    assert set(missing.get("section_1") or []) == set(s1_ids)
    assert set(missing.get("section_2") or []) == set(s2_ids)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_partial_submission_only_flags_the_unanswered_ids():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    ids = _fetch_question_ids()
    if not ids:
        pytest.skip("questions endpoint unavailable")
    s1_ids, s2_ids = ids

    # Answer everything EXCEPT the last item in each section.
    section_1 = {qid: "no" for qid in s1_ids[:-1]}
    section_2 = {qid: "yes" for qid in s2_ids[:-1]}
    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": section_1, "section_2": section_2},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 400
    missing = r.json()["detail"]["missing"]
    assert missing["section_1"] == [s1_ids[-1]]
    assert missing["section_2"] == [s2_ids[-1]]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_unknown_answer_values_are_treated_as_missing():
    """A scripted client sending 'maybe' / '' / 'idk' should not be
    able to slip past validation."""
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    ids = _fetch_question_ids()
    if not ids:
        pytest.skip("questions endpoint unavailable")
    s1_ids, s2_ids = ids

    section_1 = {qid: "no" for qid in s1_ids}
    section_2 = {qid: "yes" for qid in s2_ids}
    # Poison one value in each section.
    section_1[s1_ids[0]] = "maybe"
    section_2[s2_ids[0]] = ""

    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": section_1, "section_2": section_2},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 400
    missing = r.json()["detail"]["missing"]
    assert s1_ids[0] in missing["section_1"]
    assert s2_ids[0] in missing["section_2"]


# ---------- Happy path ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_fully_answered_submission_returns_200_and_result():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    ids = _fetch_question_ids()
    if not ids:
        pytest.skip("questions endpoint unavailable")
    s1_ids, s2_ids = ids

    section_1 = {qid: "no" for qid in s1_ids}
    section_2 = {qid: "yes" for qid in s2_ids}
    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": section_1, "section_2": section_2},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("assessment_id")
    assert body.get("result", {}).get("level")


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_mixed_case_answers_are_accepted():
    """The frontend emits lowercase but a partner integration or
    admin-facing API user could send Title/UPPER case. The guard is
    case-insensitive on purpose."""
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    ids = _fetch_question_ids()
    if not ids:
        pytest.skip("questions endpoint unavailable")
    s1_ids, s2_ids = ids

    section_1 = {}
    for i, qid in enumerate(s1_ids):
        section_1[qid] = ["Yes", "NO", "Unsure"][i % 3]
    section_2 = {qid: "YES" for qid in s2_ids}

    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": section_1, "section_2": section_2},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=20,
    )
    assert r.status_code == 200, r.text


import pytest as _pytest  # noqa: E402
pytestmark = _pytest.mark.skip(reason="In-app safety assessment routes are removed (404). Stored answers kept, hidden.")
