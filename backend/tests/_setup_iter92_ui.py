"""Setup: creates two cases for the UI test suite.
Case 1: parent A has CHOSEN version A but not submitted (used for Quick Exit + extra-question items).
Case 2: parent A submitted (x_2=Sometimes) so professional can view responses + decide pathway; pro also CONFIRMS protected_review on A, so the Legal Lens report has a safety_pathway block.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_iter88_safety_e2e import BASE, MONGO, _accept_invite, _login, _register  # noqa: E402

PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PASSWORD = "TestPass2026!"
PARENT_PASSWORD = "TestPass2026!"
TS = int(time.time())


def _mk_case(pro, a_email, b_email, tag):
    body = {
        "child_name": f"TEST UI {tag} {TS}",
        "subject": "communication",
        "parent_a_name": f"QA UI {tag} A", "parent_a_email": a_email, "parent_a_gender": "woman",
        "parent_b_name": f"QA UI {tag} B", "parent_b_email": b_email, "parent_b_gender": "man",
    }
    r = pro.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    tok = {i["role"]: (i.get("token") or i.get("code")) for i in MONGO.invitations.find({"report_id": rid})}
    return rid, tok


pro = _login(PRO_EMAIL, PRO_PASSWORD)

# Case 1 — not submitted
A1 = f"qa.ui1.a.{TS}@example.com"
rid1, tok1 = _mk_case(pro, A1, f"qa.ui1.b.{TS}@example.com", "C1")
_register(A1, "QA UI1 A", invite=tok1["a"])
pa1 = _login(A1, PARENT_PASSWORD)
_accept_invite(pa1, tok1["a"])
r = pa1.put(f"{BASE}/api/joint/reports/{rid1}/safety-screening/choose", json={"version": "A"}, timeout=15)
assert r.status_code == 200, r.text

# Case 2 — submitted, pro confirms protected_review on A
A2 = f"qa.ui2.a.{TS}@example.com"
rid2, tok2 = _mk_case(pro, A2, f"qa.ui2.b.{TS}@example.com", "C2")
_register(A2, "QA UI2 A", invite=tok2["a"])
pa2 = _login(A2, PARENT_PASSWORD)
_accept_invite(pa2, tok2["a"])
r = pa2.put(f"{BASE}/api/joint/reports/{rid2}/safety-screening/choose", json={"version": "A"}, timeout=15)
assert r.status_code == 200, r.text
r = pa2.put(f"{BASE}/api/joint/reports/{rid2}/safety-screening",
            json={"responses": {"a1": "Never", "x_2": "Sometimes", "safe": "Very safe"}}, timeout=15)
assert r.status_code == 200, r.text
r = pro.put(f"{BASE}/api/joint/reports/{rid2}/safety-pathway/a",
            json={"action": "change", "pathway": "protected_review"}, timeout=15)
assert r.status_code == 200, r.text

print(json.dumps({
    "rid1": rid1, "a1_email": A1,
    "rid2": rid2, "a2_email": A2,
    "pro_email": PRO_EMAIL, "pro_pw": PRO_PASSWORD, "parent_pw": PARENT_PASSWORD,
}))
