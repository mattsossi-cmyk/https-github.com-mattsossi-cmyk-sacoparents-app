"""Align safety step replaces the old in-app Safety Assessment (preview). Runs with the webhook OFF:
the Family check-in status is set through the signed-body handler directly, after the signature step."""
import asyncio
import io
import json
import re
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
DONE, TODO = "Safety step: completed on SACOparentsAlign", "Safety step: see SACOparentsAlign"
BANNED = ("flagged for safety", "safety screen", "safety assessment", "level 1", "finding 3", "trauma", "redacted")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails, _cases, _uids = [], [], []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    for c in ("safety_assessments", "portal_state", "grey_rock_audit", "align_links", "align_access_log", "portal_pdf_shares",
              "prep_data", "coparent_invites"):
        db[c].delete_many({"user_id": {"$in": _uids}})
    db[cs.COLL].delete_many({"case_id": {"$in": _cases}})
    db[cs.AUDIT].delete_many({"case_id": {"$in": _cases}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db.users.delete_many({"email": {"$in": _emails}})


def run(fn):
    async def main():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        try:
            return await fn(client[os.environ["DB_NAME"]])
        finally:
            client.close()
    return arun(main())


def arun(coro):
    # A private loop, so later test files that use the main-thread loop still work.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def user():
    email = f"test_alignstep_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "Step Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    uid = db.users.find_one({"email": email})["user_id"]
    _uids.append(uid)
    return uid, {"Authorization": f"Bearer {r.json()['access_token']}"}, email


def save_old_result(uid, level):
    aid = f"sa_{uuid.uuid4().hex[:10]}"
    db.safety_assessments.insert_one({"assessment_id": aid, "user_id": uid, "created_at": datetime.now(timezone.utc).isoformat(),
                                      "answers": {"q1": "yes"}, "result": {"level": level, "pathway_title": "No Direct Communication"},
                                      "ai_summaries": {"overall": "saved summary"}})
    return aid


def case_with(*uids, checkin_done):
    cid = f"SA-TSTEP{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending",
                                         "parents": [{"parent_slot": s, "user_id": u} for s, u in zip("AB", uids)]})
    raw = json.dumps({"case_id": cid, "safety_mode": "standard", "set_by": "professional", "professional_name": "Dr. Reviewer",
                      "referral": "none", "screening_offered": checkin_done, "version": 1, "timestamp": int(time.time())}).encode()
    assert run(lambda d: handle_signed(d, raw)) == {"ok": True}
    return cid


def text(pdf_bytes):
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages)


# ---------- 1. Old assessment hidden; saved answers kept ----------

def test_old_assessment_routes_are_gone_and_saved_answers_stay():
    uid, h, _ = user()
    aid = save_old_result(uid, 1)
    for method, path in [("get", "/safety-assessment/questions"), ("get", "/safety-assessment/me"),
                         ("get", "/safety-assessment/me/history"), ("post", "/safety-assessment"),
                         ("get", f"/safety-assessment/{aid}/pdf"), ("get", f"/safety-assessment/{aid}/court-report"),
                         ("get", f"/safety-assessment/{aid}/one-pager"), ("post", f"/safety-assessment/{aid}/regenerate-summaries"),
                         ("post", f"/safety-assessment/{aid}/share-link"), ("get", "/safety-assessment/shared/abc.def"),
                         ("post", f"/safety-assessment/{aid}/email"), ("post", f"/safety-assessment/{aid}/email-mediator"),
                         ("post", f"/safety-assessment/{aid}/prepare-cosign"),
                         ("get", "/verify/court-report/abcdef1234567890")]:
        r = getattr(httpx, method)(f"{API}{path}", headers=h, timeout=20, **({"json": {}} if method == "post" else {}))
        assert r.status_code in (404, 405), (path, r.status_code)
    assert httpx.get(f"{API}/safety-assessment/problem-solving/me", headers=h, timeout=20).status_code in (200, 404)
    doc = db.safety_assessments.find_one({"assessment_id": aid})
    assert doc and doc["answers"] == {"q1": "yes"} and doc["ai_summaries"]
    exp = httpx.get(f"{API}/me/export", headers=h, timeout=30).json()
    assert [d["assessment_id"] for d in exp["collections"]["safety_assessments"]] == [aid]


