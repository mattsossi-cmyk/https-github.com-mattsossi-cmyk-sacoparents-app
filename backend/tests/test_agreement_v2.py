"""Redefined SA CoParents Co-Parenting Agreement: 10 sections, follow-ups, three-way sorting, AI/rule drafting."""
import io
import os
import uuid

import requests

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SECTION_KEYS = ["foundation", "transitions", "communication", "education", "medical", "psychological", "activities", "wellness_tech", "decisions", "differences", "review"]


def _answers(variant: str) -> dict:
    a = {k: f"We should keep {k} predictable and child focused with clear written notice and shared information" for k in SECTION_KEYS}
    a["education__records"] = "Both parents get portal access; Mom sets it up this month"
    a["education__share"] = "Within 2 days by the co-parenting app"
    a["education__disagree"] = "Ask the teacher first, then the school counselor" if variant == "a" else "Dad decides because he handles school"
    a["medical__emergency"] = "Call 911 then the other parent within 30 minutes"
    return a


def _agreement_case() -> tuple:
    pro = new_user(API, "professional", "Agreement Pro")
    ea, eb = f"t_pa_{uuid.uuid4().hex[:8]}@example.com", f"t_pb_{uuid.uuid4().hex[:8]}@example.com"
    r = pro.post(f"{API}/joint/agreements", json={"child_name": "Avery", "parent_a_name": "Parent A", "parent_a_email": ea, "parent_b_name": "Parent B", "parent_b_email": eb})
    assert r.status_code == 200, r.text
    d = r.json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    pa = new_user(API, "parent", "Parent A", email=ea, invite=toks["a"])
    pb = new_user(API, "parent", "Parent B", email=eb, invite=toks["b"])
    for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).json().get("ok")
        assert s.post(f"{API}/joint/reports/{d['id']}/safety-screening/decline").status_code == 200  # Start-with-Safety step
    return pro, pa, pb, d["id"]


def test_config_exposes_eleven_sections_with_follow_ups() -> None:
    pro = new_user(API, "professional", "Cfg Pro")
    cfg = pro.get(f"{API}/joint/config").json()
    secs = cfg["agreement_sections"]
    assert [s["key"] for s in secs] == SECTION_KEYS
    edu = next(s for s in secs if s["key"] == "education")
    assert edu["num"] == 4 and edu["goal"] and len(edu["follow_ups"]) == 5
    assert edu["follow_ups"][0]["key"] == "education__records"


def test_agreement_requires_main_answers_but_not_follow_ups() -> None:
    _pro, pa, _pb, rid = _agreement_case()
    partial = {k: "x" for k in SECTION_KEYS[:-1]}
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": partial}).status_code == 400
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {k: "ok" for k in SECTION_KEYS}}).status_code == 200


def test_agreement_report_sorts_three_ways_and_pdf_renders() -> None:
    import fitz
    pro, pa, pb, rid = _agreement_case()
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("a")}).status_code == 200
    assert pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers("b")}).status_code == 200
    rep = pro.get(f"{API}/joint/reports/{rid}/report")
    assert rep.status_code == 200, rep.text
    r = rep.json()
    assert r["report_title"] == "SA CoParents Co-Parenting Agreement"
    assert [s["key"] for s in r["sections"]] == SECTION_KEYS
    edu = next(s for s in r["sections"] if s["key"] == "education")
    for f in ("shared_goal", "current_alignment", "specific_agreements", "open_issues", "status"):
        assert f in edu
    assert edu["current_alignment"], "identical proposals must register alignment"
    joined = " ".join(edu["specific_agreements"]).lower()
    assert "portal" in joined or "2 days" in joined or "app" in joined
    assert edu["open_issues"], "differing 'disagree' answers must surface as an issue, not an agreement"
    assert not any("dad decides" in c.lower() for c in edu["specific_agreements"])
    assert set(r["summary"]) == {"alignment", "specific", "resolution"} and r["summary"]["resolution"]
    pdf = pro.get(f"{API}/joint/reports/{rid}/pdf")
    assert pdf.status_code == 200
    doc = fitz.open(stream=io.BytesIO(pdf.content), filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    assert "Child-Focused Co-Parenting Agreement" in text and "Areas Requiring Agreement" in text and "Educational Decisions" in text
    assert "2026 sacoparentsalign.com" in text
