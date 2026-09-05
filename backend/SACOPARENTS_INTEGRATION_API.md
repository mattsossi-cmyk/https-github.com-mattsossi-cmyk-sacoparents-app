# SA CoParents → SA CoParents Align — Integration API

**Base URL:** `https://sacoparentsapp.online`
**Contact:** mattsossi@bsossi.com
**Schema version:** `1`

All three endpoints are live under `/api`. Endpoints 2 and 3 are
server-to-server only — they require the shared secret. Endpoint 1 is
parent-facing and requires the parent's JWT (they call it from
inside their SA CoParents account).

## Authentication

| Endpoint | Auth |
|---|---|
| `POST /api/link-codes` | `Authorization: Bearer <parent JWT>` |
| `POST /api/integrations/verify-link-code` | `X-Integration-Key: <shared secret>` |
| `GET  /api/integrations/export-assessments` | `X-Integration-Key: <shared secret>` |

The shared secret is a 64-character hex string. It is compared with
`hmac.compare_digest` (constant time) on the server. Wrong or missing
key → **401 Unauthorized**. If the server has not been configured
with `INTEGRATION_SHARED_SECRET`, it responds **503 Service
Unavailable** rather than silently accepting anything.

---

## 1. `POST /api/link-codes`

**Called from** the SA CoParents app when the parent taps
*"Link my SA CoParents Align account"* in their account settings.

**Auth:** parent JWT. Guest accounts cannot mint (`403`).

**Rate limit:** 5 mints per parent per hour (`429`).

**Behaviour:**
* Mints a single-use 8-character code from a curated alphabet
  (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789` — no `I`, `O`, `1`, `0`).
* Stores a bcrypt hash of the code; the raw code is only ever
  returned in this response.
* TTL: **15 minutes** from mint.
* Minting a new code marks any previous unused code from the same
  parent as `superseded` — only the most recent code will verify.

**Request body:** none.

**Response 200:**

```json
{ "code": "V2TFFB6W" }
```

---

## 2. `POST /api/integrations/verify-link-code`

**Called from** the SA CoParents Align backend after the parent
pastes the code into the sibling app.

**Auth:** `X-Integration-Key: <shared secret>`.

**Behaviour:** looks up the unconsumed, non-expired code by iterating
bcrypt hashes; on match, marks it consumed (`consumed_reason:
"verified"`) and returns the parent's email.

**Codes are single-use.** A second call with the same code → `404`.

**Request body:**

```json
{ "code": "V2TFFB6W" }
```

**Response 200:**

```json
{ "email": "parent@example.com" }
```

**Errors:**
* `401` — missing or wrong `X-Integration-Key`
* `404` — code not found, expired, or already consumed
* `503` — server has no `INTEGRATION_SHARED_SECRET` configured

---

## 3. `GET /api/integrations/export-assessments`

**Called from** the SA CoParents Align backend to pull the linked
parent's assessment bundle.

**Auth:** `X-Integration-Key: <shared secret>`.

**Query param:** `email` (required) — the email returned by step 2.

**Behaviour:** returns a reconciled JSON bundle. Only the parent's
own material — never any co-parent data, never any safety-screen
answers, never any free-text notes from the Communication
Reflection.

**Response 200:**

```json
{
  "parent": {
    "email": "parent@example.com",
    "name": "Sam Parent"
  },
  "situation_snapshot": {
    "situation_focus": "cooperate",
    "child_goals": { "focus": "cooperate", "topics": [...], "notes": "..." },
    "issues": { "selected": [...], "notes": "...", "priority": [...] },
    "priority": { "issue": "...", "why": "...", "outcome": "..." },
    "comm_style": { "style": "...", "notes": "..." },
    "readiness": { "score": 78, "reflection": "..." },
    "completed_sections": ["child_goals", "issues", "priority", "readiness"],
    "updated_at": "2026-03-04T17:22:11+00:00"
  },
  "foundation_statement": {
    "child_lens": "...",
    "my_part": "...",
    "best_case": "...",
    "coparent_lens": "...",
    "updated_at": "2026-03-04T17:22:11+00:00"
  },
  "special_needs": {
    "medical": {
      "profile": { ... },
      "foundation_statement": "...",
      "questions_for_provider": [...],
      "rating_areas": [...],
      "signals": {...},
      "generated_at": "2026-02-22T12:00:00+00:00"
    },
    "educational": { ... } | null,
    "psychological": { ... } | null
  },
  "exported_at": "2026-03-04T17:23:00+00:00",
  "schema_version": 1
}
```

**Field notes for the sibling app:**
* Any lane the parent has not completed under `special_needs` will be
  `null`. Render conditionally.
* `situation_snapshot.completed_sections` tells you which mediation
  prep sections the parent has finished — safe for rendering "not
  completed yet" badges.
* All timestamps are ISO 8601 UTC.
* `schema_version` will only ever bump when the shape changes in a
  non-backward-compatible way. Additive fields will not bump it.

**Errors:**
* `400` — missing `email` query param
* `401` — missing or wrong `X-Integration-Key`
* `404` — no parent found for that email
* `503` — server has no `INTEGRATION_SHARED_SECRET` configured

---

## End-to-end staging test

A runnable Python script lives at
`/app/backend/scripts/test_sibling_integration.py`. Point it at
`https://sacoparentsapp.online`, provide the shared secret via env
var, and it will:

1. Log in as a test parent → get JWT.
2. Call `POST /api/link-codes` → capture the 8-char code.
3. Call `POST /api/integrations/verify-link-code` with the shared
   secret → assert response contains the parent's email.
4. Call `GET /api/integrations/export-assessments` → assert every
   required top-level key is present and `schema_version == 1`.
5. Attempt a second verify with the same code → assert `404`.
6. Attempt a call without the shared secret → assert `401`.

Usage:

```bash
export INTEGRATION_SHARED_SECRET=... # 64-char hex secret
export TEST_PARENT_EMAIL=parent1@test.com
export TEST_PARENT_PASSWORD=TestPass123!
python /app/backend/scripts/test_sibling_integration.py
```

---

## Rate-limit / operational notes for the sibling team

* Please cache the `export-assessments` response on your side for at
  least 5 minutes so repeated Alignment Report renders don't hammer
  our API.
* If you need to re-pull an updated snapshot, mint a fresh link code
  through the parent — do not attempt to re-use an old code, and do
  not attempt to guess the parent's user_id.
* If we ever rotate the shared secret we will email
  `mattsossi@bsossi.com` 7 days in advance with the new value.
