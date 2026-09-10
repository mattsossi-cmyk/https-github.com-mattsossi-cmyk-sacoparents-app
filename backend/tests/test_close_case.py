"""Close case: CLOSED status, hidden from active table (archived), reopenable."""
import os

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_close_and_reopen_case() -> None:
    pro, pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    assert pa.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True}).status_code == 404
    r = pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Mediation concluded"})
    assert r.status_code == 200 and r.json()["case_status"] == "CLOSED"
    mine = next(x for x in pro.get(f"{API}/joint/reports").json() if x["id"] == rid)
    assert mine["case_status"] == "CLOSED" and mine["archived"] and mine["closed_at"]
    r = pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": False})
    assert r.status_code == 200 and r.json()["case_status"] == "READY_FOR_ALIGNMENT"
    mine = next(x for x in pro.get(f"{API}/joint/reports").json() if x["id"] == rid)
    assert not mine["archived"] and not mine["closed_at"]
