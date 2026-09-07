"""Professional directory + invite integration for sacoparentsalign.com.

The sibling site (`sacoparentsalign.com`) is planned to expose a
directory of pre-vetted co-parenting professionals — mediators,
parenting coordinators, family attorneys, therapists — that
mediators inside SA CoParents can pick to co-manage a case.

Today the sibling directory API doesn't exist yet, so this module
serves a small hardcoded roster as a stand-in. When the real
endpoint ships, ONE `_fetch_directory` implementation swap points
the app at the sibling API without touching call-sites or the UI.

See `/app/memory/INTEGRATION_TODO_sacoparentsalign.md` for the
exact contract we expect the sibling directory to expose.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


# ---------------------------------------------------------------------
# Directory — MOCK today, SWAPPABLE tomorrow.
# ---------------------------------------------------------------------
# ORDER: alphabetical by display name. Fields must match the contract
# in INTEGRATION_TODO_sacoparentsalign.md so the swap is a one-liner.
# Each entry MUST include: id, name, title, city, specialties[], bio,
# contact_email. `photo_url` is optional.
_MOCK_DIRECTORY: List[Dict[str, Any]] = [
    {
        "id": "sacpa-001",
        "name": "Adele Van Wyk",
        "title": "Accredited Family Mediator",
        "city": "Cape Town",
        "specialties": ["mediation", "parenting plans", "co-parenting coaching"],
        "bio": (
            "16 years running high-conflict mediations across the "
            "Western Cape. Warm, structured sessions; child-first framing."
        ),
        "contact_email": "adele@sacoparentsalign.com",
        "photo_url": None,
    },
    {
        "id": "sacpa-002",
        "name": "Dr. Nomsa Dlamini",
        "title": "Family Psychologist · Parenting Coordinator",
        "city": "Johannesburg",
        "specialties": ["parenting coordinator", "psychology", "high-conflict"],
        "bio": (
            "HPCSA-registered psychologist. Court-appointed parenting "
            "coordinator on Gauteng High Court cases since 2018."
        ),
        "contact_email": "nomsa@sacoparentsalign.com",
        "photo_url": None,
    },
    {
        "id": "sacpa-003",
        "name": "Kagiso Molefe",
        "title": "Family Attorney (Solicitor)",
        "city": "Pretoria",
        "specialties": ["family law", "consent papers", "Section 21"],
        "bio": (
            "Family law attorney at Molefe & Partners. Drafts consent "
            "papers and Section 21 co-parenting agreements."
        ),
        "contact_email": "kagiso@sacoparentsalign.com",
        "photo_url": None,
    },
    {
        "id": "sacpa-004",
        "name": "Priya Naidoo",
        "title": "Child & Family Therapist",
        "city": "Durban",
        "specialties": ["child therapy", "family reunification", "trauma-informed"],
        "bio": (
            "Trauma-informed family therapist. 12 years running "
            "reunification support for post-separation families."
        ),
        "contact_email": "priya@sacoparentsalign.com",
        "photo_url": None,
    },
    {
        "id": "sacpa-005",
        "name": "Sanet Botha",
        "title": "Divorce Mediator · Financial Neutral",
        "city": "Stellenbosch",
        "specialties": ["financial mediation", "budget planning", "asset division"],
        "bio": (
            "CFP® and accredited mediator specialising in the money "
            "side of separation — child budgets, asset splits, alimony."
        ),
        "contact_email": "sanet@sacoparentsalign.com",
        "photo_url": None,
    },
]


async def _fetch_directory() -> List[Dict[str, Any]]:
    """Return the sacoparentsalign.com professional directory.

    Today: returns the hardcoded `_MOCK_DIRECTORY` above.

    Tomorrow: replace with an HTTP call to the real sibling API. The
    return shape MUST stay identical (see INTEGRATION_TODO doc).

    Example future implementation (do not enable until the sibling
    endpoint ships):

        import httpx
        base = os.environ.get("SACOPARENTSALIGN_BASE_URL")
        api_key = os.environ.get("SACOPARENTSALIGN_API_KEY")
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{base}/api/directory/professionals",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            r.raise_for_status()
            return r.json().get("professionals", [])
    """
    return list(_MOCK_DIRECTORY)


def _tokenise(text: str) -> List[str]:
    return [t.strip().lower() for t in (text or "").split() if t.strip()]


async def list_directory(
    *,
    query: Optional[str] = None,
    specialty: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return directory rows filtered by optional query + specialty.
    `query` matches against name / title / city / specialties (case-
    insensitive substring). `specialty` is an exact match against the
    specialties list (also case-insensitive)."""
    rows = await _fetch_directory()
    q_tokens = _tokenise(query or "")
    spec = (specialty or "").strip().lower() or None
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        haystack = " ".join([
            row.get("name") or "",
            row.get("title") or "",
            row.get("city") or "",
            " ".join(row.get("specialties") or []),
        ]).lower()
        if q_tokens and not all(tok in haystack for tok in q_tokens):
            continue
        if spec:
            if not any(spec == (s or "").lower() for s in (row.get("specialties") or [])):
                continue
        filtered.append(row)
    return filtered[: max(1, min(int(limit or 50), 100))]