def test_ai_never_gets_old_answers():
    _, h, _ = user()
    from ai_notice import AI_NOTICE_VERSION
    ack = httpx.post(f"{API}/ai-notice/ack", headers=h, json={"ai_notice_version": AI_NOTICE_VERSION,
                                                              "ai_notice_ack_at": datetime.now(timezone.utc).isoformat()}, timeout=20)
    assert ack.status_code == 200, ack.text
    r = httpx.post(f"{API}/mediation/section-coaching", headers=h, json={"section": "safety", "data": {"level": 1}}, timeout=20)
    assert r.status_code == 400, r.text
    import self_assessment_ai

    uid, _, _ = user()
    save_old_result(uid, 1)

    class Req:
        class app:
            class state:
                db = None

    class U:
        user_id = uid
    assert arun(self_assessment_ai._grey_rock(Req, U, False)) is False
    assert arun(self_assessment_ai._grey_rock(Req, U, True)) is True


# ---------- 2. Protections kept, neutral wording ----------

def test_no_old_result_is_never_blocked():
    _, h, _ = user()
    assert httpx.get(f"{API}/invites/coparent/gate", headers=h, timeout=20).json() == {"clear": True, "code": "ok"}


def test_saved_concerning_result_blocks_invite_with_neutral_note():
    uid, h, _ = user()
    save_old_result(uid, 1)
    gate = httpx.get(f"{API}/invites/coparent/gate", headers=h, timeout=20).json()
    assert gate == {"clear": False, "code": "not_available", "message": NOT_AVAILABLE}
    r = httpx.post(f"{API}/invites/coparent", headers=h, json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"}, timeout=20)
    assert r.status_code == 403 and r.json()["detail"] == {"code": "not_available", "message": NOT_AVAILABLE}
    r = httpx.post(f"{API}/link-codes", headers=h, json={"context": "account"}, timeout=20)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "not_available"
    low = json.dumps(gate).lower() + r.text.lower()
    assert "level" not in low and "hotline" not in low and "safety" not in low


def test_level_three_is_not_blocked():
    uid, h, _ = user()
    save_old_result(uid, 3)
    assert httpx.get(f"{API}/invites/coparent/gate", headers=h, timeout=20).json()["clear"] is True


def test_comparison_blocked_neutral_and_reminders_still_skipped():
    uid, h, _ = user()
    save_old_result(uid, 2)
    d = httpx.get(f"{API}/court-path/compare", headers=h, timeout=20).json()
    assert d["state"] == "not_available"
    d = httpx.post(f"{API}/court-path/compare/share", headers=h, json={"shared": True}, timeout=20).json()
    assert d["state"] == "not_available" and d["shared"] is False
    from self_assessment_reminders import is_safety_flagged
    assert run(lambda d: is_safety_flagged(d, uid)) is True
    quick, _, _ = user()
    db.portal_state.update_one({"user_id": quick}, {"$set": {"safety_ack": {"flagged": True}}}, upsert=True)
    assert run(lambda d: is_safety_flagged(d, quick)) is True
    clear, _, _ = user()
    assert run(lambda d: is_safety_flagged(d, clear)) is False


def test_compare_messages_are_neutral():
    for f in ("deep_dive_compare_router_factory.py", "snc2_comparison_routes.py"):
        src = (ROOT / f).read_text()
        assert "limited-contact" not in src and "Safety Screen recommends" not in src, f


def test_align_export_holds_back_like_nothing_saved_and_no_flag():
    import integration_routes as ir
    ir_verify = ir._verify_integration_key
    ir._verify_integration_key = lambda _h: None
    try:
        held, _, held_email = user()
        empty, _, empty_email = user()
        save_old_result(held, 1)
        db.prep_data.update_one({"user_id": held}, {"$set": {"user_id": held, "reflection": {"child_lens": "private words"},
                                                            "child_goals": {"focus": "school"}}}, upsert=True)
        for u, e in ((held, held_email), (empty, empty_email)):
            db.align_links.insert_one({"user_id": u, "email": e, "linked_at": datetime.now(timezone.utc), "unlinked_at": None})
        a = run(lambda d: ir.export_assessments(email=held_email, x_integration_key=None, db=d))
        b = run(lambda d: ir.export_assessments(email=empty_email, x_integration_key=None, db=d))
        assert "redacted_for_safety" not in a
        strip = lambda x: {k: v for k, v in x.items() if k not in ("parent", "exported_at")}  # noqa: E731
        assert strip(a) == strip(b)
        with pytest.raises(Exception) as e:
            run(lambda d: ir.integrations_foundation_statement_pdf(email=held_email, x_integration_key=None, db=d))
        assert getattr(e.value, "status_code", None) == 409
    finally:
        ir._verify_integration_key = ir_verify


def test_grey_rock_timeline_drops_safety_screen_rows():
    import cp_progress_extras
    uid, _, _ = user()
    now = datetime.now(timezone.utc).isoformat()
    db.grey_rock_audit.insert_many([{"user_id": uid, "event": "on", "source": "safety_screen", "at": now},
                                    {"user_id": uid, "event": "on", "source": "toggle_chip", "at": now}])
    rows = run(lambda d: cp_progress_extras.load_grey_rock_timeline(d, uid))
    assert [r["source"] for r in rows] == ["Grey-Rock chip"]


# ---------- 3. Documents carry only the safety-step line ----------

def test_complete_report_shows_only_the_step_line():
    uid, h, _ = user()
    save_old_result(uid, 1)
    body = {"safety_ack": {"cleared": False, "flagged": True, "date": "2026-10-01"}, "author_name": "Step Test"}
    r = httpx.post(f"{API}/portal/complete-report-pdf", headers=h, json=body, timeout=30)
    assert r.status_code == 200, r.text
    t = text(r.content)
    assert TODO in t and DONE not in t
    assert not any(w in t.lower() for w in BANNED), t
    case_with(uid, checkin_done=True)
    t = text(httpx.post(f"{API}/portal/complete-report-pdf", headers=h, json=body, timeout=30).content)
    assert DONE in t and TODO not in t


def test_shared_complete_report_link_drops_old_flag():
    uid, h, _ = user()
    payload = {"safety_ack": {"cleared": False, "flagged": True}, "author_name": "Step Test"}
    r = httpx.post(f"{API}/portal/share", headers=h, json={"artefact_type": "complete", "payload": payload}, timeout=30)
    assert r.status_code == 200, r.text
    sid = r.json()["share_id"]
    assert "safety_ack" not in db.portal_pdf_shares.find_one({"share_id": sid})["payload"]
    db.portal_pdf_shares.update_one({"share_id": sid}, {"$set": {"payload.safety_ack": payload["safety_ack"]}})
    t = text(httpx.get(f"{API}/portal/share/{sid}.pdf", timeout=30).content)
    assert TODO in t and "flagged" not in t.lower()


def test_court_checklist_pdf_step_line():
    uid, h, _ = user()
    t = text(httpx.post(f"{API}/court-path/checklist/pdf", headers=h, json={}, timeout=30).content)
    assert TODO in t and "safety check" not in t.lower()
    case_with(uid, checkin_done=True)
    t = text(httpx.post(f"{API}/court-path/checklist/pdf", headers=h, json={}, timeout=30).content)
    assert DONE in t


def test_joint_report_step_line_and_no_lens():
    from joint_professional_report import build_joint_report
    from joint_professional_report_pdf import build_joint_report_pdf
    empty = {"shared_pathways": [], "steps": [], "highlights": [],
             "summary": {"total_items": 0, "aligned_pct": 0, "divergent_pct": 0, "counts": {}}}
    p = build_joint_report(parent_a_name="A", parent_b_name="B", share_id="s", comparison=empty, prep_a={}, prep_b={},
                           safety_step=DONE)
    assert p["safety_step"] == DONE and "safety_privacy_note" not in p
    t = text(build_joint_report_pdf(p))
    assert DONE in t and "finding 3" not in t.lower()
    a, _, _ = user()
    b, _, _ = user()
    assert run(lambda d: cs.safety_step_line(d, a, b)) == TODO
    case_with(a, b, checkin_done=True)
    assert run(lambda d: cs.safety_step_line(d, a, b)) == DONE


def test_mediator_and_report_emails_have_no_lens_text():
    src = (ROOT / "email_service.py").read_text()
    assert "Finding 3" not in src and "Trauma-Informed Safety" not in src


def test_snc2_report_never_reads_old_level():
    import snc2_routes
    uid, _, _ = user()
    save_old_result(uid, 1)
    assert run(lambda d: snc2_routes._latest_safety_level(d, uid)) is None


# ---------- 4. Old links, next steps, readiness and notice ----------

def test_old_safety_next_steps_are_gone():
    uid, h, _ = user()
    db.next_steps.insert_one({"user_id": uid, "assessment": "safety", "steps": [{"what": "Share your safety report"}]})
    try:
        assert httpx.get(f"{API}/next-steps/safety", headers=h, timeout=20).status_code == 404
        r = httpx.get(f"{API}/next-steps/readiness", headers=h, timeout=20)
        assert r.status_code == 200 and "Safety pathway" not in r.text and "Family Violence" not in r.text
    finally:
        db.next_steps.delete_many({"user_id": uid})


def test_old_assessment_share_links_not_listed():
    uid, h, _ = user()
    db.share_tokens.insert_many([
        {"jti": uuid.uuid4().hex, "user_id": uid, "doc_type": "safety", "doc_id": "sa_x", "created_at": datetime.now(timezone.utc).isoformat()},
        {"jti": uuid.uuid4().hex, "user_id": uid, "doc_type": "cp_report", "doc_id": "cp_x", "created_at": datetime.now(timezone.utc).isoformat()},
    ])
    try:
        d = httpx.get(f"{API}/share/mine", headers=h, timeout=20).json()
        types = [r.get("doc_type") for r in d["active"] + d["past"]]
        assert "safety" not in types and "cp_report" in types
    finally:
        db.share_tokens.delete_many({"user_id": uid})


def test_old_emailed_safety_pdfs_no_longer_open():
    from secure_docs import hash_value
    uid, h, _ = user()
    now = datetime.now(timezone.utc)
    later = now.replace(year=now.year + 1).isoformat()
    tokens = {name: uuid.uuid4().hex for name in ("sacoparents-safety-assessment-level-1.pdf", "safety-assessment.pdf",
                                                  "joint-report.pdf")}
    for name, tok in tokens.items():
        db.secure_documents.insert_one({"doc_id": uuid.uuid4().hex, "token_hash": hash_value(tok), "recipient_email": "pro@example.com",
                                        "sender_user_id": uid, "sender_name": "Step Test", "label": name,
                                        "files": [{"name": name, "file_id": None, "size": 1}], "created_at": now.isoformat(),
                                        "expires_at": later, "revoked_at": None, "opened_at": None, "code_hash": None,
                                        "code_expires_at": None, "code_attempts": 0, "code_sends": []})
    try:
        for name, tok in tokens.items():
            r = httpx.get(f"{API}/secure-docs/open/{tok}", timeout=20)
            if "safety" in name:
                assert r.status_code == 404 and r.json()["detail"] == "This link isn't valid.", name
            else:
                assert r.status_code == 200, r.text
        sent = [d["label"] for d in httpx.get(f"{API}/secure-docs/sent", headers=h, timeout=20).json()]
        assert sent == ["joint-report.pdf"]
        assert db.secure_documents.count_documents({"sender_user_id": uid}) == 3
    finally:
        db.secure_documents.delete_many({"sender_user_id": uid})


def test_readiness_profile_ignores_old_safety_data():
    from readiness_scoring import compute_readiness
    prep = {"readiness": {"cooperation": 5, "hope_agreement": 5}}
    plain = compute_readiness(prep)
    with_old = compute_readiness({**prep, "safety_assessment": {"high_risk": True, "moderate_concern": True}})
    assert json.dumps(plain, sort_keys=True) == json.dumps(with_old, sort_keys=True)
    low = json.dumps(with_old).lower()
    assert "finding 3" not in low and "trauma-informed" not in low and "safety concerns identified" not in low


def test_ai_prompts_have_no_safety_section_and_intro_has_no_lens():
    import ai_service
    import professional_intro_transcript as pit
    assert "Safety Assessment pathway" not in (ROOT / "ai_service.py").read_text()
    assert "Finding 3" not in json.dumps([list(x) for x in pit.__dict__.values() if isinstance(x, (list, tuple))], default=str)
    assert ai_service is not None


def test_privacy_notice_short_true_text():
    from privacy_consent import PRIVACY_NOTICE_VERSION
    fe = ROOT.parent / "frontend/src"
    notice = (fe / "components/privacy/ProfessionalAccessNotice.jsx").read_text()
    page = " ".join((fe / "pages/privacyNotice/PrivacyNoticeContent.jsx").read_text().split())
    for s in ("Safety questions are answered privately on SACOparentsAlign, not in this app.",
              "On SACOparentsAlign, your co-parent never sees your answers. The professionals assigned to your case and a small number of "
              "SA CoParents administrators can, and every view is recorded.",
              "Nothing about your answers appears in this app&apos;s reports or documents. They show only &ldquo;Safety step: completed on "
              "SACOparentsAlign&rdquo; or, when this app can&apos;t know, &ldquo;Safety step: see SACOparentsAlign&rdquo;."):
        assert s in " ".join(notice.split()) and s in page, s
    assert "not started" not in page and "not started" not in notice
    assert "your professional" not in page.lower() and "the professional linked" not in page.lower()
    assert "six points" not in (fe / "components/PreShareConsentDialog.jsx").read_text()
    assert PRIVACY_NOTICE_VERSION == "2026-10-19-v7"
    heads = re.findall(r"<h2[^>]*>(\d+)\. ", page)
    assert heads == [str(i) for i in range(1, len(heads) + 1)], heads


def test_saved_quick_check_cannot_be_changed_or_read():
    uid, h, _ = user()
    db.portal_state.update_one({"user_id": uid}, {"$set": {"safety_ack": {"cleared": False, "flagged": True, "date": "2026-01-01"},
                                                           "safety_plan": {"safe_place": "x"}}}, upsert=True)
    r = httpx.put(f"{API}/portal/state", headers=h, json={"safety_ack": {"cleared": True, "flagged": False, "date": "2026-10-19"},
                                                          "safety_plan": None, "foundation_text": "ours"}, timeout=20)
    assert r.status_code == 200, r.text
    saved = db.portal_state.find_one({"user_id": uid})
    assert saved["safety_ack"]["flagged"] is True and saved["safety_plan"] == {"safe_place": "x"} and saved["foundation_text"] == "ours"
    state = httpx.get(f"{API}/portal/state", headers=h, timeout=20).json()["state"]
    assert "safety_ack" not in state and "safety_plan" not in state


def test_public_pages_no_longer_describe_the_old_screen():
    fe = ROOT.parent / "frontend/src/pages"
    for f in ("Methodology.jsx", "Accessibility.jsx"):
        src = (fe / f).read_text()
        assert "Safety Screen" not in src and "MasicComparison" not in src, f
    assert "Safety step: completed on SACOparentsAlign" in (fe / "Methodology.jsx").read_text().replace("&ldquo;", "").replace("&rdquo;", "")
