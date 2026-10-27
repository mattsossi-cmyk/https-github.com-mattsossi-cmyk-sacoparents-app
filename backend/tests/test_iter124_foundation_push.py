"""Owner 2026-10-27: parent app pushes Mother's/Father's Foundation Statements to POST /integrations/case-update (status "foundation").
Stored against the invitation's parent + case only; private to that parent until they include it; one parent can never send or overwrite the other's."""
import json
import os
import sys

import pymupdf
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(__file__))
from casekit import new_user  # noqa: E402

API = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
ENV = dotenv_values("/app/backend/.env")
KEY = ENV["INTEGRATION_SHARED_SECRET"]
MONGO = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]
KEYS = ["foundation", "transitions", "communication", "education", "medical", "psychological", "activities", "wellness_tech", "decisions", "differences", "review"]
MOTHER = "MOTHER-STATEMENT-7f3a: I want our child to feel safe in both homes."
FATHER = "FATHER-STATEMENT-9c1d: I want our child to know both parents show up."


def _push(body, key=KEY):
    return requests.post(f"{API}/integrations/case-update", headers={"X-Integration-Key": key}, json=body, timeout=20)


def _agreement_case(submit: bool = True):
    pro = new_user(API, "professional", "Push Pro")
    emails = {"a": f"t_m_{os.urandom(3).hex()}@example.com", "b": f"t_f_{os.urandom(3).hex()}@example.com"}
    d = pro.post(f"{API}/joint/agreements", json={"child_name": "Avery", "parent_a_name": "Mother", "parent_a_email": emails["a"],
                                                   "parent_b_name": "Father", "parent_b_email": emails["b"]}).json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    parents = {}
    for role in ("a", "b"):
        s = new_user(API, "parent", f"Parent {role.upper()}", email=emails[role], invite=toks[role])
        assert s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]}).json().get("ok")
        assert s.post(f"{API}/joint/reports/{d['id']}/safety-screening/decline").status_code == 200
        if submit:
            assert s.put(f"{API}/joint/reports/{d['id']}/responses", json={"answers": {k: f"{role} proposal for {k}" for k in KEYS}}).status_code == 200
        parents[role] = s
    return pro, parents["a"], parents["b"], d["id"], toks


def _imports(rid):
    return MONGO.joint_reports.find_one({"id": rid}, {"foundation_imports": 1, "responses": 1}) or {}


def test_auth_and_validation():
    _pro, _pa, _pb, rid, toks = _agreement_case(submit=False)
    assert _push({"token": toks["a"], "status": "foundation", "foundation_statement": {"content": MOTHER}}, key="nope").status_code == 401
    assert _push({"token": "not-a-token", "status": "foundation", "foundation_statement": {"content": MOTHER}}).status_code == 404
    assert _push({"token": toks["a"], "status": "foundation"}).status_code == 400
    assert _push({"token": toks["a"], "status": "foundation", "foundation_statement": {"content": "   ", "fields": {"child_name": "Avery"}}}).status_code == 400
    assert _push({"token": toks["a"], "status": "bogus"}).status_code == 400
    assert "foundation_imports" not in _imports(rid)


def test_stored_against_invitation_parent_never_request_fields():
    _pro, pa, pb, rid, toks = _agreement_case(submit=False)
    # Token = Mother (role a). Body lies and says it is the Father's — the lie is ignored, nothing lands on side b.
    r = _push({"token": toks["a"], "status": "foundation", "parent": "b", "role": "b", "parent_email": pb.email, "author": "Father",
               "foundation_statement": {"completed_at": "2026-10-26T10:00:00Z", "title": "Mother's Foundation Statement", "content": MOTHER,
                                        "fields": {"wellness_tech": ["Same bedtime in both homes"], "priorities": ["Safety first"], "ssn": "000-00-0000", "role": "b"}}})
    assert r.status_code == 200, r.text
    imp = _imports(rid)["foundation_imports"]
    assert set(imp) == {"a"}
    a = imp["a"]
    assert a["content"] == MOTHER and a["title"] == "Mother's Foundation Statement" and a["completed_at"] == "2026-10-26" and a["source"] == "sacoparentsapp.online"
    assert a["structured"]["wellness_tech"] == ["Same bedtime in both homes"] and "ssn" not in a["structured"] and "role" not in a["structured"]
    assert a["invitation_id"] == MONGO.invitations.find_one({"report_id": rid, "role": "a"})["id"]
    # Father's own push lands on b; Mother's untouched. A second Mother push overwrites only a.
    assert _push({"token": toks["b"], "status": "foundation", "foundation_statement": {"content": FATHER}}).status_code == 200
    imp = _imports(rid)["foundation_imports"]
    assert imp["a"]["content"] == MOTHER and imp["b"]["content"] == FATHER
    assert _push({"token": toks["a"], "foundation_statement": {"content": MOTHER + " (revised)"}}).status_code == 200  # status omitted → inferred
    imp = _imports(rid)["foundation_imports"]
    assert imp["a"]["content"].endswith("(revised)") and imp["b"]["content"] == FATHER
    # Oversize content is truncated, never rejected; the write is audited without content.
    assert _push({"token": toks["b"], "status": "foundation", "foundation_statement": {"content": "x" * 9000}}).status_code == 200
    assert len(_imports(rid)["foundation_imports"]["b"]["content"]) == 5000
    ev = MONGO.access_events.find_one({"report_id": rid, "kind": "integration_write", "role": "a"})
    assert ev and ev["fields"] == ["foundation_imports"] and MOTHER not in json.dumps(ev, default=str)
    # Nothing was shared into the case by the push itself.
    assert not (_imports(rid).get("responses") or {}).get("a", {}).get("foundation")


