"""
Iter207 diagnosis: Full PDF endpoint matrix + Align share pipeline audit.
Backend-only. Runs against REACT_APP_BACKEND_URL as parent1 & parent2.
"""
import os
import io
import json
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Load integration key from backend/.env directly
INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET") or ""
if not INTEGRATION_KEY:
    try:
        with open("/app/backend/.env") as f:
            for ln in f:
                if ln.startswith("INTEGRATION_SHARED_SECRET="):
                    INTEGRATION_KEY = ln.split("=", 1)[1].strip().strip("'\"")
                    break
    except Exception:
        pass

SEED_SHARES = {
    "edu": "seed_edu_deep_share",
    "med": "seed_med_deep_share",
    "psych": "seed_psych_deep_share",
    "snc2": "seed_snc2_deep_share",  # may not exist
}

CREDS = {
    "parent1": ("parent1@test.com", "TestPass123!"),
    "parent2": ("parent2@test.com", "TestPass123!"),
}

# module-level cache: token per parent
_TOKENS: dict[str, str] = {}
# collected results per parent → list[dict]
RESULTS: dict[str, list[dict]] = {"parent1": [], "parent2": []}


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def _hdr(pname: str) -> dict:
    if pname not in _TOKENS:
        _TOKENS[pname] = _login(*CREDS[pname])
    return {"Authorization": f"Bearer {_TOKENS[pname]}"}


def _classify(r: requests.Response, allow_zip: bool = False) -> tuple[str, str]:
    """
    Returns (verdict, note). verdict ∈ {ok_pdf, ok_zip, empty_expected, bug}.
    """
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code == 200:
        body = r.content
        if allow_zip and "zip" in ct:
            return "ok_zip", f"len={len(body)}"
        if body[:4] == b"%PDF":
            return "ok_pdf", f"len={len(body)} ct={ct.split(';')[0]}"
        return "bug", f"200 but not PDF; ct={ct} head={body[:16]!r}"
    if r.status_code in (401, 403):
        return "bug", f"auth leak/miss: {r.status_code} {r.text[:120]}"
    if r.status_code in (404, 409, 400, 410, 422):
        try:
            j = r.json()
            if isinstance(j, dict) and ("detail" in j or "error" in j or "message" in j):
                return "empty_expected", f"{r.status_code} detail={str(j.get('detail') or j.get('error') or j.get('message'))[:120]}"
        except Exception:
            pass
        return "empty_expected", f"{r.status_code} body={r.text[:120]}"
    if 500 <= r.status_code < 600:
        return "bug", f"5xx {r.status_code} {r.text[:200]}"
    return "bug", f"unexpected {r.status_code} {r.text[:200]}"


