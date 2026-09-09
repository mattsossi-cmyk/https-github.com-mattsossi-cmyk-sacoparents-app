"""Report access log: views and PDF downloads are recorded with actor identity and shown to the assigned professional."""
import os

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_view_and_download_are_logged_with_actor() -> None:
    pro, pa, pb, d, _detail = completed_case(API)
    rid = d["id"]
    assert pro.get(f"{API}/joint/reports/{rid}/activity").json()["access_log"] == []

    assert pa.get(f"{API}/joint/reports/{rid}/report").status_code == 200
    assert pro.get(f"{API}/joint/reports/{rid}/pdf").status_code == 200
    assert pb.get(f"{API}/joint/reports/{rid}/pdf").status_code == 200

    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert act["view_count"] == 1 and act["download_count"] == 2
    log = act["access_log"]
    assert [e["kind"] for e in log] == ["download", "download", "view"]
    assert log[0]["by_role"] == "Parent 2" and log[0]["action"] == "Downloaded PDF"
    assert log[1]["by_role"] == "Assigned professional" and log[1]["by_name"] == pro.name
    assert log[2]["by_role"] == "Parent 1" and log[2]["action"] == "Viewed report on screen"
    assert all(e["at"] and e["by"] for e in log)
    assert all(e.get("kind") not in ("view", "download") for e in act["access_events"])


def test_parents_cannot_read_activity() -> None:
    pro, pa, pb, d, _detail = completed_case(API)
    assert pa.get(f"{API}/joint/reports/{d['id']}/activity").status_code == 403
