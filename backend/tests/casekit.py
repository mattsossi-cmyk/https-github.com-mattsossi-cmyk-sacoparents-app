"""Shared helpers for tests: Align is professional-initiated, so parents are
created through a real invitation (pro creates case -> parent registers with
the invite token -> parent accepts)."""
import os
import uuid
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

# Throwaway password for self-destructing test accounts only — not a real secret.
TEST_PASSWORD = os.environ.get("E2E_TEST_PASSWORD", "testpass123")

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


@dataclass
class CaseSpec:
    subject: str = "education"
    child: str = "TEST_Kid"
    custom_subject: str = ""
    subjects: list | None = None
    pa_email: str | None = None
    pb_email: str | None = None
    case_reference: str = ""


def _approve(email: str) -> None:
    """Test fixtures act as already-approved professionals (real signups are pending)."""
    import pymongo
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    client[os.environ["DB_NAME"]].users.update_one({"email": email.lower()}, {"$set": {"approved": True}})
    client.close()


def new_user(api: str, role: str = "professional", name: str = "T", email: str | None = None,
             password: str | None = None, invite: str = "") -> requests.Session:
    s = requests.Session()
    email = email or f"t_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{api}/auth/register", json={
        "name": name, "email": email, "password": password or TEST_PASSWORD, "role": role,
        "invite": invite, "agreements_accepted": role == "professional",
    })
    assert r.status_code == 200, f"register {role} failed: {r.status_code} {r.text}"
    if role == "professional":
        _approve(email)
    s.email = email
    s.name = name
    return s


def new_case(api: str, spec: CaseSpec | None = None, **overrides) -> tuple:
    """Pro creates a case; both parents register via their invite tokens and accept.
    Returns (pro, pa, pb, create_response_dict)."""
    spec = spec or CaseSpec(**overrides)
    pro = new_user(api, "professional", "Pro")
    ea = spec.pa_email or f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
    eb = spec.pb_email or f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "subject": spec.subject, "custom_subject": spec.custom_subject, "child_name": spec.child,
        "parent_a_name": "Parent A", "parent_a_email": ea,
        "parent_b_name": "Parent B", "parent_b_email": eb,
    }
    if spec.subjects:
        payload["subjects"] = spec.subjects
    if spec.case_reference:
        payload["case_reference"] = spec.case_reference
    r = pro.post(f"{api}/joint/reports/professional", json=payload)
    assert r.status_code == 200, f"pro create failed: {r.status_code} {r.text}"
    d = r.json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    pa = new_user(api, "parent", "Parent A", email=ea, invite=toks["a"])
    pb = new_user(api, "parent", "Parent B", email=eb, invite=toks["b"])
    for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
        r = s.post(f"{api}/joint/invitations/accept", json={"code": tok})
        assert r.json().get("ok"), f"accept failed: {r.text}"
    return pro, pa, pb, d


def fill(api: str, session: requests.Session, rid: str, theme: str) -> dict:
    answers = {
        "needs_most": f"Our child needs {theme} academic support and consistent homework routines.",
        "working_well": f"The current homework schedule at my home works with {theme} consistent evening routines.",
        "concerns": f"I'm concerned about inconsistent homework completion and {theme} varying expectations between homes.",
        "improve": f"I would like to improve communication about homework and academic {theme} expectations.",
        "options": f"Option A: shared homework log. Option B: same homework times. {theme} coordinated with teacher.",
        "other_parent": f"The other parent likely worries about homework quality and {theme} academic consistency.",
    }
    r = session.put(f"{api}/joint/reports/{rid}/responses", json={"answers": answers})
    assert r.status_code == 200, f"fill failed: {r.status_code} {r.text}"
    return r.json()


def completed_case(api: str, subject: str = "education", **kwargs) -> tuple:
    """Full cycle: case created, both parents accept and complete. Returns (pro, pa, pb, report, detail)."""
    pro, pa, pb, d = new_case(api, CaseSpec(subject=subject, **kwargs))
    rid = d["id"]
    fill(api, pa, rid, "alpha")
    fill(api, pb, rid, "beta")
    detail = pro.get(f"{api}/joint/reports/{rid}").json()
    assert detail["status"] == "ready", detail["status"]
    return pro, pa, pb, d, detail
