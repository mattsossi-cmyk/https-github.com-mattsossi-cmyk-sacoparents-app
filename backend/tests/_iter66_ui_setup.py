"""Iter66 UI setup: login as approval.test.pro1, create a case with two parents,
fill both parents' answers so Section 4 has content for lens-child-suggest.
Prints the case id + parent A credentials for the UI script."""
import os
import sys
import uuid

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PW = "TestPass2026!"


def main():
    pro = requests.Session()
    r = pro.post(f"{API}/auth/login", json={"email": PRO_EMAIL, "password": PRO_PW})
    assert r.status_code == 200, r.text
    ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
    eb = f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
    pw = "testpass123"
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "child_name": "TEST_Iter66",
        "parent_a_name": "Parent A", "parent_a_email": ea,
        "parent_b_name": "Parent B", "parent_b_email": eb,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    rid = d["id"]
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}

    def _reg(email, tok, name):
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "name": name, "email": email, "password": pw, "role": "parent",
            "invite": tok, "agreements_accepted": False,
        })
        assert r.status_code == 200, r.text
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).json().get("ok")
        return s

    pa = _reg(ea, toks["a"], "Parent A")
    pb = _reg(eb, toks["b"], "Parent B")

    answers_a = {
        "needs_most": "Our child needs consistent homework routines across homes.",
        "working_well": "Evenings at my home have a predictable schedule.",
        "concerns": "I am worried about inconsistent homework completion between homes.",
        "improve": "I would like better coordination on academic expectations.",
        "options": "Shared homework log, aligned bedtimes.",
        "other_parent": "The other parent likely worries about quality of homework.",
    }
    answers_b = {k: v.replace("my home", "our home") for k, v in answers_a.items()}
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers_a}).status_code == 200
    assert pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers_b}).status_code == 200

    print(f"CASE_ID={rid}")
    print(f"PARENT_A_EMAIL={ea}")
    print(f"PARENT_A_PASSWORD={pw}")
    print(f"PARENT_B_EMAIL={eb}")


if __name__ == "__main__":
    main()
