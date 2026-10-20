"""Part 3 (preview): safety-step wording, old-result hold + professional lift, Mediation Prep sharing privacy."""
import asyncio
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import case_safety as cs  # noqa: E402
from case_safety_routes import handle_signed  # noqa: E402

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
NOT_AVAILABLE = "This isn't available right now. Your Family check-in on SACOparentsAlign is the next step."
SEE, DONE = "Safety step: see SACOparentsAlign", "Safety step: completed on SACOparentsAlign"
SAFE_TXT, REFL_TXT, READY_TXT = "SAFETYSECRETXYZ", "REFLECTSECRETXYZ", "Needs Support"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails, _cases, _uids = [], [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    for c in ("safety_assessments", "portal_state", "prep_data", "summaries", "agreements", "share_tokens",
              "coparent_invites", "snc2_shares", "secure_documents", "align_links", "align_access_log"):
        db[c].delete_many({"$or": [{"user_id": {"$in": _uids}}, {"sender_user_id": {"$in": _uids}},
                                   {"user_pair": {"$in": _uids}}]})
    db[cs.COLL].delete_many({"case_id": {"$in": _cases}})
    db[cs.AUDIT].delete_many({"case_id": {"$in": _cases}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db.users.delete_many({"email": {"$in": _emails}})


def arun(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run(fn):
    async def main():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        try:
            return await fn(client[os.environ["DB_NAME"]])
        finally:
            client.close()
    return arun(main())


def user():
    email = f"test_part3_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Part Three", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    uid = db.users.find_one({"email": email})["user_id"]
    _uids.append(uid)
    return uid, {"Authorization": f"Bearer {r.json()['access_token']}"}, email


def old_result(uid, level=1):
    db.safety_assessments.insert_one({"assessment_id": f"sa_{uuid.uuid4().hex[:10]}", "user_id": uid, "answers": {"q1": "yes"},
                                      "created_at": datetime.now(timezone.utc).isoformat(), "result": {"level": level}})


def case_for(*uids, set_by="professional", done=False):
    cid = f"SA-TP3{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending",
                                         "parents": [{"parent_slot": s, "user_id": u} for s, u in zip("AB", uids)]})
    body = {"case_id": cid, "safety_mode": "standard", "set_by": set_by, "referral": "none", "screening_offered": done,
            "version": 1, "timestamp": int(time.time())}
    if set_by == "professional":
        body["professional_name"] = "Dr. Lift"
    assert run(lambda d: handle_signed(d, json.dumps(body).encode())) == {"ok": True}
    return cid


def pdf_text(b):
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)


# ---------- Safety-step wording: never "not started" ----------

def test_safety_step_two_states_only():
    assert cs.safety_step_text(True) == DONE and cs.safety_step_text(False) == SEE
    assert not hasattr(cs, "SAFETY_STEP_TODO")
    src = " ".join((ROOT / f).read_text() for f in ("portal_pdf.py", "court_checklist.py", "joint_professional_report.py",
                                                    "joint_professional_report_pdf.py", "case_safety.py"))
    assert "Safety step: not started" not in src


def test_unknown_and_known_safety_step_in_documents():
    a, ha, _ = user()
    r = httpx.post(f"{API}/portal/complete-report-pdf", headers=ha, json={}, timeout=60)
    t = pdf_text(r.content)
    assert SEE in t and "Safety step: not started" not in t
    case_for(a, done=True)
    t = pdf_text(httpx.post(f"{API}/portal/complete-report-pdf", headers=ha, json={}, timeout=60).content)
    assert DONE in t and SEE not in t


# ---------- Old-result hold: neutral, and a professional can lift it ----------

def test_hold_neutral_then_professional_lifts_it():
    a, ha, _ = user()
    b, hb, b_email = user()
    old_result(a, 1)
    gate = httpx.get(f"{API}/invites/coparent/gate", headers=ha, timeout=20).json()
    assert gate == {"clear": False, "code": "not_available", "message": NOT_AVAILABLE}
    r = httpx.post(f"{API}/snc2/compare/link", headers=ha, json={"email": b_email}, timeout=20)
    assert r.status_code == 403 and r.json()["detail"] == NOT_AVAILABLE
    # The co-parent starts a comparison: nothing they get hints at a reason.
    a_email = db.users.find_one({"user_id": a})["email"]
    r = httpx.post(f"{API}/snc2/compare/link", headers=hb, json={"email": a_email}, timeout=20)
    assert r.status_code == 200, r.text
    share_id = r.json()["share"]["share_id"]
    assert httpx.post(f"{API}/snc2/compare/{share_id}/consent", headers=ha, json={"consent": True}, timeout=20).status_code == 403
    seen_by_b = httpx.get(f"{API}/snc2/compare/me", headers=hb, timeout=20).text.lower()
    seen_by_b += httpx.get(f"{API}/invites/coparent/gate", headers=hb, timeout=20).text.lower()
    for w in ("safety", "level", "flag", "not_available", "isn't available", "red"):
        assert w not in seen_by_b.replace("shared", "").replace("required", ""), w
    from self_assessment_reminders import is_safety_flagged
    assert run(lambda d: is_safety_flagged(d, a)) is True
    # An Align update without a named professional keeps the hold.
    case_for(a, b, set_by="default")
    assert httpx.get(f"{API}/invites/coparent/gate", headers=ha, timeout=20).json()["clear"] is False
    # A named professional's case settings (signed, from SACOparentsAlign) lift it, and the change is logged.
    cid = case_for(a, b, set_by="professional")
    assert httpx.get(f"{API}/invites/coparent/gate", headers=ha, timeout=20).json() == {"clear": True, "code": "ok"}
    assert httpx.post(f"{API}/snc2/compare/{share_id}/consent", headers=ha, json={"consent": True}, timeout=20).status_code == 200
    assert run(lambda d: is_safety_flagged(d, a)) is False
    assert db[cs.AUDIT].find_one({"case_id": cid, "actor_type": "professional", "actor_id": "Dr. Lift", "action": "write"})


def test_automatic_update_can_not_lift():
    a, ha, _ = user()
    old_result(a, 2)
    cid = f"SA-TP3{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    db.joint_alignment_cases.insert_one({"case_id": cid, "parents": [{"parent_slot": "A", "user_id": a}]})
    raw = json.dumps({"case_id": cid, "safety_mode": "standard", "set_by": "auto_red", "referral": "none",
                      "screening_offered": False, "version": 1, "timestamp": int(time.time())}).encode()
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        run(lambda d: handle_signed(d, raw))
    assert httpx.get(f"{API}/invites/coparent/gate", headers=ha, timeout=20).json()["clear"] is False


# ---------- Mediation Prep: safety box ----------

def test_safety_box_ignored_and_old_text_kept_hidden():
    uid, h, _ = user()
    items = {"schedule_conflicts": "late pickups", "safety_concerns": "NEWTYPED"}
    assert httpx.put(f"{API}/mediation/issues", headers=h, json={"items": items}, timeout=20).status_code == 200
    saved = db.prep_data.find_one({"user_id": uid})["issues"]["items"]
    assert "safety_concerns" not in saved and saved["schedule_conflicts"] == "late pickups"
    db.prep_data.update_one({"user_id": uid}, {"$set": {"issues.items.safety_concerns": SAFE_TXT}})
    httpx.put(f"{API}/mediation/issues", headers=h, json={"items": {**items, "safety_concerns": "OVERWRITE"}}, timeout=20)
    assert db.prep_data.find_one({"user_id": uid})["issues"]["items"]["safety_concerns"] == SAFE_TXT
    assert SAFE_TXT not in httpx.get(f"{API}/mediation/prep", headers=h, timeout=20).text


# ---------- Mediation Prep: AI prompts ----------

def test_document_ai_prompts_never_get_safety_text_or_reflection(monkeypatch):
    import ai_service
    sent = []

    class Chat:
        async def send_message(self, m):
            sent.append(m.text)
            return "{}"
    monkeypatch.setattr(ai_service, "_make_chat", lambda *a, **k: Chat())
    prep = {"child_goals": {"focus": "stability"}, "issues": {"items": {"safety_concerns": SAFE_TXT, "schedule_conflicts": "x"}},
            "reflection": {"child_lens": REFL_TXT}, "priority": {"issue": "school"}}
    prev = {"prep_snapshot": prep, "executive_summary": "e"}
    arun(ai_service.generate_summary(prep, "P", previous=prev))
    arun(ai_service.generate_agreement_draft(prep, "P", previous=prev))
    joined = "\n".join(sent)
    assert len(sent) == 2 and SAFE_TXT not in joined and REFL_TXT not in joined and "stability" in joined


# ---------- Mediation Prep: shared copies ----------

def _summary(uid, clean, **extra):
    sid = f"sum_{uuid.uuid4().hex[:12]}"
    db.summaries.insert_one({"summary_id": sid, "user_id": uid, "generated_at": datetime.now(timezone.utc).isoformat(),
                             "readiness_score": 41, "readiness_label": READY_TXT, "readiness_narrative": "READYNARR",
                             "executive_summary": "EXECTEXT", "top_concerns": ["CONCERNTEXT"],
                             "priority_agenda": [{"rank": 1, "topic": "AGENDATOPIC", "category": "urgent"}],
                             "prep_snapshot": {"issues": {"items": {"safety_concerns": SAFE_TXT}}},
                             **({"clean_inputs": True} if clean else {}), **extra})
    return sid


def test_new_share_link_never_has_readiness():
    uid, h, _ = user()
    sid = _summary(uid, True)
    r = httpx.post(f"{API}/mediation/summary/{sid}/share-link", headers=h, json={}, timeout=30)
    assert r.status_code == 200, r.text
    token = r.json()["url"].rstrip("/").split("/")[-1] if "url" in r.json() else r.json()["token"]
    pdf = httpx.get(f"{API}/mediation/shared/{token}", timeout=60)
    assert pdf.status_code == 200, pdf.text[:200]
    t = pdf_text(pdf.content)
    assert "AGENDATOPIC" in t and "CONCERNTEXT" in t
    for w in (READY_TXT, "41/100", "READYNARR", SAFE_TXT):
        assert w not in t, w


def test_old_doc_share_falls_back_to_goals_and_agenda_and_old_links_stop():
    uid, h, _ = user()
    sid = _summary(uid, False)
    r = httpx.post(f"{API}/mediation/summary/{sid}/share-link", headers=h, json={}, timeout=30).json()
    token = r.get("token") or r["url"].rstrip("/").split("/")[-1]
    t = pdf_text(httpx.get(f"{API}/mediation/shared/{token}", timeout=60).content)
    assert "AGENDATOPIC" in t and "EXECTEXT" not in t and "CONCERNTEXT" not in t and READY_TXT not in t
    from auth import create_share_token
    old = create_share_token("summary", sid, uid)
    r = httpx.get(f"{API}/mediation/shared/{old}", timeout=30)
    assert r.status_code == 410 and "privacy update" in r.json()["detail"]


def test_old_doc_rewrite_uses_clean_inputs(monkeypatch):
    import mediation_sharing
    seen = {}

    async def fake(snap, name):
        seen["snap"] = snap
        return {"executive_summary": "REWRITTEN", "readiness_label": READY_TXT, "priority_agenda": []}
    monkeypatch.setattr(mediation_sharing.ai_service, "generate_summary", fake)
    uid, _, _ = user()
    sid = _summary(uid, False, prep_snapshot={"issues": {"items": {"safety_concerns": SAFE_TXT}}, "reflection": {"x": REFL_TXT},
                                              "readiness": {"answers": {}}, "child_goals": {"focus": "f"}})
    doc = db.summaries.find_one({"summary_id": sid}, {"_id": 0})

    class U:
        ai_notice_current, name = True, "P"
    run(lambda d: mediation_sharing.prepare(d, "summary", doc, U))
    blob = json.dumps(seen["snap"])
    assert SAFE_TXT not in blob and REFL_TXT not in blob and "readiness" not in seen["snap"]
    view, _ = mediation_sharing.shared_view("summary", doc, None)
    assert view["executive_summary"] == "REWRITTEN" and "readiness_label" not in view


def test_mediator_email_gets_shared_copy(monkeypatch):
    import email_service
    import mediation_routes
    from models import UserPublic
    got = {}
    monkeypatch.setattr(email_service, "send_mediator_email", lambda **kw: got.update(kw))
    uid, _, email = user()
    sid = _summary(uid, True)
    cur = UserPublic(user_id=uid, email=email, name="Part Three", created_at="2026-01-01")

    async def go(d):
        class Req:
            class app:
                class state:
                    pass
        Req.app.state.db = d
        body = mediation_routes.MediatorEmailRequest(mediator_email="mediator@example.com", summary_id=sid)
        return await mediation_routes.email_mediator(body, Req, cur)
    run(go)
    t = pdf_text(got["attachments"][0][1])
    assert "AGENDATOPIC" in t and READY_TXT not in t and "41/100" not in t


def test_agreement_seen_by_others_is_the_shared_copy():
    import mediation_sharing
    old = {"agreement_id": "agr_x", "generated_at": "g", "shared_goals": ["G"], "priority_items": ["P"], "communication": ["COMMSECRET"],
           "readiness": {"overall": 40}, "prep_snapshot": {"issues": {"items": {"safety_concerns": SAFE_TXT}}}}
    v = mediation_sharing.shared_agreement(old)
    assert v == {"agreement_id": "agr_x", "generated_at": "g", "shared_goals": ["G"], "priority_items": ["P"]}
    v = mediation_sharing.shared_agreement({**old, "clean_inputs": True})
    assert v["communication"] == ["COMMSECRET"] and "readiness" not in v and "prep_snapshot" not in v


def test_complete_report_uses_shared_agreement():
    uid, h, _ = user()
    db.agreements.insert_one({"agreement_id": f"agr_{uuid.uuid4().hex[:10]}", "user_id": uid, "overview": "OVERVIEWSECRET",
                              "generated_at": datetime.now(timezone.utc).isoformat(), "shared_goals": ["SHAREDGOALX"],
                              "communication": ["COMMSECRET"], "closing_note": "CLOSINGSECRET"})
    t = pdf_text(httpx.post(f"{API}/portal/complete-report-pdf", headers=h, json={}, timeout=60).content)
    assert "SHAREDGOALX" in t and "COMMSECRET" not in t and "OVERVIEWSECRET" not in t and "CLOSINGSECRET" not in t


def test_own_lists_hide_snapshots():
    uid, h, _ = user()
    _summary(uid, True)
    body = httpx.get(f"{API}/mediation/summaries", headers=h, timeout=20).text
    assert SAFE_TXT not in body and "prep_snapshot" not in body and READY_TXT in body  # the parent's own view keeps readiness


def test_pre_update_secure_doc_link_stops():
    from secure_docs import hash_value
    uid, _, _ = user()
    tok = uuid.uuid4().hex
    db.secure_documents.insert_one({"doc_id": uuid.uuid4().hex, "token_hash": hash_value(tok), "sender_user_id": uid,
                                    "recipient_email": "m@example.com", "sender_name": "P", "label": "x",
                                    "files": [{"name": "mediation_summary_sum_abc.pdf", "size": 1}],
                                    "created_at": datetime.now(timezone.utc).isoformat(), "expires_at": "2099-01-01T00:00:00+00:00"})
    r = httpx.get(f"{API}/secure-docs/open/{tok}", timeout=20)
    assert r.status_code == 410 and "privacy update" in r.json()["detail"]
    assert db.secure_documents.find_one({"token_hash": hash_value(tok)})  # kept in storage


# ---------- Align no longer receives reflection or readiness ----------

def test_align_payloads_have_no_reflection_or_readiness():
    import integration_routes as ir
    import joint_alignment_routes as jar
    uid, _, email = user()
    db.prep_data.update_one({"user_id": uid}, {"$set": {"reflection": {"child_lens": REFL_TXT, "own_part": REFL_TXT},
                                                        "readiness": {"score": 77, "reflection": "READYREF"},
                                                        "issues": {"items": {"safety_concerns": SAFE_TXT}, "notes": "n"}}}, upsert=True)
    db[ir._LINKS].insert_one({"user_id": uid, "unlinked_at": None, "linked_at": datetime.now(timezone.utc).isoformat()})
    orig = ir._verify_integration_key
    ir._verify_integration_key = lambda _h: None
    try:
        out = run(lambda d: ir.export_assessments(email=email, x_integration_key="x", db=d))
    finally:
        ir._verify_integration_key = orig
    blob = json.dumps(out, default=str)
    assert REFL_TXT not in blob and "READYREF" not in blob and SAFE_TXT not in blob
    src = (ROOT / "joint_alignment_routes.py").read_text()
    assert '"readiness": _pick_prep' not in src and jar is not None
