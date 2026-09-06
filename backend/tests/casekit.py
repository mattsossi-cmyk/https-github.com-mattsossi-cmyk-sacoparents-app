"""Shared helpers for tests: Align is professional-initiated, so parents are
created through a real invitation (pro creates case -> parent registers with
the invite token -> parent accepts)."""
import os
import uuid
import requests

# Throwaway password for self-destructing test accounts only — not a real secret.
TEST_PASSWORD = os.environ.get("E2E_TEST_PASSWORD", "testpass123")

ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


def new_user(api, role="professional", name="T", email=None, password=None, invite=""):
    s = requests.Session()
    email = email or f"t_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{api}/auth/register", json={
        "name": name, "email": email, "password": password or TEST_PASSWORD, "role": role, "invite": invite,
    })
    assert r.status_code == 200, f"register {role} failed: {r.status_code} {r.text}"
    s.email = email
    s.name = name
    return s


def new_case(api, subject="education", child="TEST_Kid", custom_subject="", subjects=None,
             pa_email=None, pb_email=None, case_reference=""):
    """Pro creates a case; both parents register via their invite tokens and accept.
    Returns (pro, pa, pb, create_response_dict)."""
    pro = new_user(api, "professional", "Pro")
    ea = pa_email or f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
    eb = pb_email or f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "subject": subject, "custom_subject": custom_subject, "child_name": child,
        "parent_a_name": "Parent A", "parent_a_email": ea,
        "parent_b_name": "Parent B", "parent_b_email": eb,
    }
    if subjects:
        payload["subjects"] = subjects
    if case_reference:
        payload["case_reference"] = case_reference
    r = pro.post(f"{api}/joint/reports/professional", json=payload)
    assert r.status_code == 200, f"pro create failed: {r.status_code} {r.text}"
    d = r.json()
    toks = {i["role"]: i["link"].rsplit("/", 1)[-1] for i in d["invitations"]}
    pa = new_user(api, "parent", "Parent A", email=ea, invite=toks["a"])
    pb = new_user(api, "parent", "Parent B", email=eb, invite=toks["b"])
    for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
        r = s.post(f"{api}/joint/invitations/accept", json={"code": tok})
        assert r.json().get("ok"), f"accept failed: {r.text}"
    return pro, pa, pb, d


def fill(api, session, rid, theme):
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


def completed_case(api, subject="education", **kwargs):
    """Full cycle: case created, both parents accept and complete. Returns (pro, pa, pb, report, detail)."""
    pro, pa, pb, d = new_case(api, subject=subject, **kwargs)
    rid = d["id"]
    fill(api, pa, rid, "alpha")
    fill(api, pb, rid, "beta")
    detail = pro.get(f"{api}/joint/reports/{rid}").json()
    assert detail["status"] == "ready", detail["status"]
    return pro, pa, pb, d, detail
