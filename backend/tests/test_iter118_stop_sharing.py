"""Stop sharing (owner 2026-10-20): parents can remove professionals they added; case-assigned professionals cannot be removed."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case, new_user  # noqa: E402

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api" if os.environ.get("REACT_APP_BACKEND_URL") else "http://localhost:8001/api"


def _api():
    from dotenv import dotenv_values
    url = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
    return url + "/api"


def test_share_list_and_stop():
    api = _api()
    pro, pa, pb, d, _ = completed_case(api)
    rid = d["id"]
    extra = new_user(api, "professional", "Extra Pro")

    shares = pa.get(f"{api}/joint/reports/{rid}/shares").json()
    assert len(shares) == 1 and shares[0]["assigned"] and not shares[0]["removable"]
    assigned_id = shares[0]["id"]

    assert pa.post(f"{api}/joint/reports/{rid}/share", json={"email": extra.email}).status_code == 200
    shares = pa.get(f"{api}/joint/reports/{rid}/shares").json()
    added = [s for s in shares if not s["assigned"]]
    assert len(added) == 1 and added[0]["removable"] and added[0]["name"] == "Extra Pro"
    assert extra.get(f"{api}/joint/reports/{rid}").status_code == 200

    # case-assigned professional cannot be removed by a parent
    assert pa.delete(f"{api}/joint/reports/{rid}/share/{assigned_id}").status_code == 403
    # the professional cannot use the parent endpoints
    assert pro.get(f"{api}/joint/reports/{rid}/shares").status_code == 403
    assert pro.delete(f"{api}/joint/reports/{rid}/share/{added[0]['id']}").status_code == 403

    # co-parent B may also stop the share (both are participants of the one report)
    assert pb.delete(f"{api}/joint/reports/{rid}/share/{added[0]['id']}").status_code == 200
    assert extra.get(f"{api}/joint/reports/{rid}").status_code in (403, 404)
    assert pa.delete(f"{api}/joint/reports/{rid}/share/{added[0]['id']}").status_code == 404
    assert all(s["assigned"] for s in pa.get(f"{api}/joint/reports/{rid}/shares").json())
