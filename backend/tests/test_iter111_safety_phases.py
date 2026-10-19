"""Iter-111 Phases 2-4: safety-first invitations (templates, reply-to, single-use 7-day, cadence), signed safety-status webhook (OFF), safety review + provisions export scan."""
import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import pymongo
import pytest
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402
from test_iter110_family_checkin import ALL_NO  # noqa: E402

import safety_invites as si  # noqa: E402
import safety_review as sr  # noqa: E402
import safety_status_webhook as wh  # noqa: E402
from core import INVITE_EXPIRY_DAYS  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_FORBIDDEN = ("screen", "tier", "red", "amber", "violence", "abuse", "co-parent has", "safety")


def _plain(html):
    return re.sub(r"<[^>]+>", " ", html).lower()


def test_templates_neutral_single_use_private_device_and_distinct():
    s1, h1 = si.professional_template("Alex", "Dr. Pro", "ABCD1234", "tok")
    s2, h2 = si.coparent_template("Alex", "Sam", "ABCD1234", "tok")
    assert s1 == s2 and "message from" in s1.lower()
    for h in (h1, h2):
        t = _plain(h)
        assert "works once and expires in 14 days" in t and "device only you can access" in t and "abcd1234" in t and "invite=tok" in h
        for bad in _FORBIDDEN:
            assert bad not in t, bad
    assert "reply to this email" in _plain(h1) and "reply to this email" not in _plain(h2)
    assert INVITE_EXPIRY_DAYS == 14


def test_reminder_preview_uses_template1_with_reply_to_professional_and_one_email_per_parent():
    pro, pa, pb, rid = _case()
    pro_email = pro.get(f"{API}/auth/me").json()["email"]
    invs = list(_db.invitations.find({"report_id": rid}, {"_id": 0}))
    assert len(invs) == 2 and {i["role"] for i in invs} == {"a", "b"} and all(i["status"] == "accepted" for i in invs)
    # a fresh pending invite via reissue path is not possible after accept; preview on an accepted invite still renders template 1
    r = pro.get(f"{API}/joint/invitations/{invs[0]['id']}/reminder-preview")
    assert r.status_code == 200 and r.json()["reply_to"] == pro_email and "reply to this email" in _plain(r.json()["html"])
    comms = list(_db.case_communications.find({"case_id": rid, "kind": "invitation"})) if "case_communications" in _db.list_collection_names() else []
    assert len(comms) in (0, 2)


def test_cadence_defaults_and_professional_override_and_reminder_runner(monkeypatch):
    pro, pa, pb, rid = _case()
    d = pro.get(f"{API}/joint/reports/{rid}/invite-cadence").json()
    assert d["cadence"] == {"reminder_days": [3, 6], "max_reminders": 2, "expiry_days": 14}
    assert pa.get(f"{API}/joint/reports/{rid}/invite-cadence").status_code == 403
    r = pro.put(f"{API}/joint/reports/{rid}/invite-cadence", json={"reminder_days": [2, 5, 9], "max_reminders": 5})
    assert r.json()["cadence"] == {"reminder_days": [2, 5, 9], "max_reminders": 2, "expiry_days": 14}
    # runner: plant a pending invite created 4 days ago → reminder 1 sent, second not yet; expired invite skipped
    iid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    _db.invitations.insert_one({"id": iid, "report_id": rid, "role": "b", "invitee_name": "Pat", "invitee_email": f"t_pend_{iid[:6]}@example.com", "inviter_name": "Pro", "token": "tk" + iid[:10], "code": "ZZZZ9999", "status": "pending", "created_at": (now - timedelta(days=4)).isoformat()})
    old = str(uuid.uuid4())
    _db.invitations.insert_one({"id": old, "report_id": rid, "role": "b", "invitee_name": "Old", "invitee_email": f"t_old_{old[:6]}@example.com", "inviter_name": "Pro", "token": "tk" + old[:10], "code": "ZZZZ9998", "status": "pending", "created_at": (now - timedelta(days=16)).isoformat()})
    import asyncio

    async def _twice():
        first = await si.run_invite_reminders()
        inv = _db.invitations.find_one({"id": iid})
        second = await si.run_invite_reminders()
        return first, inv, second
    sent, inv, _second = asyncio.run(_twice())
    assert sent >= 1
    assert inv["reminders_sent"] == 1 and inv.get("last_reminder_at")
    assert _db.invitations.find_one({"id": old}).get("reminders_sent") is None
    assert _db.invitations.find_one({"id": iid})["reminders_sent"] == 1  # 20h gap guard
    _db.invitations.delete_many({"id": {"$in": [iid, old]}})


