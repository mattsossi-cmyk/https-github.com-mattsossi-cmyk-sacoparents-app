"""Safety Gate core: one encrypted case_safety record per joint case (sent by SACOparentsAlign).

Parents never read the record; they only get the resolved feature flags (identical for both parents).
Every read and write is logged to safety_audit_log, which only platform admins can export.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from pymongo.errors import DuplicateKeyError

COLL = "case_safety"
AUDIT = "safety_audit_log"
SEEN = "safety_webhook_seen"
REJECTS = "safety_webhook_rejects"
TESTS = "safety_webhook_tests"
CASES = "joint_alignment_cases"

MODES = ("standard", "structured", "restricted")
RANK = {m: i for i, m in enumerate(MODES)}
SET_BY = ("default", "auto_red", "professional")
REFERRALS = ("none", "parallel_parenting")
TEMPLATE_CATEGORIES = ["schedule", "health", "school", "expenses"]
NOTE_MAX = 280

DEFAULT = {
    "safety_mode": "standard", "set_by": "default", "professional_name": None,
    "referral": "none", "screening_offered": False, "note_review": False,
}

BANNERS = {
    "professional": "Some features are set by your professional for this case.",
    "case_setup": "Some features are limited until your case setup is complete.",
}
SET_BY_LABELS = {
    "professional": "Set by your professional",
    "case_setup": "These settings apply until your case setup is complete.",
}

_ON = {
    "free_form_messaging": True, "template_messages": True, "template_note_max_chars": NOTE_MAX,
    "template_note_review": False, "calls_video": True, "addresses_visible": True, "gps_checkins": True,
    "exchange_location": "parent_entered", "read_receipts": True, "last_seen": True, "typing_indicators": True,
    "photo_sharing": True, "file_metadata": "kept", "calendar": True, "expenses": True, "history_export": True,
}
_STRUCTURED = {
    **_ON, "free_form_messaging": False, "calls_video": False, "addresses_visible": False, "gps_checkins": False,
    "exchange_location": "public_place", "read_receipts": False, "last_seen": False, "typing_indicators": False,
    "file_metadata": "location_removed",
}
_RESTRICTED = {**_STRUCTURED, "exchange_location": "public_place_or_supervised", "file_metadata": "all_removed"}
FEATURES = {"standard": _ON, "structured": _STRUCTURED, "restricted": _RESTRICTED}

_TEMPLATES_LINE = "Ready-made templates for schedule, health, school and expenses, each with an optional note of up to 280 characters."
_SETTINGS = {
    "standard": [
        ("Messages", "Your own messages and the ready-made templates are both on."),
        ("Calls and video", "On"),
        ("Home and school addresses", "Shown to both parents"),
        ("Live location and location check-ins", "On"),
        ("Exchange location", "Entered by a parent"),
        ("Read receipts, last seen and typing", "On"),
        ("Photos and files", "On"),
        ("Calendar, expenses and history export", "On"),
    ],
    "structured": [
        ("Messages", f"{_TEMPLATES_LINE} Free-form messages are off."),
        ("Calls and video", "Off"),
        ("Home and school addresses", "Not shown to the other parent"),
        ("Live location and location check-ins", "Off"),
        ("Exchange location", "A fixed public place"),
        ("Read receipts, last seen and typing", "Off"),
        ("Photos and files", "On. Location details are removed before anything is stored."),
        ("Calendar, expenses and history export", "On"),
    ],
    "restricted": [
        ("Messages", f"{_TEMPLATES_LINE} Free-form messages are off."),
        ("Calls and video", "Off"),
        ("Home and school addresses", "Not shown to the other parent"),
        ("Live location and location check-ins", "Off"),
        ("Exchange location", "A fixed public place, or a third-party or supervised exchange"),
        ("Read receipts, last seen and typing", "Off"),
        ("Photos and files", "On. All hidden details (such as location, date and device) are removed before anything is stored."),
        ("Calendar, expenses and history export", "On"),
    ],
}
_REVIEW_LINE = ("Template notes", "Your professional reads notes before they are delivered.")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fernet() -> Fernet:
    return Fernet(os.environ["SAFETY_ENC_KEY"].encode())


def encrypt(fields: Dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(fields, sort_keys=True).encode()).decode()


def decrypt(token: str) -> Dict[str, Any]:
    return json.loads(_fernet().decrypt(token.encode()))


async def ensure_indexes(db) -> None:
    await db[COLL].create_index("case_id", unique=True)
    await db[AUDIT].create_index("at")
    await db[SEEN].create_index("seen_at", expireAfterSeconds=24 * 3600)
    await db[REJECTS].create_index("created", expireAfterSeconds=35 * 24 * 3600)
    await db[TESTS].create_index("created", expireAfterSeconds=35 * 24 * 3600)


REJECTS_PER_MINUTE = 60


async def record_test(db, test_id: str) -> None:
    """A signed test message: proves the link works, never touches a case."""
    now = datetime.now(timezone.utc)
    prior = await db[TESTS].find_one({"_id": test_id}, {"requested_at": 1})
    took = None
    if prior and prior.get("requested_at"):
        took = round((now - datetime.fromisoformat(prior["requested_at"])).total_seconds() * 1000)
    source = "self" if test_id.startswith("self-") else "align"
    await db[TESTS].update_one(
        {"_id": test_id},
        {"$set": {"received_at": now.isoformat(), "round_trip_ms": took, "source": source}, "$setOnInsert": {"created": now}},
        upsert=True,
    )
    await audit(db, "system", "align", "test_received", None)
SILENCE_DAYS = 7


def silence_status(last_at: Optional[str], now: datetime) -> Dict[str, Any]:
    """Warn admins when no signed Align update (applied or ignored) has arrived for SILENCE_DAYS."""
    if not last_at:
        return {"threshold_days": SILENCE_DAYS, "days_since": None, "warn": True}
    days = (now - datetime.fromisoformat(last_at)).days
    return {"threshold_days": SILENCE_DAYS, "days_since": days, "warn": days >= SILENCE_DAYS}


async def record_reject(db, reason: str) -> None:
    """Only the time and the reason are kept for a refused Align request; a flood is capped per minute."""
    now = datetime.now(timezone.utc)
    if await db[REJECTS].count_documents({"created": {"$gte": now - timedelta(minutes=1)}}, limit=REJECTS_PER_MINUTE) >= REJECTS_PER_MINUTE:
        return
    await db[REJECTS].insert_one({"at": now_iso(), "reason": reason, "created": now})


async def audit(db, actor_type: str, actor_id: Optional[str], action: str, case_id: Optional[str]) -> None:
    await db[AUDIT].insert_one({"at": now_iso(), "actor_type": actor_type, "actor_id": actor_id, "action": action, "case_id": case_id})


async def read_record(db, case_id: str, actor_type: str, actor_id: Optional[str]) -> Optional[Dict[str, Any]]:
    doc = await db[COLL].find_one({"case_id": case_id}, {"_id": 0})
    await audit(db, actor_type, actor_id, "read", case_id)
    if not doc:
        return None
    return {**decrypt(doc["enc"]), "version": doc["version"], "updated_at": doc["updated_at"],
            "setup_completed_at": doc.get("setup_completed_at")}


async def apply_update(db, upd: Dict[str, Any]) -> str:
    """Versioned write. Returns 'applied', 'stale' (version not higher) or 'refused'.
    Only a named professional sets or lifts a limit; any other update can change the check-in status only."""
    case_id, version = upd["case_id"], upd["version"]
    pro = (upd.get("professional_name") or "").strip() if upd["set_by"] == "professional" else ""
    if upd["set_by"] == "auto_red" or (upd["set_by"] == "professional" and not pro):
        await audit(db, "system", "sacoparentsalign", "write_refused", case_id)
        return "refused"
    cur = await db[COLL].find_one({"case_id": case_id}, {"_id": 0})
    await audit(db, "system", "sacoparentsalign", "read", case_id)
    if cur and version <= cur["version"]:
        await audit(db, "system", "sacoparentsalign", "write_ignored_stale_version", case_id)
        return "stale"
    old = decrypt(cur["enc"]) if cur else DEFAULT
    if pro:
        fields = {**{k: upd[k] for k in DEFAULT}, "professional_name": pro}
    else:
        # Existing limits (including older automatic ones) stay exactly as they are.
        fields = {**{k: old[k] for k in DEFAULT}, "screening_offered": upd["screening_offered"]}
    # Date the case setup was marked complete: set when it turns complete, kept while it stays complete, cleared if reopened.
    was_complete = bool(cur) and old["screening_offered"]
    completed_at = (cur.get("setup_completed_at") if was_complete else now_iso()) if fields["screening_offered"] else None
    doc = {"case_id": case_id, "version": version, "enc": encrypt(fields), "updated_at": now_iso(),
           "setup_completed_at": completed_at}
    if cur:
        res = await db[COLL].update_one({"case_id": case_id, "version": cur["version"]}, {"$set": doc})
        if not res.modified_count:
            return "stale"
    else:
        try:
            await db[COLL].insert_one(doc)
        except DuplicateKeyError:
            return "stale"
    await audit(db, *(("professional", pro) if pro else ("system", "sacoparentsalign")), "write", case_id)
    return "applied"


def resolve(rec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Effective mode for one case. Only a professional sets limits; the app never limits a case on its own.
    Older auto_red records keep the limit they had until a professional changes it."""
    r = {**DEFAULT, **(rec or {})}
    if r["set_by"] == "default":
        mode, source = "standard", "case_setup"
    else:
        mode, source = r["safety_mode"], "professional"
    return {"mode": mode, "source": source, "referral": r["referral"], "note_review": bool(r["note_review"]) and mode == "restricted",
            "setup_complete": bool(r["screening_offered"]),
            "setup_completed_at": r.get("setup_completed_at") if r["screening_offered"] else None}


