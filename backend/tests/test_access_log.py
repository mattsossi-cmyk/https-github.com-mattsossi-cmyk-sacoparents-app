"""Report access log: views and PDF downloads are recorded with actor identity and shown to the assigned professional."""
import os

import pytest

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def accessed_case():
    pro, pa, pb, d, _detail = completed_case(API)
    rid = d["id"]
    assert pro.get(f"{API}/joint/reports/{rid}/activity").json()["access_log"] == []
    assert pa.get(f"{API}/joint/reports/{rid}/report").status_code == 200
    assert pro.get(f"{API}/joint/reports/{rid}/pdf").status_code == 200
    assert pb.get(f"{API}/joint/reports/{rid}/pdf").status_code == 200
    activity = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    return {"pro": pro, "pa": pa, "rid": rid, "activity": activity}


def test_counts(accessed_case) -> None:
    act = accessed_case["activity"]
    assert act["view_count"] == 1
    assert act["download_count"] == 2
    assert [e["kind"] for e in act["access_log"]] == ["download", "download", "view"]


@pytest.mark.parametrize("idx,role,action", [
    (0, "Parent 2", "Downloaded PDF"),
    (1, "Assigned professional", "Downloaded PDF"),
    (2, "Parent 1", "Viewed report on screen"),
])
def test_actor_and_action(accessed_case, idx, role, action) -> None:
    ev = accessed_case["activity"]["access_log"][idx]
    assert ev["by_role"] == role
    assert ev["action"] == action
    assert ev["at"]
    assert ev["by"]


def test_professional_name_recorded(accessed_case) -> None:
    ev = accessed_case["activity"]["access_log"][1]
    assert ev["by_name"] == accessed_case["pro"].name


def test_access_log_separate_from_other_events(accessed_case) -> None:
    kinds = {e.get("kind") for e in accessed_case["activity"]["access_events"]}
    assert not kinds & {"view", "download"}


def test_parents_cannot_read_activity(accessed_case) -> None:
    r = accessed_case["pa"].get(f"{API}/joint/reports/{accessed_case['rid']}/activity")
    assert r.status_code == 403
