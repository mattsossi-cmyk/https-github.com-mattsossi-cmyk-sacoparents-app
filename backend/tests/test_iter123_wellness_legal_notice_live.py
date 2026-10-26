"""Iter123: live API checks — Wellness, Phones & Social Media (Foundation + Agreement) and the new IMPORTANT LEGAL NOTICE on agreements."""
import io
import os
import uuid

import pymupdf
import pytest
import requests

from casekit import new_user, new_case, fill

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].rstrip("/")
API = f"{BASE_URL}/api"

KEYS = ["foundation", "transitions", "communication", "education", "medical", "psychological", "activities", "wellness_tech", "decisions", "differences", "review"]
WT_FU = ["wellness_tech__anchors", "wellness_tech__phone", "wellness_tech__social", "wellness_tech__screens", "wellness_tech__concerns"]
ACK = "By signing below, the parents acknowledge that they understand the purpose and potential legal limitations of this Agreement and that not all provisions are necessarily legally enforceable."
CONCERN = "Text the other parent within 24 hours about any sleep, mood or online safety concern"


def _norm(s):
    return " ".join(s.replace("’", "'").split())


def _pdf_text(content):
    return _norm("\n".join(p.get_text() for p in pymupdf.open(stream=io.BytesIO(content), filetype="pdf")))


def _accept_privacy(s):
    v = s.get(f"{API}/privacy-notice").json()["notice"].get("version")
    r = s.post(f"{API}/privacy-notice/accept", json={"version": v, "acknowledged": True})
    assert r.status_code == 200, r.text


def _answers():
    a = {k: f"We propose {k} stays predictable and child focused with written notice and shared information" for k in KEYS}
    a["wellness_tech__anchors"] = "Same bedtime of 9pm and family dinner in both homes"
    a["wellness_tech__phone"] = "Smartphone at age 13 paid by both parents equally"
    a["wellness_tech__concerns"] = CONCERN
    return a


# Config: 11 sections + wellness follow-ups
def test_config_eleven_sections():
    pro = new_user(API, "professional", "Cfg")
    cfg = pro.get(f"{API}/joint/config").json()
    assert len(cfg["agreement_areas"]) == 11
    assert [s["key"] for s in cfg["agreement_sections"]] == KEYS
    assert [s["num"] for s in cfg["agreement_sections"]] == list(range(1, 12))
    w = next(s for s in cfg["agreement_sections"] if s["key"] == "wellness_tech")
    assert w["num"] == 8 and [f["key"] for f in w["follow_ups"]] == WT_FU


# Public sample PDFs
def test_sample_pdfs():
    r = requests.get(f"{API}/joint/sample-agreement/pdf")
    assert r.status_code == 200
    t = _pdf_text(r.content)
    assert "IMPORTANT LEGAL NOTICE AND DISCLAIMER" in t and "Parent 1:" in t and "Parent 2:" in t and ACK in t
    assert "LEGAL NOTICE & DISCLAIMER:" not in t


@pytest.fixture(scope="module")
def agreement_case():
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
        _accept_privacy(s)
        assert s.post(f"{API}/joint/reports/{d['id']}/safety-screening/decline").status_code == 200
    return pro, pa, pb, d["id"]


# Agreement flow: missing wellness_tech -> 400, full -> 200, report & PDF
def test_missing_wellness_rejected(agreement_case):
    _pro, pa, _pb, rid = agreement_case
    a = _answers()
    a.pop("wellness_tech")
    r = pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": a})
    assert r.status_code == 400
    assert "Please answer the main question in every section" in r.text