def combine(resolved: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A parent in more than one case gets the most limited settings of any of them."""
    if not resolved:
        return resolve(None)
    top = max(resolved, key=lambda x: RANK[x["mode"]])
    dates = [x["setup_completed_at"] for x in resolved]
    same = [x for x in resolved if x["mode"] == top["mode"]]
    return {
        "mode": top["mode"],
        "source": "professional" if any(x["source"] == "professional" for x in same) else "case_setup",
        "referral": "parallel_parenting" if any(x["referral"] == "parallel_parenting" for x in resolved) else "none",
        "note_review": any(x["note_review"] for x in same),
        "setup_complete": all(x["setup_complete"] for x in resolved),
        "setup_completed_at": max(dates) if all(dates) else None,
    }


def payload(res: Dict[str, Any]) -> Dict[str, Any]:
    """The only thing parents receive. No mode name, reason, professional name or per-user field."""
    mode, limited = res["mode"], res["mode"] != "standard"
    features = {**FEATURES[mode], "template_note_review": res["note_review"]}
    settings = list(_SETTINGS[mode]) + ([_REVIEW_LINE] if res["note_review"] else [])
    return {
        "banner": BANNERS[res["source"]] if limited else None,
        "set_by_label": SET_BY_LABELS[res["source"]] if limited else None,
        "features": features,
        "template_categories": TEMPLATE_CATEGORIES,
        "settings": [{"label": a, "value": b} for a, b in settings],
        "plan_options": res["referral"] == "parallel_parenting",
        "setup_complete": res["setup_complete"],
        "setup_completed_on": (res["setup_completed_at"] or "")[:10] or None,
    }


def message_allowed(features: Dict[str, Any], kind: str, category: Optional[str] = None, note: str = "") -> bool:
    """For parent-to-parent messaging: child information always flows through templates in every mode."""
    if kind == "template":
        return category in TEMPLATE_CATEGORIES and len(note or "") <= features["template_note_max_chars"]
    return kind == "free_form" and features["free_form_messaging"]


def scrub_level(features: Dict[str, Any]) -> str:
    return {"kept": "none", "location_removed": "location", "all_removed": "all"}[features["file_metadata"]]


async def case_ids_for(db, user_id: str) -> List[str]:
    cur = db[CASES].find({"parents.user_id": user_id}, {"_id": 0, "case_id": 1})
    return sorted({d["case_id"] async for d in cur if d.get("case_id")})


async def resolved_for_case(db, case_id: str, actor_type: str, actor_id: Optional[str]) -> Dict[str, Any]:
    return resolve(await read_record(db, case_id, actor_type, actor_id))


async def setup_complete_for(db, user_id: str) -> bool:
    """Family check-in done for every case this parent is in (same answer for both parents)."""
    ids = await case_ids_for(db, user_id)
    return combine([await resolved_for_case(db, c, "user", user_id) for c in ids])["setup_complete"]


SAFETY_STEP_DONE = "Safety step: completed on SACOparentsAlign"
SAFETY_STEP_SEE = "Safety step: see SACOparentsAlign"


def safety_step_text(done: bool) -> str:
    """Completed only when SACOparentsAlign has told this app so; otherwise this app can't know."""
    return SAFETY_STEP_DONE if done else SAFETY_STEP_SEE


async def safety_step_line(db, *user_ids: Optional[str]) -> str:
    """The only safety wording documents may carry, from the same status as the Family check-in card."""
    ids = [u for u in user_ids if u]
    done = bool(ids) and all([await setup_complete_for(db, u) for u in ids])
    return safety_step_text(done)


def as_utc(v):
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return v.replace(tzinfo=timezone.utc) if isinstance(v, datetime) and v.tzinfo is None else v


async def linked_at_for(db, user_id: str) -> Optional[datetime]:
    """Case-level link date (latest parent acceptance, else case creation): the same for both parents."""
    dates = []
    async for d in db[CASES].find({"parents.user_id": user_id}, {"_id": 0, "created_at": 1, "parents.accepted_at": 1}):
        accepted = [as_utc(p["accepted_at"]) for p in d.get("parents") or [] if p.get("accepted_at")]
        when = max(accepted) if accepted else as_utc(d.get("created_at"))
        if isinstance(when, datetime):
            dates.append(when)
    return min(dates) if dates else None


async def count_auto_restricted(db) -> int:
    """Cases still restricted by an older automatic (auto_red) update: a professional should review them."""
    n = 0
    async for d in db[COLL].find({}, {"_id": 0, "enc": 1}):
        f = decrypt(d["enc"])
        n += f["safety_mode"] == "restricted" and f["set_by"] == "auto_red"
    return n