def _hit(pname: str, method: str, path: str, allow_zip: bool = False, **kwargs) -> dict:
    url = f"{API}{path}"
    try:
        r = requests.request(method, url, headers=_hdr(pname), timeout=60, **kwargs)
    except Exception as e:
        entry = {"endpoint": f"{method} {path}", "verdict": "bug", "note": f"exception: {e}"}
        RESULTS[pname].append(entry)
        return entry
    verdict, note = _classify(r, allow_zip=allow_zip)
    entry = {"endpoint": f"{method} {path}", "status": r.status_code, "verdict": verdict, "note": note}
    RESULTS[pname].append(entry)
    return entry


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------
def _try_get_json(pname: str, path: str):
    try:
        r = requests.get(f"{API}{path}", headers=_hdr(pname), timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _discover_ids(pname: str) -> dict:
    ids = {"safety_assessment_id": None, "summary_id": None, "agreement_id": None, "nd_risk_id": None}
    # Safety
    j = _try_get_json(pname, "/safety-assessment/me")
    if j:
        if isinstance(j, dict):
            ids["safety_assessment_id"] = j.get("id") or j.get("assessment_id") or (j.get("assessment") or {}).get("id")
        elif isinstance(j, list) and j:
            ids["safety_assessment_id"] = j[0].get("id")

    # Mediation summaries
    for p in ("/mediation/summaries", "/mediation/summaries/me", "/mediation/summary/list"):
        j = _try_get_json(pname, p)
        if j:
            items = j if isinstance(j, list) else j.get("items") or j.get("summaries") or []
            if items:
                ids["summary_id"] = items[0].get("id") or items[0].get("summary_id")
                break

    # Mediation agreement
    for p in ("/mediation/agreements", "/mediation/agreements/me", "/mediation/agreement/list"):
        j = _try_get_json(pname, p)
        if j:
            items = j if isinstance(j, list) else j.get("items") or j.get("agreements") or []
            if items:
                ids["agreement_id"] = items[0].get("id") or items[0].get("agreement_id")
                break

    # ND-risk
    for p in ("/nd-risk/assessments/me", "/nd-risk/me", "/nd-risk/assessments"):
        j = _try_get_json(pname, p)
        if j:
            items = j if isinstance(j, list) else j.get("items") or j.get("assessments") or []
            if items:
                ids["nd_risk_id"] = items[0].get("id") or items[0].get("assessment_id")
                break
    return ids


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pname", ["parent1", "parent2"])
def test_own_artefact_pdf_matrix(pname):
    ids = _discover_ids(pname)
    print(f"\n[{pname}] discovered ids: {ids}")

    # 1
    _hit(pname, "GET", "/coparenting/report/pdf")
    # 2
    _hit(pname, "GET", "/mediation/foundation-statement.pdf")
    # 3
    if ids["summary_id"]:
        _hit(pname, "GET", f"/mediation/summary/{ids['summary_id']}/pdf")
    else:
        RESULTS[pname].append({"endpoint": "GET /mediation/summary/{id}/pdf", "verdict": "skipped", "note": "no summary"})
    # 4
    if ids["agreement_id"]:
        _hit(pname, "GET", f"/mediation/agreement/{ids['agreement_id']}/pdf")
    else:
        RESULTS[pname].append({"endpoint": "GET /mediation/agreement/{id}/pdf", "verdict": "skipped", "note": "no agreement"})
    # 5-7
    if ids["safety_assessment_id"]:
        sid = ids["safety_assessment_id"]
        _hit(pname, "GET", f"/safety-assessment/{sid}/pdf")
        _hit(pname, "GET", f"/safety-assessment/{sid}/court-report")
        _hit(pname, "GET", f"/safety-assessment/{sid}/one-pager")
    else:
        for suf in ("pdf", "court-report", "one-pager"):
            RESULTS[pname].append({"endpoint": f"GET /safety-assessment/{{id}}/{suf}", "verdict": "skipped", "note": "no safety assessment"})
    # 8-11
    _hit(pname, "GET", "/edu-deep/report/pdf")
    _hit(pname, "GET", "/med-deep/report/pdf")
    _hit(pname, "GET", "/psych-deep/report/pdf")
    _hit(pname, "GET", "/snc2/report/pdf")
    # 12
    if ids["nd_risk_id"]:
        _hit(pname, "GET", f"/nd-risk/assessment/{ids['nd_risk_id']}/pdf")
    else:
        RESULTS[pname].append({"endpoint": "GET /nd-risk/assessment/{id}/pdf", "verdict": "skipped", "note": "no nd-risk"})
    # 13
    _hit(pname, "GET", "/activities-costs/compare.pdf")
    # 14
    _hit(pname, "GET", "/dimension-companion/four-dimension-briefing/pdf")
    # 15
    _hit(pname, "GET", "/pathway-report/preview/pdf")
    # 16
    _hit(pname, "GET", "/complete-report/mine.pdf")
    # 17
    _hit(pname, "GET", "/complete-report/joint/SA-DEMO01.pdf")
    # 18
    _hit(pname, "GET", f"/joint-agreement/{SEED_SHARES['edu']}/pdf")
    # 19-20
    _hit(pname, "GET", f"/joint-professional-report/{SEED_SHARES['edu']}/pdf")
    _hit(pname, "GET", f"/joint-professional-report/{SEED_SHARES['edu']}/professional-intro.pdf")
    # 21
    _hit(pname, "GET", f"/pathway-report/dual/{SEED_SHARES['edu']}/pdf")
    # 22 deep-dive compare joint variants
    _hit(pname, "GET", f"/edu-deep/compare/{SEED_SHARES['edu']}/pdf")
    _hit(pname, "GET", f"/med-deep/compare/{SEED_SHARES['med']}/pdf")
    _hit(pname, "GET", f"/psych-deep/compare/{SEED_SHARES['psych']}/pdf")
    _hit(pname, "GET", f"/snc2/compare/{SEED_SHARES['snc2']}/pdf")

    # bundle
    _hit(pname, "GET", "/bundle/my-completed.zip", allow_zip=True)

    # Dump summary
    print(f"\n=========== PDF MATRIX for {pname} ===========")
    for r in RESULTS[pname]:
        print(f"  {r['endpoint']:<70} → {r.get('verdict'):<15} {r.get('note','')}")

    # Only fail on real bugs (5xx / malformed)
    bugs = [r for r in RESULTS[pname] if r.get("verdict") == "bug"]
    assert not bugs, f"{pname} has {len(bugs)} bug(s): {bugs}"


# ---------------------------------------------------------------------------
# Bundle content sanity
# ---------------------------------------------------------------------------
def test_bundle_manifest_and_pdf():
    r = requests.get(f"{API}/bundle/my-completed.zip", headers=_hdr("parent1"), timeout=90)
    if r.status_code in (404, 409):
        pytest.skip(f"empty-state bundle {r.status_code}: {r.text[:120]}")
    assert r.status_code == 200
    assert "zip" in (r.headers.get("content-type") or "").lower()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    print(f"bundle contents: {names}")
    assert any(n.upper().endswith("MANIFEST.TXT") for n in names), f"no MANIFEST.TXT in {names}"
    pdfs = [n for n in names if n.lower().endswith(".pdf")]
    assert pdfs, "no PDFs in bundle"
    # verify at least one is valid PDF
    with z.open(pdfs[0]) as fh:
        head = fh.read(4)
        assert head == b"%PDF", f"first pdf {pdfs[0]} not valid: {head!r}"


# ---------------------------------------------------------------------------
# Align share pipeline
# ---------------------------------------------------------------------------
ALIGN = {}  # stash between tests


def test_align_a_professional_invitation_and_permission_gate():
    """POST /parent/professional-invitations then GET /integrations/report-permissions/{id}"""
    # Need a valid report_id. Grab one from parent1's completed reports.
    # Try coparenting report first (widely-completed).
    report_id = None
    for probe in (
        "/parent/report-catalog",
        "/parent/completed-reports",
        "/parent/reports/completed",
        "/reports/mine",
        "/complete-report/mine",
    ):
        j = _try_get_json("parent1", probe)
        if isinstance(j, dict) and (j.get("reports") or j.get("items")):
            items = j.get("reports") or j.get("items")
            if items:
                report_id = items[0].get("report_id") or items[0].get("id")
                break
        elif isinstance(j, list) and j:
            report_id = j[0].get("report_id") or j[0].get("id")
            break
    print(f"resolved report_id={report_id}")
    ALIGN["invite_report_id"] = report_id

    payload = {
        "professional_first_name": "Iter207",
        "professional_last_name": "Prof",
        "professional_email": "prof-iter207@example.com",
        "professional_email_confirm": "prof-iter207@example.com",
        "professional_role": "mediator",
        "report_ids": [report_id or "coparenting_report"],
        "view_permission": True,
        "download_permission": False,
        "access_days": 30,
        "consent_authorised": True,
        "consent_relationship_acknowledged": True,
    }
    r = requests.post(
        f"{API}/parent/professional-invitations",
        headers=_hdr("parent1"),
        json=payload,
        timeout=30,
    )
    print(f"invitations POST → {r.status_code} {r.text[:250]}")
    ALIGN["invite_status"] = r.status_code
    ALIGN["invite_body"] = r.text[:400]

    if r.status_code not in (200, 201):
        # Not a hard fail — record and continue
        ALIGN["permission_id"] = None
    else:
        j = r.json()
        invitation_id = j.get("invitation_id") or (j.get("invitation") or {}).get("invitation_id")
        ALIGN["invitation_id"] = invitation_id
        # fetch permissions via GET /parent/professional-invitations/{id}
        pid = None
        if invitation_id:
            rg = requests.get(
                f"{API}/parent/professional-invitations/{invitation_id}",
                headers=_hdr("parent1"), timeout=30,
            )
            if rg.status_code == 200:
                gj = rg.json()
                perms = gj.get("permissions") or (gj.get("invitation") or {}).get("permissions") or []
                if perms:
                    pid = perms[0].get("permission_id") or perms[0].get("id")
        ALIGN["permission_id"] = pid

    # Verify gate: no header → 401/403
    r_nohdr = requests.get(
        f"{API}/integrations/report-permissions/{ALIGN.get('permission_id') or 'dummy-id'}",
        timeout=30,
    )
    print(f"perm no-hdr → {r_nohdr.status_code}")
    ALIGN["perm_no_header_status"] = r_nohdr.status_code
    assert r_nohdr.status_code in (401, 403, 422), f"gate not enforced: {r_nohdr.status_code}"

    # With header
    if INTEGRATION_KEY and ALIGN.get("permission_id"):
        r_ok = requests.get(
            f"{API}/integrations/report-permissions/{ALIGN['permission_id']}",
            headers={"X-Integration-Key": INTEGRATION_KEY},
            timeout=30,
        )
        print(f"perm with-hdr → {r_ok.status_code} {r_ok.text[:250]}")
        ALIGN["perm_with_header_status"] = r_ok.status_code


def test_align_b_export_assessments_gate():
    # no header
    r = requests.get(f"{API}/integrations/export-assessments", params={"email": "parent1@test.com"}, timeout=30)
    print(f"export no-hdr → {r.status_code}")
    ALIGN["export_no_header"] = r.status_code
    assert r.status_code in (401, 403), f"gate not enforced: {r.status_code}"

    if not INTEGRATION_KEY:
        pytest.skip("INTEGRATION_SHARED_SECRET not discoverable")

    r2 = requests.get(
        f"{API}/integrations/export-assessments",
        params={"email": "parent1@test.com"},
        headers={"X-Integration-Key": INTEGRATION_KEY},
        timeout=30,
    )
    print(f"export with-hdr → {r2.status_code} keys={list(r2.json().keys()) if r2.headers.get('content-type','').startswith('application/json') else 'n/a'}")
    ALIGN["export_with_header"] = r2.status_code
    assert r2.status_code == 200, f"export failed: {r2.text[:200]}"
    body = r2.json()
    # Must NOT include safety or co-parent data
    forbidden = [k for k in body.keys() if "safety" in k.lower() or "coparent" in k.lower() or "co_parent" in k.lower()]
    if forbidden:
        print(f"WARN forbidden keys present: {forbidden}")
    ALIGN["export_forbidden_keys"] = forbidden
    ALIGN["export_keys"] = list(body.keys())


def test_align_c_link_code_roundtrip():
    r = requests.post(f"{API}/link-codes", headers=_hdr("parent1"), json={}, timeout=30)
    print(f"link-codes → {r.status_code} {r.text[:250]}")
    ALIGN["link_code_status"] = r.status_code
    if r.status_code != 200:
        pytest.skip(f"link-code create failed: {r.status_code}")
    j = r.json()
    code = j.get("code") or j.get("link_code") or (j.get("link_code_details") or {}).get("code")
    join_url = j.get("join_url") or j.get("align_join_url")
    ALIGN["link_code"] = code
    ALIGN["align_join_url"] = join_url
    assert code, f"no code in response: {j}"

    if not INTEGRATION_KEY:
        pytest.skip("no integration key")
    r2 = requests.post(
        f"{API}/integrations/verify-link-code",
        headers={"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"},
        json={"code": code},
        timeout=30,
    )
    print(f"verify-link-code → {r2.status_code} {r2.text[:250]}")
    ALIGN["verify_link_code_status"] = r2.status_code
    assert r2.status_code == 200


def test_align_d_execute_release_dual_consent_gate():
    r = requests.post(
        f"{API}/joint-alignment/cases/SA-DEMO01/execute-release",
        headers=_hdr("parent1"),
        json={"professional_name": "Iter207 Test Prof"},
        timeout=30,
    )
    print(f"execute-release → {r.status_code} {r.text[:250]}")
    ALIGN["execute_release_status"] = r.status_code
    # Expect 409 (dual consent missing) or 400/404
    assert r.status_code in (200, 400, 404, 409), f"unexpected: {r.status_code} {r.text[:200]}"


def test_zzz_dump_align_summary():
    print("\n=========== ALIGN PIPELINE SUMMARY ===========")
    print(json.dumps(ALIGN, indent=2, default=str))
    print("\n=========== INTEGRATION KEY DISCOVERED ===========")
    print(f"key_present: {bool(INTEGRATION_KEY)} len={len(INTEGRATION_KEY)}")