def test_full_flow_report_and_pdf(agreement_case):
    pro, pa, pb, rid = agreement_case
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers()}).status_code == 200
    assert pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": _answers()}).status_code == 200
    rep = pro.get(f"{API}/joint/reports/{rid}/report", timeout=120)
    assert rep.status_code == 200, rep.text
    r = rep.json()
    assert [s["key"] for s in r["sections"]] == KEYS
    assert [s["num"] for s in r["sections"]] == list(range(1, 12))
    w = next(s for s in r["sections"] if s["key"] == "wellness_tech")
    print("WELLNESS SECTION:", w)
    assert w["label"] == "Wellness, Phones & Social Media" and w["specific_agreements"]
    assert w["communication_method"], "communication_method should come from wellness_tech__concerns"
    ln = r["legal_notice"]
    assert ln["heading"] == "IMPORTANT LEGAL NOTICE AND DISCLAIMER" and ln["subheading"] == "SA CoParents – Co-Parenting Agreement"
    assert len(ln["paragraphs"]) == 6 and ln["acknowledgment_heading"] == "Acknowledgment" and ln["acknowledgment"] == ACK
    assert ln["signature_labels"] == ["Parent 1", "Parent 2"]
    # parent can also view
    pr = pa.get(f"{API}/joint/reports/{rid}/report", timeout=60)
    assert pr.status_code == 200 and pr.json().get("legal_notice", {}).get("heading") == ln["heading"]
    pdf = pro.get(f"{API}/joint/reports/{rid}/pdf", timeout=120)
    assert pdf.status_code == 200
    t = _pdf_text(pdf.content)
    assert t.count("IMPORTANT LEGAL NOTICE AND DISCLAIMER") == 1 and "LEGAL NOTICE & DISCLAIMER:" not in t
    i = t.index("IMPORTANT LEGAL NOTICE AND DISCLAIMER")
    assert "Wellness, Phones & Social Media" in t and t.index("Wellness, Phones & Social Media") < i
    tail = t[i:]
    assert tail.index("Parent 2:") > tail.index("Parent 1:") > tail.index(ACK)
    print("PDF TAIL END:", t[-300:])


# Foundation editor API round-trip + PDF + share text
def test_foundation_roundtrip_pdf_and_share():
    pro, pa, _pb, d = new_case(API, subject="education")
    _accept_privacy(pa)
    fields = {"child_name": "TEST_Kid", "shared_purpose": "Raise a secure kid", "vision": "Happy and healthy", "priorities": "Stability\nSchool",
              "commitments": "Be on time", "parent_commitment": "I commit", "wellness_tech": "No phones in bedrooms after 9pm\nSmartphone at age 13\n\n  Shared parental controls  "}
    r = pa.put(f"{API}/foundation/mine", json={"fields": fields, "safety": {"q1": False, "q2": False, "q3": False}})
    assert r.status_code == 200, r.text
    g = pa.get(f"{API}/foundation/mine").json()
    assert g["statement"]["fields"]["wellness_tech"] == ["No phones in bedrooms after 9pm", "Smartphone at age 13", "Shared parental controls"]
    assert ["wellness_tech", "Wellness, Phones & Social Media"] in g["sections"]
    keys = [s[0] for s in g["sections"]]
    assert keys.index("concerns") < keys.index("wellness_tech") < keys.index("child_may_need")
    pdf = pa.get(f"{API}/foundation/mine/pdf")
    assert pdf.status_code == 200
    t = _pdf_text(pdf.content)
    assert "Wellness, Phones & Social Media" in t and "No phones in bedrooms after 9pm" in t and "Shared parental controls" in t
    # share into the case
    sq = [q["key"] for q in g["safety_questions"]]
    pa.put(f"{API}/foundation/mine", json={"fields": fields, "safety": {k: False for k in sq}})
    s = pa.post(f"{API}/joint/reports/{d['id']}/foundation/share")
    assert s.status_code == 200, s.text
    import pymongo
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    c = pymongo.MongoClient(os.environ["MONGO_URL"])
    doc = c[os.environ["DB_NAME"]].joint_reports.find_one({"id": d["id"]}, {"_id": 0, "responses": 1})
    c.close()
    content = doc["responses"]["a"]["foundation"][0]["content"]
    assert "Wellness, Phones & Social Media:" in content and "- Smartphone at age 13" in content


# Regression: joint (non-agreement) report PDF unchanged
def test_joint_report_pdf_regression():
    pro, pa, pb, d = new_case(API, subject="education")
    fill(API, pa, d["id"], "alpha")
    fill(API, pb, d["id"], "beta")
    pdf = pro.get(f"{API}/joint/reports/{d['id']}/pdf", timeout=120)
    assert pdf.status_code == 200
    t = _pdf_text(pdf.content)
    assert "IMPORTANT LEGAL NOTICE AND DISCLAIMER" not in t and "Acknowledgment" not in t
    rep = pro.get(f"{API}/joint/reports/{d['id']}/report", timeout=120).json()
    assert "legal_notice" not in rep or not rep.get("legal_notice")
