import json, os, re, sys, time
import requests

API = None
for line in open("/app/frontend/.env"):
    if line.startswith("REACT_APP_BACKEND_URL="):
        API = line.strip().split("=", 1)[1]
SECRET = None
for line in open("/app/backend/.env"):
    if line.startswith("INTEGRATION_SHARED_SECRET="):
        SECRET = line.strip().split("=", 1)[1].strip("\"'")

TS = str(int(time.time()))
PA, PB, PC, PRO = f"caseA_{TS}@testmail.com", f"caseB_{TS}@testmail.com", f"caseC_{TS}@testmail.com", f"casepro_{TS}@testmail.com"

def reg(email, name, role):
    s = requests.Session()
    r = s.post(f"{API}/api/auth/register", json={"name": name, "email": email, "password": "TestPass123!", "role": role})
    assert r.status_code == 200, r.text
    return s

pro, sa, sb, sc = reg(PRO, "Pro Pat", "professional"), reg(PA, "Parent Ann", "parent"), reg(PB, "Parent Bob", "parent"), reg(PC, "Parent Cy", "parent")

print("=== 1. Pro creates case with case_reference ===")
r = pro.post(f"{API}/api/joint/reports/professional", json={
    "subject": "education", "child_name": "Riley",
    "parent_a_name": "Ann", "parent_a_email": PA,
    "parent_b_name": "Bob", "parent_b_email": PB,
    "case_reference": "FILE-2026-114",
})
d = r.json()
cc = d.get("case_code", "")
assert re.fullmatch(r"SA-EDU-\d{6}", cc), f"bad case code: {cc}"
assert d.get("case_reference") == "FILE-2026-114", "case_reference missing for creator"
invs = d["invitations"]
assert len(invs) == 2 and invs[0]["code"] == invs[1]["code"] == cc, "invitations must share the case code"
assert d["status"] == "pending_invite"
RID = d["id"]
toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in invs}
print(f"PASS: case_code {cc} | shared by both invitations | case_reference stored")

print("=== 2. Integration case-invite lookup ===")
r = requests.get(f"{API}/api/integrations/case-invite/{toks['a']}")
assert r.status_code == 401, r.status_code
print("no key -> 401 PASS")
r = requests.get(f"{API}/api/integrations/case-invite/{toks['a']}", headers={"X-Integration-Key": SECRET})
d = r.json()
print("DEBUG lookup:", r.status_code, json.dumps(d)[:300])
assert r.status_code == 200 and d["case_id"] == cc and d["parent_role"] == "a" and d["parent_email"] == PA.lower()
print(f"PASS: case-invite -> {d['case_id']} | {d['assessment_type']} | parent {d['parent_role']} | requested_by {d['requested_by']}")

print("=== 3. Shared case code + email disambiguation ===")
r = sb.post(f"{API}/api/joint/invitations/accept", json={"code": cc})
assert r.json().get("ok"), r.text
print("PASS: Parent B accepted via shared case code")
r = sc.post(f"{API}/api/joint/invitations/accept", json={"code": cc})
assert r.status_code in (403, 404), r.text
print(f"PASS: wrong-email user rejected -> {r.status_code} {r.json()['detail']}")
r = sa.post(f"{API}/api/joint/invitations/accept", json={"code": toks["a"]})
assert r.json().get("ok"), r.text
print("PASS: Parent A accepted via token link")

print("=== 4. App pushes status updates (case-update) ===")
r = requests.post(f"{API}/api/integrations/case-update", json={"token": toks["a"], "status": "completed"}, headers={"X-Integration-Key": "wrong"})
assert r.status_code == 401, r.status_code
print("wrong key -> 401 PASS")
r = requests.post(f"{API}/api/integrations/case-update", json={"token": toks["b"], "status": "started"}, headers={"X-Integration-Key": SECRET})
assert r.json()["case_status"] == "in_progress", r.text
print("PASS: started -> in_progress")
ans_a = {"needs_most": "Riley needs homework consistency", "working_well": "Both homes communicate with the teacher", "concerns": "Homework timing differs", "improve": "Shared homework window", "options": "Teacher conference", "other_parent": "Worried about grades"}
r = requests.post(f"{API}/api/integrations/case-update", json={"token": toks["a"], "status": "completed", "assessment_id": "app-asm-001", "responses": ans_a}, headers={"X-Integration-Key": SECRET})
assert r.json()["case_status"] == "in_progress", r.text
print("PASS: A completed -> in_progress (waiting on B)")
ans_b = {"needs_most": "Riley needs homework routine and consistency", "working_well": "Teacher communication reaches both homes", "concerns": "Evenings are rushed", "improve": "Predictable homework time", "options": "Mediator session", "other_parent": "Worried about schedule rigidity"}
r = requests.post(f"{API}/api/integrations/case-update", json={"token": toks["b"], "status": "completed", "assessment_id": "app-asm-002", "responses": ans_b}, headers={"X-Integration-Key": SECRET})
assert r.json()["case_status"] == "ready", r.text
print("PASS: B completed -> ready")

print("=== 5. Pro dashboard data ===")
r = pro.get(f"{API}/api/joint/reports")
rep = [x for x in r.json() if x["id"] == RID][0]
assert rep["status"] == "ready"
assert rep.get("case_code", "").startswith("SA-EDU-")
assert rep.get("case_reference") == "FILE-2026-114"
assert rep["participants"]["a"]["completed"] and rep["participants"]["b"]["completed"]
assert rep["participants"]["a"]["imported"] and rep["participants"]["b"]["imported"]
assert not rep.get("pending_invitations"), "invitations should no longer be pending"
print("PASS: ready, imported both sides, case code + private ref visible to pro, no pending invitations")

print("=== 6. Privacy: parent must NOT see case_reference ===")
r = sb.get(f"{API}/api/joint/reports/{RID}")
d = r.json()
assert "case_reference" not in d, "case_reference leaked to parent!"
assert d.get("case_code", "").startswith("SA-")
print("PASS: case_reference hidden from parents; case code visible")

print("=== 7. Report + PDF generate from imported material ===")
r = pro.get(f"{API}/api/joint/reports/{RID}/report")
d = r.json()
assert d["report_title"] == "Joint Parenting Alignment Report"
print(f"PASS: report generated | {len(d['alignment_statements'])} alignment stmts, {len(d['differences'])} differences, imported={d['imported']}")
r = pro.get(f"{API}/api/joint/reports/{RID}/pdf")
assert r.status_code == 200 and r.content[:5] == b"%PDF-", r.status_code
print(f"PASS: valid PDF ({len(r.content)} bytes)")

print("=== 8. Legacy parent-created report also gets a case code ===")
r = sa.post(f"{API}/api/joint/reports", json={"subject": "communication", "child_name": "Riley", "co_parent_name": "Cy", "co_parent_email": PC})
d = r.json()
assert re.fullmatch(r"SA-COM-\d{6}", d.get("case_code", "")), d.get("case_code")
assert d["invitation"]["code"] == d["case_code"]
print(f"PASS: parent flow case code {d['case_code']}")

print("ALL CHECKS PASSED")