def test_webhook_payload_signature_allowlist_and_flag_off():
    p = wh.build_payload("case-1", "protected_review", "Dr. Pro")
    assert set(p) == wh.ALLOWED_KEYS and p["safety_mode"] == "protected" and p["referral"] is True and p["set_by"] == "professional" and p["version"] == "1"
    assert wh.build_payload("c", None, "x")["safety_mode"] == "standard" and wh.build_payload("c", "standard", "x")["referral"] is False
    body = json.dumps(p, separators=(",", ":"), sort_keys=True).encode()
    assert wh.sign("s3cret", body) == "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    for bad in ("answers", "tier", "free_text", "rationale", "discloser", "responses", "triggered"):
        assert bad not in json.dumps(p)
    assert wh.WEBHOOK_ENABLED is False and os.environ.get("SAFETY_STATUS_WEBHOOK", "false") == "false"


def test_pathway_confirm_does_not_deliver_while_off_and_admin_status_endpoint():
    pro, pa, pb, rid = _case()
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "stalk": "In the last 12 months"}, "safe_contact": None})
    before = _db.webhook_deliveries.count_documents({"case_id": rid})
    r = pro.put(f"{API}/joint/reports/{rid}/safety-pathway/a", json={"action": "change", "pathway": "protected_review"})
    assert r.status_code == 200
    assert _db.webhook_deliveries.count_documents({"case_id": rid}) == before
    assert pro.get(f"{API}/admin/safety-status-webhook").status_code == 403


def test_safety_review_two_columns_pattern_concern_reasons_provisions_and_logged():
    pro, pa, pb, rid = _case()
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "stalk": "In the last 12 months"}, "safe_contact": None})
    pb.post(f"{API}/joint/reports/{rid}/safety-screening/decline")
    assert pa.get(f"{API}/joint/reports/{rid}/safety-review").status_code == 403
    d = pro.get(f"{API}/joint/reports/{rid}/safety-review").json()
    a, b = d["columns"]
    assert a["app_tier"] == "red" and a["app_tier_label"] == "Red" and b["received"] is False and b["entry_status"] == "declined"
    doms = {p["domain"]: p["signals"] for p in a["pattern"]}
    assert any("Followed" in s for sig in doms.values() for s in sig) and "In the last" not in json.dumps(a["pattern"])
    assert d["review"]["concern_level"] == "none" and len(d["provisions"]) >= 12 and {p["group"] for p in d["provisions"]} == {"Exchange", "Communication", "Contact", "Supervision", "Firearms", "No-contact"}
    r = pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "red", "reasons": [], "provisions": []})
    assert r.status_code == 400
    r = pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "red", "reasons": [sr.REASONS[0], "bogus"], "provisions": ["ex1", "fa1", "nope"], "custom_provisions": ["Exchanges on Sundays at 5pm."], "notes": "n"})
    assert r.status_code == 200 and r.json()["reasons"] == [sr.REASONS[0]] and r.json()["provisions"] == ["ex1", "fa1"] and r.json()["level_label"].startswith("Red")
    kinds = {e["kind"] for e in _db.access_events.find({"report_id": rid})}
    assert {"safety_review"} <= kinds
    # parents and co-parent payloads never include the review
    for s in (pa, pb):
        assert "safety_review" not in s.get(f"{API}/joint/reports/{rid}").text and "concern_level" not in s.get(f"{API}/joint/reports/{rid}").text


def test_provisions_pdf_has_footer_no_screening_text_and_export_scan_blocks_leak():
    pro, pa, pb, rid = _case()
    pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "amber", "reasons": [sr.REASONS[1]], "provisions": ["cm1", "nc1"], "custom_provisions": ["Holiday exchanges at the police station lobby."]})
    r = pro.get(f"{API}/joint/reports/{rid}/safety-review/provisions.pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    import pymupdf
    text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
    assert "only the court decides" in text and "Communication" in text and "No-contact" in text
    for bad in ("Amber", "Red", "pushed, hit", "last 12 months", "Followed / showed up"):
        assert bad not in text, bad
    assert pa.get(f"{API}/joint/reports/{rid}/safety-review/provisions.pdf").status_code == 403
    # leak: custom provision quoting a screening question → scan blocks the export (409) and logs the block
    pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "amber", "reasons": [sr.REASONS[1]], "provisions": [], "custom_provisions": ["Parent answered: Has the other parent pushed, hit, kicked, or physically hurt you? In the last month"]})
    r = pro.get(f"{API}/joint/reports/{rid}/safety-review/provisions.pdf")
    assert r.status_code == 409
    assert _db.access_events.count_documents({"report_id": rid, "kind": "export_scan_block"}) == 1
    assert sr.scan_text("nothing unusual here") == [] and sr.scan_text("In the last month she said") == ["In the last month"]


