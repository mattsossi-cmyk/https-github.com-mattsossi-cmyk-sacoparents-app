"""Seed a demo co-parent pair for the Court page both-parent comparison.

    cd /app/backend && python -c "from seed_court_compare_pair import run; import asyncio; print(asyncio.run(run()))"

Creates parent3@test.com and parent4@test.com (TestPass123!), both on court key PAIR-DEMO-01, safety-cleared,
with Co-Parenting, Self-Assessment and Child Needs results. Resets sharing, sharing-alert history and saved
talking points. Idempotent; local dev DB only.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


KEY = "PAIR-DEMO-01"
SECTIONS = ["Communication & Information Sharing", "Pick-Up, Drop-Off & Transitions", "Educational Needs",
            "Medical & Healthcare Needs", "Daily Routines & Home Consistency", "Emotional & Behavioral Support",
            "Therapy & Skill Reinforcement", "Safety & Supervision", "Social & Community Participation",
            "Long-Term Child Success"]
PARENTS = [
    {"email": "parent3@test.com", "name": "Jordan Parent", "cp": "GGEFGGFEGG", "sa": [4, 4, 3, 3],
     "child": {"medical": {"med_provider": "Dr. Lee, Northside Pediatrics", "med_insurance": "Covered by Jordan's plan"},
               "educational": {"edu_school": "Oak Elementary, 2nd grade"}}},
    {"email": "parent4@test.com", "name": "Casey Parent", "cp": "GFEGGNFEGF", "sa": [4, 2, 3, 4],
     "child": {"medical": {"med_provider": "Dr. Lee, Northside Pediatrics", "med_insurance": "Shared 50/50"},
               "psychological": {"psych_needs": "Gets anxious at handoffs; needs a calm goodbye routine."}}},
]
RATING = {"E": ("Excellent", 3.6), "G": ("Good", 3.0), "F": ("Fair", 2.2), "N": ("Needs Improvement", 1.4)}


async def _ensure_user(db, email: str, name: str) -> str:
    from auth import hash_password

    u = await db.users.find_one({"email": email}, {"_id": 0, "user_id": 1, "created_at": 1})
    if u and isinstance(u.get("created_at"), str):
        return u["user_id"]
    uid = (u or {}).get("user_id") or f"user_{uuid.uuid4().hex[:12]}"
    await db.users.update_one(
        {"email": email},
        {"$set": {"user_id": uid, "email": email, "name": name, "hashed_password": hash_password("TestPass123!"),
                  "created_at": datetime.now(timezone.utc).isoformat(), "email_verified": True, "auth_method": "jwt"}},
        upsert=True,
    )
    return uid


async def run() -> dict:
    from portal_routes import _hash_key
    from self_assessment_routes import CONTENT, compute_scores

    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    now = datetime.now(timezone.utc).isoformat()
    await db.portal_court_keys.update_one(
        {"key_hash": _hash_key(KEY)},
        {"$setOnInsert": {"key_hash": _hash_key(KEY), "case_id": KEY, "mediator_name": "Demo Mediator",
                          "expires_at": None, "revoked_at": None, "created_at": now}},
        upsert=True,
    )
    out = {}
    for p in PARENTS:
        uid = await _ensure_user(db, p["email"], p["name"])
        out[p["email"]] = uid
        await db.portal_state.update_one(
            {"user_id": uid},
            {"$set": {"court_key": KEY, "court_legal_name": p["name"], "updated_at": now,
                      "safety_ack": {"cleared": True, "flagged": False, "date": now[:10]}}},
            upsert=True,
        )
        rows = [{"id": f"s{i + 1}", "number": i + 1, "name": n, "rating": RATING[c][0], "avg": RATING[c][1]}
                for i, (n, c) in enumerate(zip(SECTIONS, p["cp"]))]
        snap = {"submitted_at": now, "overall_rating": "Building Progress", "overall_value": 2, "section_avgs": rows,
                "answered": 67, "total": 67}
        await db.cp_report_history.update_one({"_id": uid}, {"$set": {"user_id": uid, "snapshots": [snap]}}, upsert=True)
        answers = {f"{s['key']}_{i + 1}": v for s, v in zip(CONTENT["sections"], p["sa"]) for i in range(len(s["questions"]))}
        await db.self_assessment_history.delete_many({"user_id": uid})
        await db.self_assessment_history.insert_one({
            "id": uuid.uuid4().hex, "user_id": uid, "completed_at": now, "parent_name": p["name"].split()[0],
            "answers": answers, "reflections": {}, "goal": "", "scores": compute_scores(answers),
        })
        await db.child_needs_assessments.update_one(
            {"user_id": uid},
            {"$set": {"answers": p["child"], "completed_at": {k: now for k in p["child"]}, "updated_at": now}},
            upsert=True,
        )
        await db.court_compare_shares.delete_one({"user_id": uid})
        await db.court_compare_alerts.delete_one({"user_id": uid})
    await db.court_talking_points.delete_one({"court_key": KEY})
    return {"court_key": KEY, "users": out}