async def get_professional(prof_id: str) -> Optional[Dict[str, Any]]:
    """Return a single directory entry by id, or None."""
    if not prof_id:
        return None
    rows = await _fetch_directory()
    for row in rows:
        if row.get("id") == prof_id:
            return row
    return None


# ---------------------------------------------------------------------
# Invitation audit ledger — mediator picks a pro from the directory
# and dispatches an invitation email.
# ---------------------------------------------------------------------
_INVITE_COLL = "professional_directory_invites"


async def record_invitation(
    db: AsyncIOMotorDatabase,
    *,
    inviter_user_id: str,
    inviter_name: Optional[str],
    inviter_email: Optional[str],
    case_id: Optional[str],
    professional: Dict[str, Any],
    personal_note: Optional[str],
    join_url: str,
    invite_id: str,
) -> None:
    """Persist one row per invitation dispatched. Powers the future
    "who did I invite?" audit view + prevents duplicate spam
    (a mediator hitting Send twice in five seconds is caught by the
    call-site rate limit query on this collection)."""
    await db[_INVITE_COLL].insert_one({
        "invite_id": invite_id,
        "inviter_user_id": inviter_user_id,
        "inviter_name": inviter_name or None,
        "inviter_email": inviter_email or None,
        "case_id": case_id or None,
        "professional_id": professional.get("id"),
        "professional_name": professional.get("name"),
        "professional_email": professional.get("contact_email"),
        "personal_note": (personal_note or "").strip() or None,
        "join_url": join_url,
        "created_at": datetime.now(timezone.utc),
    })


async def count_recent_invitations_to(
    db: AsyncIOMotorDatabase,
    *,
    inviter_user_id: str,
    professional_id: str,
    within_hours: int = 24,
) -> int:
    """Return the number of invitations this mediator has sent to a
    specific professional in the last `within_hours`. Used by the
    invite endpoint to reject "I clicked Send twice by accident"
    double-fires."""
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    return await db[_INVITE_COLL].count_documents({
        "inviter_user_id": inviter_user_id,
        "professional_id": professional_id,
        "created_at": {"$gte": since},
    })


def align_join_url_for(*, case_id: Optional[str], token: str) -> str:
    """Build the sibling-site join URL. `SACOPARENTSALIGN_BASE_URL`
    defaults to the production sibling domain — override in tests
    or staging via env var."""
    base = os.environ.get("SACOPARENTSALIGN_BASE_URL") or "https://sacoparentsalign.com"
    qs = f"token={token}"
    if case_id:
        qs = f"case={case_id}&{qs}"
    return f"{base.rstrip('/')}/join?{qs}"
