"""Iter 105 — Trauma-Informed Safety and Functioning Lens (TISFL).

Locks the Phase 1 contract of the trauma-lens layer:

Backend:
    * Every scored assessment now carries a `result.lens` block with:
        - `lens_name` = "Trauma-Informed Safety and Functioning Lens"
        - `interpretation_rules` — the two lens rules
        - `findings.family_violence_pattern`   (confidential=True)
        - `findings.trauma_impact`             (confidential=True)
        - `findings.parenting_plan_implications` (confidential=False)
    * The three-finding language is level-appropriate (level 1-4 map).
    * `POST /api/safety-assessment` returns the lens on the submit body.
    * `GET  /api/safety-assessment/{id}/court-report` produces a real
      multi-page PDF that includes the interpretation rules on page 1,
      one page per finding, and a signature block. Excludes raw
      section-1 behavioural answers.
    * The Compare redaction helper strips findings 1 & 2, leaving only
      finding 3 for the co-parent's view.
"""
from __future__ import annotations

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


def _submit(headers: dict, s1_overrides: dict | None = None) -> dict:
    s1 = {f"s1_q{i}": "no" for i in range(1, 29)}
    if s1_overrides:
        s1.update(s1_overrides)
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"
    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": s1, "section_2": s2},
        headers=headers, timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Pure-function coverage (no HTTP) ----------

def test_trauma_lens_pure_function_shape():
    from trauma_lens import build_findings, INTERPRETATION_RULES, LENS_NAME
    for level in (1, 2, 3, 4):
        block = build_findings({"level": level})
        assert block["lens_name"] == LENS_NAME
        assert block["interpretation_rules"] == INTERPRETATION_RULES
        assert set(block["findings"].keys()) == {
            "family_violence_pattern",
            "trauma_impact",
            "parenting_plan_implications",
        }
        # Confidentiality flags — pattern & trauma stay private, plan is shareable.
        assert block["findings"]["family_violence_pattern"]["confidential"] is True
        assert block["findings"]["trauma_impact"]["confidential"] is True
        assert block["findings"]["parenting_plan_implications"]["confidential"] is False
        # Every finding has a headline + summary.
        for f in block["findings"].values():
            assert f.get("headline")
            assert f.get("summary")
            assert f.get("core_question")
    # Level 2 must use coercive-control language, level 4 must not.
    l2 = build_findings({"level": 2})["findings"]["family_violence_pattern"]["headline"].lower()
    l4 = build_findings({"level": 4})["findings"]["family_violence_pattern"]["headline"].lower()
    assert "coercive" in l2
    assert "coercive" not in l4


def test_redact_for_compare_strips_pattern_and_trauma():
    from trauma_lens import build_findings, redact_for_compare
    lens = build_findings({"level": 1})
    redacted = redact_for_compare(lens)
    assert redacted["redacted"] is True
    assert set(redacted["findings"].keys()) == {"parenting_plan_implications"}
    # And the interpretation rules still travel with it.
    assert redacted["interpretation_rules"] == lens["interpretation_rules"]


# ---------- HTTP contract ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_submit_attaches_lens_block_to_every_scored_result():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    body = _submit({"Authorization": f"Bearer {tok}"})
    lens = body["result"].get("lens")
    assert lens, "lens block missing on result"
    assert lens["lens_short"] == "TISFL"
    assert len(lens["interpretation_rules"]) == 2
    assert "family_violence_pattern" in lens["findings"]
    assert "trauma_impact" in lens["findings"]
    assert "parenting_plan_implications" in lens["findings"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_court_report_endpoint_returns_multi_page_pdf():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    r = requests.get(
        f"{API}/safety-assessment/{aid}/court-report",
        headers=headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    # Must be a substantive multi-page document (>10KB), not a stub.
    assert len(r.content) > 10_000
    # PDF magic bytes.
    assert r.content[:4] == b"%PDF"
    # Multi-page — a court report has cover + 3 findings + safeguards + signatures.
    assert r.content.count(b"/Type /Page") >= 4 or r.content.count(b"/Type/Page") >= 4


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_court_report_requires_auth():
    r = requests.get(
        f"{API}/safety-assessment/anything/court-report",
        timeout=10,
    )
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_court_report_404_for_unknown_assessment():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.get(
        f"{API}/safety-assessment/sa_nonexistent/court-report",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_level_1_lens_language_uses_high_danger_framing():
    """When s1_q1 (a high-concern hit) is answered yes, the pattern
    finding must use serious-safety-concern framing — the lens must
    not soften real danger."""
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    body = _submit({"Authorization": f"Bearer {tok}"}, s1_overrides={"s1_q1": "yes"})
    assert body["result"]["level"] == 1
    pattern = body["result"]["lens"]["findings"]["family_violence_pattern"]
    text = f"{pattern['headline']} {pattern['summary']}".lower()
    assert "serious" in text or "high" in text or "danger" in text
