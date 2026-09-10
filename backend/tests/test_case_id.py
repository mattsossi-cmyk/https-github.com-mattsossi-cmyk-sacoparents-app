"""Case ID backbone: SA-YY-PREFIX-XXXXXX, distinct parent tokens, derived case_status lifecycle."""
import os
import re

from casekit import new_case, completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CASE_ID_RE = re.compile(r"^SA-\d{2}-[A-Z]{3}-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$")


def test_case_id_format_and_distinct_parent_tokens() -> None:
    pro, _pa, _pb, d = new_case(API)
    assert CASE_ID_RE.match(d["case_code"]), d["case_code"]
    invs = d["invitations"]
    assert {i["role"] for i in invs} == {"a", "b"}
    assert invs[0]["link"] != invs[1]["link"]
    assert invs[0]["link"].split("/join/")[1] != invs[1]["link"].split("/join/")[1]
    assert d["case_status"] == "INVITED"


def test_case_status_progresses_to_report_generated() -> None:
    pro, pa, pb, d, _detail = completed_case(API)
    rid = d["id"]
    mine = next(x for x in pro.get(f"{API}/joint/reports").json() if x["id"] == rid)
    assert mine["case_status"] == "READY_FOR_ALIGNMENT"
    assert pro.get(f"{API}/joint/reports/{rid}/report").status_code == 200
    mine = next(x for x in pro.get(f"{API}/joint/reports").json() if x["id"] == rid)
    assert mine["case_status"] == "REPORT_GENERATED"
