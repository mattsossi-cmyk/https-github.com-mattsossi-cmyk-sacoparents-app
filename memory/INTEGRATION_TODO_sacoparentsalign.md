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

## The one line to change when the sibling directory ships

**Nothing.** As of iter166 (2026-09-07), `professional_directory.py`
already contains a live httpx client that activates automatically
the moment **both** env vars below are set on production:

```env
SACOPARENTSALIGN_BASE_URL=https://sacoparentsalign.com
SACOPARENTSALIGN_API_KEY=<sibling-issued-bearer>
```

Setting **both** switches `_fetch_directory()` from the hardcoded
`_MOCK_DIRECTORY` roster to a live GET against
`{SACOPARENTSALIGN_BASE_URL}/api/directory/professionals` with:
- 8-second timeout
- 60-second in-process response cache (per-worker)
- graceful fallback to `_MOCK_DIRECTORY` on ANY sibling failure
  (timeout, DNS error, 4xx, 5xx, non-JSON body, missing
  `professionals[]` key, or every row missing required fields)
- per-row validation: rows missing `id`, `name`, or `contact_email`
  are dropped before returning

Zero call-site changes, zero UI changes, zero deploys — the
`/professional/directory` endpoint just starts returning real
sibling data as soon as the env vars are configured.

Delete `_MOCK_DIRECTORY` from `professional_directory.py` when the
sibling is stable enough that a fallback roster is no longer
desired.

## Reference implementation (already shipped inside `_fetch_directory_from_sibling`)

```python
async def _fetch_directory_from_sibling(base, api_key):
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(
            f"{base}/api/directory/professionals",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if r.status_code >= 400:
        return None  # → caller falls back to mock
    payload = r.json()
    rows = payload.get("professionals", [])
    return [row for row in rows if _validate_directory_row(row)] or None
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
- calling BACK into SA CoParents on the accept webhook so the case
  status reflects the acceptance (see webhook contract below).

The `token` value is a `secrets.token_urlsafe(24)` opaque nonce
(no JWT). It is stored in `professional_directory_invites.invite_token`
on the SA CoParents side.

### Accept webhook — `POST https://sacoparentsapp.online/api/professional/directory/invite/accept-webhook`

Called by sacoparentsalign.com the moment a professional accepts.

**Headers:**
- `Content-Type: application/json`
- `X-Sacoparentsalign-Signature: sha256=<hex>` — hex-encoded
  HMAC-SHA256 of the raw request body keyed by the shared secret set
  on both sides as `SACOPARENTSALIGN_WEBHOOK_SECRET`. The `sha256=`
  prefix is accepted but optional.

**Body:**
```json
{
  "token": "<the opaque invite token>",
  "accepted_at": "2026-09-07T21:20:00Z",     // optional, server time fallback
  "professional_id": "sacpa-002",             // sibling canonical id
  "professional_name": "Dr. Nomsa Dlamini",   // display name
  "professional_email": "nomsa@sacoparentsalign.com"
}
```

**Responses:**
- `200 {ok: true, status: "accepted", case_id: str|null, applied: bool}`
  — flip persisted (or was already applied → `applied=false`,
  idempotent). If the invite was case-bound, an audit row is appended
  to `joint_alignment_cases.directory_invite_acceptances` so the
  mediator sees the acceptance on `/mine`.
- `400` — body malformed (missing `token`).
- `401` — bad or missing signature.
- `404` — unknown invite token (never leak whether a token was
  ever valid).
- `503` — server-side `SACOPARENTSALIGN_WEBHOOK_SECRET` not set.

**Idempotency:** safe to call twice. Second call returns
`applied=false` with a 200. Recommended: sibling site retries with
exponential backoff on network errors.

## Environment variables to set on production once the sibling ships

```env
SACOPARENTSALIGN_BASE_URL=https://sacoparentsalign.com
SACOPARENTSALIGN_API_KEY=<sibling-issued-bearer>
SACOPARENTSALIGN_WEBHOOK_SECRET=<shared 32+ char secret used by BOTH sides>
```

## What still lives as a mock on the SA CoParents side

- The 5-entry `_MOCK_DIRECTORY` roster in `professional_directory.py`.
  DELETE this list when the sibling endpoint returns data and the
  swap-out is complete.
