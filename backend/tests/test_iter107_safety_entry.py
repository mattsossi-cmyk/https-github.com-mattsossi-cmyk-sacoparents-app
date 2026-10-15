"""Iter-107: Start-with-Safety entry — banner status identical for all parents, skip records status only, crisis resources per version
(Bexar County FJC with hours in every version), no CDN in new assets, banner text absent from emails."""
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import completed_case  # noqa: E402
from safety_screening import SAFETY_BANNER_TEXT, crisis_resources_for  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
FE = Path("/app/frontend/src")


def test_banner_identical_shape_for_all_parents_and_hidden_after_decline_or_completion():
    pro, pa, pb, d, _ = completed_case(API)
    rid = d["id"]
    # completed_case satisfies the step for both parents (declined) so they could answer; status shape is identical for both.
    ea, eb = pa.get(f"{API}/me/safety-entry").json(), pb.get(f"{API}/me/safety-entry").json()
    assert set(ea) == set(eb) == {"applies", "has_case", "status", "report_id", "text", "notice", "notice_version", "needs_notice"}
    assert ea["status"] == eb["status"] == "declined" and ea["text"] == SAFETY_BANNER_TEXT and ea["report_id"] == rid
    assert not any(k in ea for k in ("tier", "flag", "version"))
    assert pro.get(f"{API}/me/safety-entry").json() == {"applies": False}
    assert pa.post(f"{API}/joint/reports/{rid}/safety-screening/decline").json()["entry_status"] == "declined"
    assert pa.get(f"{API}/me/safety-entry").json()["status"] == "declined"
    assert pro.post(f"{API}/joint/reports/{rid}/safety-screening/decline").status_code == 403
    st = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]["a"]
    assert st["entry_status"] == "declined" and st["received"] is False and st["entry_label"].startswith("Declined · 20")
    # Parent B completes with every question skipped → still "completed": no forced answers.
    assert pb.put(f"{API}/joint/reports/{rid}/safety-screening/choose", json={"version": "A"}).status_code == 200
    r = pb.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {}, "safe_contact": None})
    assert r.status_code == 200, r.text
    assert pb.get(f"{API}/me/safety-entry").json()["status"] == "completed"
    assert pb.post(f"{API}/joint/reports/{rid}/safety-screening/decline").json()["entry_status"] == "completed"


def test_crisis_resources_per_version_include_bexar_with_hours():
    for v in ("A", "B", "C"):
        d = crisis_resources_for(v)
        names = [i["name"] for i in d["items"]]
        assert names[0] == "Immediate danger" and d["items"][0]["contact"] == "Call 911"
        assert "National Domestic Violence Hotline" in names and "San Antonio Family Violence Prevention Services 24-hour line" in names
        assert ("VictimConnect" in names) == (v == "B")
        assert ("The Network/La Red" in names) == (v == "C") and ("The Trevor Project (for young people under 25)" in names) == (v == "C")
        bexar = d["items"][-1]
        assert bexar["name"] == "Bexar County Family Justice Center (San Antonio)" and "210-631-0100" in bexar["contact"] and "126 E. Nueva, 2nd Floor" in bexar["contact"]
        assert bexar["hours"].startswith("Open Monday to Friday, 8:00 AM to 5:00 PM; closed on county holidays") and bexar["note"] == "Advocacy and legal help."
        idx = {n: i for i, n in enumerate(names)}
        assert all(idx[bexar["name"]] > idx[n] for n in names if n != bexar["name"])


def test_crisis_endpoint_requires_login_and_serves_versions():
    pro, pa, _b, _d, _ = completed_case(API)
    assert requests.get(f"{API}/safety/crisis-resources?version=B").status_code in (401, 403)
    b = pa.get(f"{API}/safety/crisis-resources", params={"version": "B"}).json()
    assert any(i["name"] == "VictimConnect" for i in b["items"]) and b["items"][-1]["name"].startswith("Bexar County")
    assert pa.get(f"{API}/safety/crisis-resources", params={"version": "X"}).json()["version"] is None


def test_no_cdn_in_new_assets_and_banner_absent_from_emails():
    for f in ("components/SafetyEntryBanner.jsx", "components/CrisisResources.jsx", "pages/StartWithSafety.jsx", "content/safetyEntry.js"):
        src = (FE / f).read_text(encoding="utf-8")
        assert not re.search(r"https?://", src), f
    index_html = Path("/app/frontend/public/index.html").read_text(encoding="utf-8")
    assert "fonts.googleapis" not in index_html and "fonts.gstatic" not in index_html
    assert "@fontsource/plus-jakarta-sans" in (FE / "index.js").read_text(encoding="utf-8")
    for f in ("joint_helpers.py", "email_utils.py", "server.py", "core.py", "cron_jobs.py"):
        src = Path("/app/backend", f).read_text(encoding="utf-8")
        assert "Start with Safety. A private check-in" not in src and "Crisis Resources" not in src, f
    # safety_screening.py: the only email bodies are the reminder/alert templates — neither carries banner or popup text.
    ss = Path("/app/backend/safety_screening.py").read_text(encoding="utf-8")
    emails = [m for m in re.findall(r"send_email[^\n]*\n(?:[^\n]*\n){0,12}", ss)]
    assert emails and all("Start with Safety" not in e and "Crisis Resources" not in e for e in emails)
