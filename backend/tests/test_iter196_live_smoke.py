"""Live smoke against public REACT_APP_BACKEND_URL for iter196 endpoints."""
import os
import requests
import uuid

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_case_unauth_returns_401():
    r = requests.get(f"{BASE}/api/joint-alignment/case/SA-DEMO01", timeout=30)
    assert r.status_code in (401, 403)


def test_case_404_for_missing():
    tok = _login("parent1@test.com", "TestPass123!")
    r = requests.get(f"{BASE}/api/joint-alignment/case/SA-999999", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    assert r.status_code == 404, r.text


def test_case_demo01_parent1_ok():
    tok = _login("parent1@test.com", "TestPass123!")
    r = requests.get(f"{BASE}/api/joint-alignment/case/SA-DEMO01", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("case_id", "status", "professional", "assigned_steps", "parents", "me"):
        assert k in data, f"missing {k}"
    assert isinstance(data["assigned_steps"], list) and data["assigned_steps"]
    step0 = data["assigned_steps"][0]
    for k in ("assessment_type", "required", "label", "parent_statuses"):
        assert k in step0
    assert "email" in data["me"] and "steps" in data["me"]
    step_m = data["me"]["steps"][0]
    for k in ("assessment_type", "label", "required", "status"):
        assert k in step_m


def test_professional_create_case_with_extra_steps():
    tok = _login("parent1@test.com", "TestPass123!")  # parent1 doubles as demo prof
    a = f"live_{uuid.uuid4().hex[:6]}_a@test.com"
    b = f"live_{uuid.uuid4().hex[:6]}_b@test.com"
    payload = {
        "assessment_type": "co-parenting",
        "parents": [{"email": a}, {"email": b}],
        "assigned_steps": [
            {"assessment_type": "educational", "required": False},
            {"assessment_type": "medical", "required": True},
        ],
    }
    r = requests.post(
        f"{BASE}/api/professional/joint-alignment/cases",
        json=payload,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    case_id = data.get("case_id") or data.get("case", {}).get("case_id")
    assert case_id, f"no case_id in create response: {data}"
    # Fetch the case via GET (as the professional/parent1) to see assigned_steps
    g = requests.get(f"{BASE}/api/joint-alignment/case/{case_id}",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    # Professional may or may not be a parent; if 403 skip assertion beyond creation
    if g.status_code == 200:
        steps = g.json().get("assigned_steps") or []
        types = [(s["assessment_type"], s["required"]) for s in steps]
        assert types and types[0] == ("co-parenting", True), f"first must be primary+required, got {types}"
        assert ("educational", False) in types
        assert ("medical", True) in types
    else:
        # At minimum verify create succeeded
        assert g.status_code in (403, 404)


def test_professional_create_case_rejects_unknown_type():
    tok = _login("parent1@test.com", "TestPass123!")
    payload = {
        "assessment_type": "co-parenting",
        "parents": [{"email": "x@test.com"}, {"email": "y@test.com"}],
        "assigned_steps": [{"assessment_type": "bogus-type-xyz", "required": False}],
    }
    r = requests.post(
        f"{BASE}/api/professional/joint-alignment/cases",
        json=payload,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    assert r.status_code == 400, r.text
