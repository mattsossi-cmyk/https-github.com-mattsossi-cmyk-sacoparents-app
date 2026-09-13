"""Iteration 38 explicit review-request checks (health build, session-outcome error codes,
cron auth, and end-to-end new-case → outcome → close → closing PDF)."""
import os
import uuid

import pytest
import requests

from casekit import new_case, fill

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]


def test_health_build_version() -> None:
    r = requests.get(f"{API}/health")
    assert r.status_code == 200, r.text
    assert r.json().get("build") .startswith("2026-"), r.json()


def test_session_outcome_bad_date_returns_400() -> None:
    pro, pa, pb, d = new_case(API)
    rid = d["id"]
    fill(API, pa, rid, "alpha")
    fill(API, pb, rid, "beta")
    # bad date format
    r = pro.put(f"{API}/joint/reports/{rid}/session-outcome",
                json={"chosen_steps": ["x"], "follow_up_date": "05/01/2026"})
    assert r.status_code == 400, r.text


def test_session_outcome_requires_auth() -> None:
    # anon session
    pro, pa, pb, d = new_case(API)
    rid = d["id"]
    fill(API, pa, rid, "alpha")
    fill(API, pb, rid, "beta")
    r = requests.put(f"{API}/joint/reports/{rid}/session-outcome",
                     json={"chosen_steps": ["x"]})
    assert r.status_code == 401, r.status_code


def test_session_outcome_parent_forbidden() -> None:
    pro, pa, pb, d = new_case(API)
    rid = d["id"]
    fill(API, pa, rid, "alpha")
    fill(API, pb, rid, "beta")
    r = pa.put(f"{API}/joint/reports/{rid}/session-outcome",
               json={"chosen_steps": ["x"]})
    assert r.status_code == 403, r.status_code


def test_cron_endpoint_unauthenticated() -> None:
    r = requests.post(f"{API}/cron/follow-up-reminder", json={"run_id": str(uuid.uuid4())})
    assert r.status_code == 401


def test_cron_endpoint_with_secret_returns_ok() -> None:
    r = requests.post(f"{API}/cron/follow-up-reminder",
                      json={"run_id": str(uuid.uuid4())},
                      headers={"Authorization": f"Bearer {CRON_SECRET}"})
    assert r.status_code == 200
    assert r.json().get("ok")


def test_full_new_case_close_and_closing_pdf_contains_outcome() -> None:
    pro, pa, pb, d = new_case(API)
    rid = d["id"]
    fill(API, pa, rid, "alpha")
    fill(API, pb, rid, "beta")
    step = "Continue Parent Discussion"
    r = pro.put(f"{API}/joint/reports/{rid}/session-outcome",
                json={"chosen_steps": [step], "summary": "Shared homework log."})
    assert r.status_code == 200, r.text
    r = pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Done"})
    assert r.status_code == 200, r.text
    pdf = pro.get(f"{API}/joint/reports/{rid}/closing-summary.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    import pymupdf
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "Session outcome" in text
    assert step in text
