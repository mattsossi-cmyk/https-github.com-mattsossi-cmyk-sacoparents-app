"""SAFE-ND staff gate + limits using the seeded SAFE-ND test accounts (memory/test_credentials.md)."""
import json
import os

import pytest
import requests
from dotenv import dotenv_values

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
R = f"{BASE_URL}/api/safe-nd/reviews"
STAFF = ("safend.reviewer.90fd2f@example.com", "Password123!")
PARENT = ("t_pa_277a90b2@example.com", "Password123!")


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    return s


@pytest.fixture(scope="module")
def staff():
    return _login(*STAFF)


@pytest.fixture(scope="module")
def parent():
    return _login(*PARENT)


# Gate
def test_signed_out_401():
    assert requests.get(R).status_code == 401


def test_parent_403(parent):
    r = parent.get(R)
    assert r.status_code == 403
    assert "Staff sign-in required" in r.text


def test_staff_list_200(staff):
    r = staff.get(R)
    assert r.status_code == 200 and isinstance(r.json(), list)


# Limits
def test_text_plain_415(staff):
    assert staff.post(R, data='{"data":{}}', headers={"Content-Type": "text/plain"}).status_code == 415


def test_too_large_413(staff):
    body = json.dumps({"data": {"big": "x" * (501 * 1024)}})
    assert staff.post(R, data=body, headers={"Content-Type": "application/json"}).status_code == 413


def test_data_string_400(staff):
    assert staff.post(R, json={"data": "x"}).status_code == 400


def test_invalid_json_400(staff):
    assert staff.post(R, data="{not json", headers={"Content-Type": "application/json"}).status_code == 400


def test_unknown_review_404(staff):
    assert staff.get(f"{R}/does-not-exist").status_code == 404


# Lifecycle + lock + delete forbidden for professional
def test_lifecycle_lock_and_delete_forbidden(staff):
    r = staff.post(R, json={"data": {"case": {"child": "TEST_API child", "reviewDate": "2026-01-15"}}})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert staff.post(f"{R}/{rid}/finalize").status_code == 400  # no signature
    assert staff.put(f"{R}/{rid}", json={"data": {"case": {"child": "TEST_API child", "reviewDate": "2026-01-15"},
                                                  "disposition": {"signature": "Test Reviewer", "signedDate": "2026-01-15"}}}).status_code == 200
    assert staff.post(f"{R}/{rid}/finalize").status_code == 200
    g = staff.get(f"{R}/{rid}").json()
    assert g["status"] == "final" and g["data"]["case"]["child"] == "TEST_API child"
    assert staff.put(f"{R}/{rid}", json={"data": {}}).status_code == 409
    assert staff.post(f"{R}/{rid}/finalize").status_code == 409
    assert staff.delete(f"{R}/{rid}").status_code == 403
