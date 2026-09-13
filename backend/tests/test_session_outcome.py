"""Post-session outcome: pro ticks chosen next steps, saved to case record + lifecycle log."""
import os

import pytest

from casekit import completed_case, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def ready() -> tuple:
    pro, pa, _pb, d, _detail = completed_case(API)
    return pro, pa, d["id"]


def test_pro_saves_outcome_and_it_persists(ready) -> None:
    pro, _pa, rid = ready
    body = {"chosen_steps": ["Continue Parent Discussion", " Consult Teacher / School Counselor "], "summary": "Try a shared homework log for two weeks."}
    r = pro.put(f"{API}/joint/reports/{rid}/session-outcome", json=body)
    assert r.status_code == 200, r.text
    out = r.json()["session_outcome"]
    assert out["chosen_steps"] == ["Continue Parent Discussion", "Consult Teacher / School Counselor"]
    detail = pro.get(f"{API}/joint/reports/{rid}").json()
    assert detail["session_outcome"]["summary"] == body["summary"]
    assert detail["session_outcome"]["recorded_at"]


def test_outcome_logged_in_lifecycle(ready) -> None:
    pro, _pa, rid = ready
    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert any("Session outcome recorded" in e["action"] for e in act["lifecycle"])


def test_parent_cannot_save_or_see_outcome(ready) -> None:
    _pro, pa, rid = ready
    assert pa.put(f"{API}/joint/reports/{rid}/session-outcome", json={"chosen_steps": ["x"]}).status_code == 403
    assert "session_outcome" not in pa.get(f"{API}/joint/reports/{rid}").json()


def test_outcome_requires_both_parents_complete() -> None:
    pro, _pa, _pb, d = new_case(API)
    assert pro.put(f"{API}/joint/reports/{d['id']}/session-outcome", json={"chosen_steps": ["x"]}).status_code == 400
