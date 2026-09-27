"""Iteration 81: Gemini-drafted Joint Report (review-gated), admin listing hide, referral ZIP/distance, share link."""
import os
import uuid

import pymongo
import requests

from casekit import complete_both, new_user
from test_judicial_portal import API, _flow, _judge

DB = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_ai_joint_draft_review_gate() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    pa, _pb = complete_both(API, pro, rid, case["invitations"])
    base = pro.get(f"{API}/joint/reports/{rid}/report").json()
    assert not base.get("ai_assisted")
    assert pro.get(f"{API}/joint/reports/{rid}/ai-joint-draft").json()["status"] == "none"

    r = pro.post(f"{API}/joint/reports/{rid}/ai-joint-draft")
    if r.status_code != 200:  # AI unavailable: rule-based report must remain in effect
        assert r.status_code in (502, 503), r.text
        assert not pro.get(f"{API}/joint/reports/{rid}/report").json().get("ai_assisted")
        return
    d = r.json()
    assert d["status"] == "draft" and d["fields"]["alignment_statements"] and d["label"].startswith("AI-ASSISTED")
    # not yet visible to anyone
    assert not pro.get(f"{API}/joint/reports/{rid}/report").json().get("ai_assisted")

    edited = pro.put(f"{API}/joint/reports/{rid}/ai-joint-draft", json={"fields": {"next_steps": ["Schedule a neutral check-in.", "Share the school calendar."]}}).json()
    assert edited["fields"]["next_steps"] == ["Schedule a neutral check-in.", "Share the school calendar."]
    assert pro.post(f"{API}/joint/reports/{rid}/ai-joint-draft/approve").json()["status"] == "approved"
    rep = pro.get(f"{API}/joint/reports/{rid}/report").json()
    assert rep["ai_assisted"] is True and rep["next_steps"][0] == "Schedule a neutral check-in." and rep["ai_model"] == "Gemini 3.1 Pro"
    prep = pa.get(f"{API}/joint/reports/{rid}/report").json()
    assert "professional_evaluation" not in prep and prep["ai_assisted"] is True
    assert pro.get(f"{API}/joint/reports/{rid}/pdf").status_code == 200
    assert pro.post(f"{API}/joint/reports/{rid}/ai-joint-draft/discard").json()["status"] == "none"
    assert not pro.get(f"{API}/joint/reports/{rid}/report").json().get("ai_assisted")
    assert judge.get(f"{API}/joint/reports/{rid}/ai-joint-draft").status_code in (403, 404)


def test_referral_zip_distance_in_case_view() -> None:
    judge = _judge()
    pro = new_user(API, "professional", "Distance Pro")
    me = pro.get(f"{API}/auth/me").json()
    DB.users.update_one({"_id": me["id"]}, {"$set": {"profile.zip": "78130"}})
    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-D{uuid.uuid4().hex[:4]}", "requested_reports": ["co_parenting"], "parties_zip": "78201"}).json()
    assert ref["parties_zip"] == "78201" and ref["professional_zip"] == "78130" and 20 < ref["professional_distance_miles"] < 45
    rows = judge.get(f"{API}/court-dashboard/referrals").json()
    row = next(x for x in rows if x["id"] == ref["id"])
    assert row["professional_distance_miles"] == ref["professional_distance_miles"]


def test_admin_hide_listing_and_share_link() -> None:
    pro = new_user(API, "professional", "Share Pro")
    me = pro.get(f"{API}/auth/me").json()
    assert pro.put(f"{API}/me/public-listing", json={"listed": True, "bio": "Neutral mediation support."}).status_code == 200
    assert requests.get(f"{API}/public/professionals/{me['id']}").json()["name"] == "Share Pro"

    admin = new_user(API, "professional", "Temp Admin")
    admin_id = admin.get(f"{API}/auth/me").json()["id"]
    DB.users.update_one({"_id": admin_id}, {"$set": {"role": "admin"}})
    listed = admin.get(f"{API}/admin/public-listings").json()
    assert any(x["id"] == me["id"] and x["email"] == me["email"] for x in listed)
    assert admin.post(f"{API}/admin/public-listings/{me['id']}/hide", json={"hidden": True, "reason": "Bio not neutral"}).json()["hidden"] is True
    assert requests.get(f"{API}/public/professionals/{me['id']}").status_code == 404
    assert all(x["id"] != me["id"] for x in requests.get(f"{API}/public/professionals").json()["professionals"])
    mine = pro.get(f"{API}/me/public-listing").json()
    assert mine["hidden"] is True and mine["hidden_reason"] == "Bio not neutral"
    assert admin.post(f"{API}/admin/public-listings/{me['id']}/hide", json={"hidden": False}).json()["hidden"] is False
    assert requests.get(f"{API}/public/professionals/{me['id']}").status_code == 200
    assert pro.get(f"{API}/admin/public-listings").status_code == 403
