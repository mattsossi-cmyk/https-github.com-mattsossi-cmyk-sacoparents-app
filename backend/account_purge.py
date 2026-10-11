"""Complete account deletion: every record a parent owns, scrubbed from shared ones, identity stripped from compliance logs."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

logger = logging.getLogger(__name__)

# Fields that mean "this record belongs to (or is about) this parent".
UID_FIELDS = (
    "user_id", "parent_id", "inviting_parent_id", "sender_user_id", "creator_user_id", "partner_user_id",
    "inviter_user_id", "signed_up_user_id", "doc_owner_user_id", "target_user_id", "parent_user_id",
)
EMAIL_FIELDS = (
    "email", "parent_email", "target_email", "inviting_parent_email", "inviter_email", "invitee_email",
    "creator_email", "partner_email", "sender_email",
)
# `email` here is the person the parent sent something to, not the owner.
RECIPIENT_EMAIL = {"child_needs_shares", "journey_certificate_shares"}
# Kept for legal record-keeping with the name, email and account id replaced by an anonymous id.
COMPLIANCE = {"phi_access_log", "legal_acknowledgments", "hb300_acknowledgements", "hb300_access_requests"}
# Global/config collections, the users table (handled last) and shared records handled field-by-field.
SKIP = {
    "users", "portal_court_keys", "release_checks", "release_check_state", "nudge_copy_config", "nudge_copy_events",
    "nudge_copy_history", "professional_bundle_templates", "professionals_intro_voice_cache", "weekly_insights",
    "weekly_insights_emails", "hb300_breach_reports", "professionals", "mediator_badges", "account_deletions",
    "secure_doc_files.files", "secure_doc_files.chunks", "joint_alignment_cases", "court_agreements",
    "deep_dive_compare_snapshots",
}
IDENTITY_FIELDS = ("name", "full_name", "delivery_email", "ip", "ip_address", "user_agent")
SHARE_COLLECTIONS = ("med_deep_shares", "edu_deep_shares", "psych_deep_shares", "snc2_shares")
DELETED_PARENT = "A parent deleted their account"


def anon_id(user_id: str) -> str:
    return "deleted_" + hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def _owner_filter(coll: str, uid: str, email: str) -> Dict:
    ors = [{f: uid} for f in UID_FIELDS]
    if email:
        ors += [{f: email} for f in EMAIL_FIELDS if not (f == "email" and coll in RECIPIENT_EMAIL)]
    return {"$or": ors}


async def _anonymise_compliance(db: AsyncIOMotorDatabase, coll: str, uid: str, email: str, anon: str) -> int:
    n = 0
    for f in UID_FIELDS:
        n += (await db[coll].update_many({f: uid}, {"$set": {f: anon}})).modified_count
    if email:
        for f in EMAIL_FIELDS:
            n += (await db[coll].update_many({f: email}, {"$set": {f: None}})).modified_count
    unset = {f: "" for f in IDENTITY_FIELDS}
    await db[coll].update_many({"$or": [{f: anon} for f in UID_FIELDS]}, {"$unset": unset})
    return n


async def _scrub_shared(db: AsyncIOMotorDatabase, uid: str, email: str, now: str) -> None:
    """Shared records keep working for the co-parent / professional; only this parent's part goes."""
    p_match = {"$or": [{"p.user_id": uid}] + ([{"p.email": email}] if email else [])}
    await db.joint_alignment_cases.update_many(
        {"$or": [{"parents.user_id": uid}] + ([{"parents.email": email}] if email else [])},
        {"$set": {
            "parents.$[p].user_id": None, "parents.$[p].email": "", "parents.$[p].name": DELETED_PARENT,
            "parents.$[p].invitation_token": None, "parents.$[p].assessment_ref": None,
            "parents.$[p].step_completions": [], "parents.$[p].account_deleted_at": now,
        }},
        array_filters=[p_match],
    )
    await db.joint_alignment_cases.update_many(
        {"$or": [{"professional.id": uid}, {"professional_created_by": uid}]},
        {"$set": {"professional.id": None, "professional.email": "", "professional.name": "A professional deleted their account",
                  "professional_created_by": None}},
    )
    await db.court_agreements.update_many({"marked_by": uid}, {"$pull": {"marked_by": uid}})
    await db.court_agreements.update_many({"marked_by": {"$size": 0}}, {"$set": {"agreed_at": None}})
    share_ids = []
    for coll in SHARE_COLLECTIONS:
        share_ids += await db[coll].distinct("share_id", {"$or": [{"creator_user_id": uid}, {"partner_user_id": uid}]})
    if share_ids:
        await db.deep_dive_compare_snapshots.delete_many({"share_id": {"$in": share_ids}})
    await db.users.update_many({"invited_by_user_id": uid}, {"$unset": {"invited_by_user_id": ""}})
    await db.portal_court_keys.update_many(
        {"created_by": uid}, {"$set": {"created_by": None, "label": "", "mediator_name": "A professional deleted their account"}}
    )


async def _delete_sent_files(db: AsyncIOMotorDatabase, uid: str) -> None:
    bucket = AsyncIOMotorGridFSBucket(db, bucket_name="secure_doc_files")
    async for doc in db.secure_documents.find({"sender_user_id": uid}, {"_id": 0, "files.file_id": 1}):
        for f in doc.get("files") or []:
            try:
                await bucket.delete(f["file_id"])
            except Exception:  # noqa: BLE001 — already gone
                pass


async def purge_account(db: AsyncIOMotorDatabase, user_id: str, email: str) -> Dict[str, int]:
    """Delete everything this parent owns. Returns {collection: docs deleted or anonymised}."""
    email = (email or "").strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    anon = anon_id(user_id)
    counts: Dict[str, int] = {}
    await _scrub_shared(db, user_id, email, now)
    await _delete_sent_files(db, user_id)
    await db.cp_report_history.delete_many({"_id": user_id})
    for coll in await db.list_collection_names():
        if coll in SKIP or coll.startswith("system."):
            continue
        if coll in COMPLIANCE:
            n = await _anonymise_compliance(db, coll, user_id, email, anon)
        else:
            n = (await db[coll].delete_many(_owner_filter(coll, user_id, email))).deleted_count
        if n:
            counts[coll] = n
    counts["users"] = (await db.users.delete_many({"user_id": user_id})).deleted_count
    await db.account_deletions.insert_one({"anon_id": anon, "deleted_at": now, "collections": len(counts)})
    logger.info("account purged anon=%s collections=%d", anon, len(counts))
    return counts