def test_private_until_parent_includes_then_visible_to_case():
    pro, pa, pb, rid, toks = _agreement_case(submit=True)
    assert _push({"token": toks["a"], "status": "foundation", "foundation_statement": {"content": MOTHER}}).status_code == 200
    assert _push({"token": toks["b"], "status": "foundation", "foundation_statement": {"content": FATHER}}).status_code == 200
    # Before inclusion: professional sees nothing; each parent sees only their own; report/PDF carry neither.
    pro_view = pro.get(f"{API}/joint/reports/{rid}").json()
    assert pro_view.get("foundation_statements") == [] and "my_foundation_import" not in pro_view and MOTHER not in json.dumps(pro_view) and FATHER not in json.dumps(pro_view)
    a_view, b_view = pa.get(f"{API}/joint/reports/{rid}").json(), pb.get(f"{API}/joint/reports/{rid}").json()
    assert a_view["my_foundation_import"]["content"] == MOTHER and a_view["my_foundation_import"]["included"] is False and FATHER not in json.dumps(a_view)
    assert b_view["my_foundation_import"]["content"] == FATHER and MOTHER not in json.dumps(b_view)
    rep = pro.get(f"{API}/joint/reports/{rid}/report").json()
    assert rep["foundation_statements"] == []
    pdf = pro.get(f"{API}/joint/reports/{rid}/pdf")
    assert pdf.status_code == 200
    text = " ".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "MOTHER-STATEMENT" not in text and "FATHER-STATEMENT" not in text
    # Father cannot include Mother's statement: the endpoint only ever touches the caller's own side.
    assert pb.post(f"{API}/joint/reports/{rid}/foundation/use-import").status_code == 200
    resp = _imports(rid)["responses"]
    assert resp["b"]["foundation"][0]["content"] == FATHER and resp["b"]["foundation"][0]["source"] == "sacoparentsapp.online" and not resp["a"].get("foundation")
    # Professional cannot call it at all; a stranger gets 404 (cannot see the case).
    assert pro.post(f"{API}/joint/reports/{rid}/foundation/use-import").status_code == 403
    stranger = new_user(API, "professional", "Stranger Pro")  # not on the case → cannot see it
    assert stranger.post(f"{API}/joint/reports/{rid}/foundation/use-import").status_code in (403, 404)
    # After Father included his: professional + the agreement show FATHER only; Mother still private.
    pro_view = pro.get(f"{API}/joint/reports/{rid}").json()
    assert [s["content"] for s in pro_view["foundation_statements"]] == [FATHER] and pro_view["foundation_statements"][0]["side"] == "b"
    rep = pro.get(f"{API}/joint/reports/{rid}/report").json()
    assert [f["content"] for f in rep["foundation_statements"]] == [FATHER]
    a_rep = pa.get(f"{API}/joint/reports/{rid}/report").json()  # the OTHER parent now sees Father's included statement in the agreement — by design, and disclosed
    assert FATHER in json.dumps(a_rep) and MOTHER not in json.dumps(a_rep)
    assert pb.get(f"{API}/joint/reports/{rid}").json()["my_foundation_import"]["included"] is True


def test_use_import_requires_statement_and_respects_safety_flag():
    _pro, pa, pb, rid, toks = _agreement_case(submit=False)
    assert pa.post(f"{API}/joint/reports/{rid}/foundation/use-import").status_code == 404  # nothing on file for Mother
    assert _push({"token": toks["a"], "status": "foundation", "foundation_statement": {"content": MOTHER}}).status_code == 200
    MONGO.joint_reports.update_one({"id": rid}, {"$set": {"safety_flags.a": True}})
    assert pa.post(f"{API}/joint/reports/{rid}/foundation/use-import").status_code == 409  # safety pathway: not routed into a joint document
    MONGO.joint_reports.update_one({"id": rid}, {"$unset": {"safety_flags": ""}})
    # Agreement form path: {"use_import": true} makes the server copy the stored statement; client text is ignored.
    r = pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {k: f"a proposal for {k}" for k in KEYS}, "foundation": [{"use_import": True, "content": "CLIENT-SUPPLIED-TEXT"}]})
    assert r.status_code == 200, r.text
    fa = _imports(rid)["responses"]["a"]["foundation"]
    assert len(fa) == 1 and fa[0]["content"] == MOTHER and fa[0]["source"] == "sacoparentsapp.online"
    # Father with no statement on file asking to use one → 404, and his answers are NOT saved.
    r = pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {k: f"b proposal for {k}" for k in KEYS}, "foundation": [{"use_import": True}]})
    assert r.status_code == 404 and not (_imports(rid)["responses"].get("b"))