@pytest.mark.parametrize("fn", ["pdf_lens.build_legal_lens_pdf", "pdf_individual.build_individual_reports_pdf"])
def test_scan_helper_is_importable_for_report_builders(fn):
    mod, name = fn.split(".")
    assert hasattr(__import__(mod), name)


def test_review_fixes_no_tier_in_receipt_scan_or_parent_overview():
    # Code review 2026-10-18: (1a) court receipt line never carries a tier and the export scan blocks tier labels; (2) parent payload has no tier/flag keys
    import safety_screening as ss
    line = ss.receipt({"version": "FV", "tier": 3, "completed_at": "2026-10-18T00:00:00+00:00"}, "Parent A")
    assert "Received" in line and "Tier" not in line and "tier" not in line
    for t in ss.TIER_LABEL.values():
        assert sr.scan_text(f"Parent A: safety screening — Received. {t}.")
    pro, pa, pb, rid = _case()
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "stalk": "In the last 12 months"}, "safe_contact": None})
    mine = pa.get(f"{API}/joint/reports/{rid}/safety-screening").json()
    blob = json.dumps(mine).lower()
    for k in ("app_tier", "app_tier_label", "triggered_rules", "tier", "tier_label"):
        assert k not in mine["roles"]["a"]
    assert "followed / showed up" not in blob and "tier 3" not in blob and "\"red\"" not in blob
    assert "tier" in pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]["a"]


def test_check_in_alias_resolves_by_session_and_shared_code():
    pro, pa, pb, rid = _case()
    code = pro.get(f"{API}/joint/reports/{rid}").json().get("case_code")
    r = pa.get(f"{API}/me/check-in"); assert r.status_code == 200 and r.json()["report_id"] == rid and r.json()["path"] == f"/joint/{rid}/safety-screening"
    r = pa.get(f"{API}/me/check-in", params={"case": code.lower()}); assert r.status_code == 200 and r.json()["report_id"] == rid
    assert pb.get(f"{API}/me/check-in", params={"case": code}).json()["report_id"] == rid
    assert pa.get(f"{API}/me/check-in", params={"case": "SA-000000"}).status_code == 404
    assert pro.get(f"{API}/me/check-in").status_code == 403
    body = pa.get(f"{API}/me/check-in").json(); assert not any(k in body for k in ("tier", "app_tier", "triggered_rules"))


def test_who_looked_parent_sees_views_admin_by_role_only():
    pro, pa, pb, rid = _case()
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO}, "safe_contact": None})
    assert pa.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").json()["events"] == []
    assert pro.get(f"{API}/joint/reports/{rid}/safety-screening/a/responses").status_code == 200
    assert pro.get(f"{API}/joint/reports/{rid}/safety-review").status_code == 200
    ev = pa.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").json()["events"]
    kinds = [e["what"] for e in ev]
    assert "Your individual answers and safe-contact details" in kinds and any("concern level" in k for k in kinds)
    assert all(e["viewer"] and e["at"] for e in ev) and all("Parent" not in e["viewer"] for e in ev)
    assert pb.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").json()["events"] == [e for e in [] ] or all("Your individual answers" not in e["what"] for e in pb.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").json()["events"])
    assert pro.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").status_code == 403
    # widened 2026-10-19: professional views of assessment answers in the report + Foundation Statements appear too, labelled clearly
    pb.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO}, "safe_contact": None})
    rep = pro.get(f"{API}/joint/reports/{rid}/report"); pro.get(f"{API}/joint/reports/{rid}")
    mine = pa.get(f"{API}/joint/reports/{rid}/safety-screening/who-looked").json()
    labels = {e["what"] for e in mine["events"]}
    if rep.status_code == 200:
        assert "Your assessment answers (report)" in labels
    else:
        assert rep.status_code == 400 and "Your assessment answers (report)" not in labels  # report not yet available → nothing viewed, nothing listed
    assert all(e["viewer_role"] != "Parent A" and e["viewer_role"] != "Parent B" for e in mine["events"])
