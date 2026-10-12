"""Seed a completed non-court-referred joint report for approval.test.pro1@gmail.com for UI testing."""
import os, sys, uuid, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
sys.path.insert(0, os.path.dirname(__file__))
from casekit import new_user, fill, _approve

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"

# Login as pro1
pro = requests.Session()
r = pro.post(f"{API}/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"})
assert r.status_code == 200, r.text
_approve("approval.test.pro1@gmail.com")

ea = f"ui103_a_{uuid.uuid4().hex[:6]}@example.com"
eb = f"ui103_b_{uuid.uuid4().hex[:6]}@example.com"
r = pro.post(f"{API}/joint/reports/professional", json={
    "subject": "education", "custom_subject": "", "child_name": "UI_Kid",
    "parent_a_name": "UI A", "parent_a_email": ea,
    "parent_b_name": "UI B", "parent_b_email": eb,
})
assert r.status_code == 200, r.text
d = r.json(); rid = d["id"]
toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
pa = new_user(API, "parent", "UI A", email=ea, invite=toks["a"])
pb = new_user(API, "parent", "UI B", email=eb, invite=toks["b"])
for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
    rr = s.post(f"{API}/joint/invitations/accept", json={"code": tok})
    assert rr.json().get("ok"), rr.text
fill(API, pa, rid, "alpha")
fill(API, pb, rid, "beta")
print(f"RID={rid}")
