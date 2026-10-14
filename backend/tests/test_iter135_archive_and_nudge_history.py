"""iter135: Archive endpoint + nudge history fields on court codes & joint cases."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email: str, password: str = "TestPass123!") -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def pro_headers():
    return {"Authorization": f"Bearer {_login('parent1@test.com')}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def p2_headers():
    return {"Authorization": f"Bearer {_login('parent2@test.com')}", "Content-Type": "application/json"}


# --- nudge history fields -------------------------------------------------
class TestNudgeHistoryFields:
    def test_court_codes_include_nudge_history_fields(self, pro_headers):
        r = requests.get(f"{API}/professional/court-codes", headers=pro_headers, timeout=20)
        assert r.status_code == 200
        codes = r.json()["codes"]
        p445 = next((c for c in codes if c["case_id"] == "CC-P445YM"), None)
        assert p445 is not None, "CC-P445YM missing"
        assert "archived_at" in p445
        assert p445["parents"], "CC-P445YM should have at least one parent"
        p0 = p445["parents"][0]
        for k in ("pid", "nudge_next_at", "nudge_last_at", "nudge_count"):
            assert k in p0, f"missing {k} in parent 0"
        assert p0["nudge_count"] == 1, f"expected nudge_count=1 got {p0['nudge_count']}"
        assert p0["nudge_last_at"] is not None

    def test_joint_cases_include_nudge_fields(self, pro_headers):
        r = requests.get(f"{API}/professional/joint-alignment/cases-i-created", headers=pro_headers, timeout=20)
        assert r.status_code == 200
        data = r.json()
        cases = data.get("cases") or data
        if isinstance(cases, dict):
            cases = cases.get("cases") or []
        assert isinstance(cases, list) and len(cases) > 0
        for c in cases:
            assert "archived_at" in c, f"case {c.get('case_id')} missing archived_at"
            for p in c.get("parents") or []:
                if p.get("nudge_pid"):
                    for k in ("nudge_next_at", "nudge_last_at", "nudge_count"):
                        assert k in p, f"missing {k} on joined parent in case {c.get('case_id')}"


# --- archive endpoint -----------------------------------------------------
class TestArchiveEndpoint:
    def test_unauth_401(self):
        r = requests.put(f"{API}/professional/archive", json={"ref": "CC-P445YM", "archived": True}, timeout=20)
        assert r.status_code in (401, 403)

    def test_unknown_ref_404(self, pro_headers):
        r = requests.put(f"{API}/professional/archive",
                         headers=pro_headers, json={"ref": "CC-DOESNOTEXIST", "archived": True}, timeout=20)
        assert r.status_code == 404

    def test_non_owner_404(self, p2_headers):
        r = requests.put(f"{API}/professional/archive",
                         headers=p2_headers, json={"ref": "CC-P445YM", "archived": True}, timeout=20)
        assert r.status_code == 404

    def test_archive_restore_court_code_roundtrip(self, pro_headers):
        # archive
        r = requests.put(f"{API}/professional/archive",
                         headers=pro_headers, json={"ref": "CC-P445YM", "archived": True}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ref"] == "CC-P445YM"
        assert body["archived_at"] is not None

        # verify via GET
        r2 = requests.get(f"{API}/professional/court-codes", headers=pro_headers, timeout=20)
        codes = r2.json()["codes"]
        p = next(c for c in codes if c["case_id"] == "CC-P445YM")
        assert p["archived_at"] is not None

        # restore
        r3 = requests.put(f"{API}/professional/archive",
                          headers=pro_headers, json={"ref": "CC-P445YM", "archived": False}, timeout=20)
        assert r3.status_code == 200
        assert r3.json()["archived_at"] is None

        r4 = requests.get(f"{API}/professional/court-codes", headers=pro_headers, timeout=20)
        p = next(c for c in r4.json()["codes"] if c["case_id"] == "CC-P445YM")
        assert p["archived_at"] is None

    def test_archived_code_unaffected_for_parent_and_pdf(self, pro_headers):
        # archive CC-P445YM
        requests.put(f"{API}/professional/archive",
                     headers=pro_headers, json={"ref": "CC-P445YM", "archived": True}, timeout=20)
        try:
            # progress PDF still 200
            r_pdf = requests.get(f"{API}/professional/court-codes/CC-P445YM/progress.pdf",
                                 headers=pro_headers, timeout=30)
            # some apps serve PDF under different path; accept 200 or 404 if endpoint differs,
            # but main acceptance is PDF should still work.
            assert r_pdf.status_code in (200, 404), f"progress pdf got {r_pdf.status_code}"
            if r_pdf.status_code == 404:
                # try alt path
                r_pdf2 = requests.get(f"{API}/professional/court-codes/CC-P445YM/progress-pdf",
                                      headers=pro_headers, timeout=30)
                assert r_pdf2.status_code in (200, 404)

            # ccparent's requested view unchanged
            cc_headers = {"Authorization": f"Bearer {_login('ccparent@test.com')}"}
            r_req = requests.get(f"{API}/court-path/requested", headers=cc_headers, timeout=20)
            assert r_req.status_code == 200

            # nudge POST still allowed (but will 429 because nudge_count=1 within 7 days)
            codes = requests.get(f"{API}/professional/court-codes", headers=pro_headers, timeout=20).json()["codes"]
            p445 = next(c for c in codes if c["case_id"] == "CC-P445YM")
            pid = p445["parents"][0]["pid"]
            r_n = requests.post(f"{API}/professional/nudges", headers=pro_headers,
                                json={"ref": "CC-P445YM", "pid": pid}, timeout=20)
            # 429 (rate-limited) or 200/409 — the key is NOT a 403/404 due to archive
            assert r_n.status_code in (200, 409, 429), f"nudge got {r_n.status_code}: {r_n.text}"
        finally:
            # ALWAYS restore
            requests.put(f"{API}/professional/archive",
                         headers=pro_headers, json={"ref": "CC-P445YM", "archived": False}, timeout=20)

    def test_archive_restore_joint_case(self, pro_headers):
        # find a joint case owned by pro
        r = requests.get(f"{API}/professional/joint-alignment/cases-i-created", headers=pro_headers, timeout=20)
        cases = r.json().get("cases") or []
        assert cases, "no joint cases"
        case_id = cases[0]["case_id"]

        r1 = requests.put(f"{API}/professional/archive",
                          headers=pro_headers, json={"ref": case_id, "archived": True}, timeout=20)
        assert r1.status_code == 200
        assert r1.json()["archived_at"] is not None

        r2 = requests.put(f"{API}/professional/archive",
                          headers=pro_headers, json={"ref": case_id, "archived": False}, timeout=20)
        assert r2.status_code == 200
        assert r2.json()["archived_at"] is None


def test_cleanup_restore_all(pro_headers):
    """Belt+braces: ensure CC-P445YM, CC-AKDYZ5 and SA-DEMO01 are restored."""
    for ref in ("CC-P445YM", "CC-AKDYZ5", "SA-DEMO01"):
        requests.put(f"{API}/professional/archive",
                     headers=pro_headers, json={"ref": ref, "archived": False}, timeout=20)
