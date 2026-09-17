"""Create ready cases for colleague and stranger for iteration 49 UI checks."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case, TEST_PASSWORD  # noqa
import pymongo, requests  # noqa

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ORG = "Alamo Test Org"


def _login(email, password=TEST_PASSWORD):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


def _login_or_new_case(email):
    # Log in as existing user, use their existing (new) case flow.
    # We'll create a *new* completed case as that user by directly running new_case with pro=that user session.
    # But completed_case creates a new_user. Instead, mimic new_case with existing pro session:
    from casekit import CaseSpec, fill
    import uuid
    from casekit import new_user
    # Log in to that user
    pro = _login(email)
    pro.email = email
    ea = f"t_pa_{uuid.uuid4().hex[:8]}@example.com"
    eb = f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"subject": "education", "child_name": "TEST_Kid",
               "parent_a_name": "PA", "parent_a_email": ea,
               "parent_b_name": "PB", "parent_b_email": eb}
    r = pro.post(f"{API}/joint/reports/professional", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    rid = d["id"]
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    pa = new_user(API, "parent", "PA", email=ea, invite=toks["a"])
    pb = new_user(API, "parent", "PB", email=eb, invite=toks["b"])
    for s, tok, theme in ((pa, toks["a"], "alpha"), (pb, toks["b"], "beta")):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).json().get("ok")
        fill(API, s, rid, theme)
    return rid


if __name__ == "__main__":
    col = os.environ.get("COLLEAGUE", "t_2bc1fe43@example.com")
    stg = os.environ.get("STRANGER", "t_dce2e321@example.com")
    out = {"colleague_rid": _login_or_new_case(col), "stranger_rid": _login_or_new_case(stg)}
    print(json.dumps(out, indent=2))
