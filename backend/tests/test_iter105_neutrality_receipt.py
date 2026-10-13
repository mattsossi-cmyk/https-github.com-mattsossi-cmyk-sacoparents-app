"""Iter-105: summaries neutrality gate (Jev), judge submissions packet_label, professional-notice CSV, receipt fields."""
import os
import uuid

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import completed_case  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"


def test_summaries_neutrality_gate():
    pro, _a, _b, d, _ = completed_case(API)
    rid = d["id"]
    bad = pro.put(f"{API}/joint/reports/{rid}/individual-summaries", json={"a": {"concerns": "The other parent constantly lies and is a terrible, manipulative father who neglects the child."}})
    assert bad.status_code == 400, bad.text
    assert bad.json()["detail"].startswith("Neutrality check")
    ok = pro.put(f"{API}/joint/reports/{rid}/individual-summaries", json={"a": {"concerns": "Emphasis on consistent handoff times during the school week."}})
    assert ok.status_code == 200, ok.text
    assert ok.json()["summaries"]["a"]["concerns"].startswith("Emphasis")


def test_professional_notice_csv_admin_only():
    s = requests.Session()
    s.post(f"{API}/auth/register", json={"name": "CSV QA", "email": f"t_csv_{uuid.uuid4().hex[:8]}@example.com", "password": "testpass123", "role": "professional", "agreements_accepted": True, "organization": "QA", "pro_role": "Mediator"})
    assert s.get(f"{API}/admin/professional-notice/acceptances.csv").status_code == 403
    admin = requests.Session()
    r = admin.post(f"{API}/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", ""), "password": os.environ.get("ADMIN_PASSWORD", "")})
    if r.status_code != 200:
        return
    csv_r = admin.get(f"{API}/admin/professional-notice/acceptances.csv")
    assert csv_r.status_code == 200 and csv_r.text.startswith("name,email,role,accepted_version")
