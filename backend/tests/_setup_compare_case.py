"""One-off setup: create a READY joint report with pro=approval.test.pro1 and parents Ann/Jordan.
Prints the created report id to stdout for the frontend test to consume."""
import os
import sys
import uuid
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/")
API = BASE + "/api"
PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PASS = "TestPass2026!"

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": PRO_EMAIL, "password": PRO_PASS})
assert r.status_code == 200, f"pro login failed: {r.status_code} {r.text}"

ann_email = f"t_ann_{uuid.uuid4().hex[:8]}@example.com"
jor_email = f"t_jor_{uuid.uuid4().hex[:8]}@example.com"

payload = {
    "subject": "education", "child_name": "Vida",
    "parent_a_name": "Ann", "parent_a_email": ann_email,
    "parent_b_name": "Jordan", "parent_b_email": jor_email,
}
r = s.post(f"{API}/joint/reports/professional", json=payload)
assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
d = r.json()
rid = d["id"]
toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}

# Register parents & accept
def reg(name, email, tok):
    ns = requests.Session()
    rr = ns.post(f"{API}/auth/register", json={
        "name": name, "email": email, "password": "testpass123", "role": "parent",
        "invite": tok, "agreements_accepted": False,
    })
    assert rr.status_code == 200, f"register {name} failed: {rr.status_code} {rr.text}"
    a = ns.post(f"{API}/joint/invitations/accept", json={"code": tok})
    assert a.json().get("ok"), f"accept failed: {a.text}"
    return ns

pa = reg("Ann", ann_email, toks["a"])
pb = reg("Jordan", jor_email, toks["b"])

# Distinct answers to yield mix of agree/partial/differ
ann_ans = {
    "needs_most": "Vida needs steady homework routines with predictable evening pickups.",
    "working_well": "Consistent homework hour at my home is going well.",
    "concerns": "I worry about inconsistent bedtimes affecting Vida's focus.",
    "improve": "I'd like a shared homework log we both update daily.",
    "options": "Option A: shared homework log. Option B: same start time.",
    "other_parent": "Jordan may value flexibility but I think Vida needs structure.",
}
jor_ans = {
    "needs_most": "Vida needs steady homework routines with predictable evening pickups.",
    "working_well": "I feel free-time creativity works well after school at my home.",
    "concerns": "I worry about too rigid schedules limiting Vida's play time.",
    "improve": "I'd like a shared homework log we both update daily.",
    "options": "Option A: shared homework log. Option C: flexible weekend catch-up.",
    "other_parent": "Ann may prefer structure; I think Vida needs balance.",
}
for sess, ans in ((pa, ann_ans), (pb, jor_ans)):
    rr = sess.put(f"{API}/joint/reports/{rid}/responses", json={"answers": ans})
    assert rr.status_code == 200, rr.text

# Verify ready
r = s.get(f"{API}/joint/reports/{rid}")
assert r.status_code == 200 and r.json()["status"] == "ready", r.text

print("REPORT_ID=" + rid)
print("ANN_EMAIL=" + ann_email)
print("JOR_EMAIL=" + jor_email)
