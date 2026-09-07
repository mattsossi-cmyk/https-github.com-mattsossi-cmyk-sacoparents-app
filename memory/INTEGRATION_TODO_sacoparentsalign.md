# Integration TODO — `sacoparentsalign.com` Professional Directory

**Owner:** Cross-repo (SA CoParents + sacoparentsalign.com)
**Status:** SA CoParents side ready · sibling directory endpoint pending
**Last updated:** 2026-09-07

---

## What's shipped on the SA CoParents side (this repo)

- `professional_directory.py` module with `list_directory()`,
  `get_professional()`, `record_invitation()`, `count_recent_invitations_to()`,
  `align_join_url_for()`.
- Endpoint `GET /api/professional/directory?q=&specialty=` — returns a
  filterable directory (currently a **hardcoded roster of 5 sample
  professionals** in `_MOCK_DIRECTORY`).
- Endpoint `POST /api/professional/directory/invite` — accepts
  `{professional_id, case_id?, personal_note?}`, dispatches a branded
  email invitation to the picked professional, logs the invitation
  in `professional_directory_invites`, and returns
  `{invite_id, delivered_to, join_url, case_id, remaining_this_hour}`.
- Rate limits: 20 invitations / hour / mediator, plus a per-pair
  24-hour duplicate guard that returns 409.
- Frontend "Invite a professional" surface on `/mine` (see
  `ProfessionalDirectoryModal.jsx`).

## The one file to change when the sibling directory ships

`/app/backend/professional_directory.py` → `_fetch_directory()`

```python
# TODAY (temporary):
async def _fetch_directory() -> List[Dict[str, Any]]:
    return list(_MOCK_DIRECTORY)

# TOMORROW (swap in one place, no call-site changes):
async def _fetch_directory() -> List[Dict[str, Any]]:
    import httpx
    base = os.environ["SACOPARENTSALIGN_BASE_URL"]
    api_key = os.environ["SACOPARENTSALIGN_API_KEY"]
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(
            f"{base}/api/directory/professionals",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return r.json().get("professionals", [])
```

## Contract the sibling directory MUST expose

### `GET /api/directory/professionals`

**Headers:**
- `Authorization: Bearer <SACOPARENTSALIGN_API_KEY>` — long-lived
  server-to-server token issued by sacoparentsalign.com and set in
  the SA CoParents `.env` as `SACOPARENTSALIGN_API_KEY`.

**Query params (all optional):**
- `q` — free-text substring; matches against name, title, city,
  specialties. Case-insensitive.
- `specialty` — exact tag match, case-insensitive.
- `limit` — 1-100, default 50.

**Response:**
```json
{
  "professionals": [
    {
      "id": "sacpa-001",                                   // stable across requests
      "name": "Adele Van Wyk",
      "title": "Accredited Family Mediator",
      "city": "Cape Town",
      "specialties": ["mediation", "parenting plans"],     // lowercase tags
      "bio": "16 years running high-conflict mediations…",
      "contact_email": "adele@sacoparentsalign.com",       // used by the invite email
      "photo_url": "https://…/avatar.png"                  // optional; may be null
    }
  ]
}
```

**Error shapes:**
- `401` — invalid or missing bearer token.
- `429` — rate limit exceeded (return `Retry-After` in seconds).
- `503` — upstream directory currently unavailable.

## Contract for the invitation-accept flow

### `GET https://sacoparentsalign.com/join?case=SA-XXXXXX&token=…`

The SA CoParents side dispatches an email with this URL to the
professional. `sacoparentsalign.com` owns:
- rendering the "You've been invited to case SA-XXXXXX" landing page;
- authenticating the professional against their sacoparentsalign.com
  account (no SA CoParents login is issued);
- persisting the acceptance;
- optionally calling BACK into SA CoParents on a webhook so the case
  status reflects the acceptance (webhook contract TBD — file a
  follow-up issue when needed).

The `token` value is a `secrets.token_urlsafe(24)` opaque nonce
(no JWT). It is stored in `professional_directory_invites.join_url`
on the SA CoParents side. When the sibling site hits back with a
webhook, matching by this token identifies the invitation row.

## Environment variables to set on production once the sibling ships

```env
SACOPARENTSALIGN_BASE_URL=https://sacoparentsalign.com
SACOPARENTSALIGN_API_KEY=<sibling-issued-bearer>
```

## What still lives as a mock on the SA CoParents side

- The 5-entry `_MOCK_DIRECTORY` roster in `professional_directory.py`.
  DELETE this list when the sibling endpoint returns data and the
  swap-out is complete.
