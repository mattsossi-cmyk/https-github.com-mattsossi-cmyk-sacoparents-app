# SA CoParents App ↔ SA CoParents Align — Link Contract (2026-10-14)

Status: implemented in Align behind **`PARENT_APP_LINK_CONTRACT`** (default `false` = legacy behaviour unchanged). Align code: `backend/parent_app_contract.py`, `backend/bridge_views.py`, `backend/integrations.py`. Secret values are never written here, in logs, or in error messages.

## 1. Headers Align sends on every call to the parent app (flag ON)
| Header | Value |
|---|---|
| `X-Integration-Key` | shared secret from env `INTEGRATION_SHARED_SECRET` (never logged) |
| `X-Professional-Id` | Align's stable professional user id (assigned professional / creator of the case) |
| `X-Case-Id` | Align `joint_reports.id` (omitted only on `aggregate`, where `case_id` is a query param) |
| `X-Professional-Email` | optional, legacy invitation matches only — **not sent today** (no legacy path wired) |

Flag OFF: only `X-Integration-Key` (current production behaviour).

## 2. Endpoints Align calls
| Call | Request | 200 response Align expects |
|---|---|---|
| `POST /api/integrations/verify-link-code` | body `{code, professional_id, case_id}` (flag OFF: `{code}`) | `{email}` |
| `GET /api/integrations/export-assessments?email=` | headers above | `{access_scope: "case" \| "legacy_unscoped", assessments:[…], statements:[…], safety_flags}` — on `legacy_unscoped` Align discards any `responses` and sets `safety_flags=null` even if present |
| `GET /api/integrations/safe-contact?email=` | headers above | `{access_scope:"case", safe_contact:{…}\|null}` — displayed live on the professional-only, access-logged screening-responses page; never stored, never in reports/PDFs/emails/exports |
| `POST /api/integrations/screening/assign` | body `{email, version: "A"\|"B"\|"C"}` | any 200 — fired after the professional assigns a version in Align; failures are logged, Align's own assignment still stands |
| `GET /api/integrations/aggregate?case_id=` | `X-Integration-Key`, `X-Professional-Id` | ratings only |

## 3. Refusals → what the Align user sees (neutral; no safety/screening/flag words)
| Parent app | Align | User-facing text |
|---|---|---|
| 401 invalid key | 502 | "The SA CoParents connection is not set up correctly. Please contact support." |
| 503 not configured | 503 | "The SA CoParents connection is not available right now. Please try again later." |
| 400 missing ids | 502 | same as 401 (configuration error; logged server-side without the secret) |
| 404 "Not found" (unknown email / unlinked / wrong case or professional / legacy parent asking for safe contact or raw answers) | 404 | "The SA CoParents service did not release information for this link. Ask the parent to confirm the link for this case, then try again." |
| 404 "No completed assessments found" | 404 | "No completed assessments were found for the linked SA CoParents account." |
| 404 "Invalid or expired link code" | 400 | "Invalid or expired link code" |
| network / other | 502 | "Could not reach the SA CoParents service. Try again later." |

Linking without a case while the flag is ON → 400 "Link your SA CoParents account from inside the case your professional invited you to."

## 4. Align inbound (parent app → Align), header `X-Integration-Key`
- `GET /api/integrations/case-invite/{token}` now also returns **`professional_id`** so new invitation links are tied to that professional.
- `POST /api/integrations/case-update`, `GET /api/integrations/safety-screening-spec` unchanged.

## 5. Tests
`backend/tests/test_iter106_parent_app_contract.py` (every refusal code, flag off/on, scope stripping, headers/body per endpoint, invite `professional_id`, bridge views hidden when flag off) + `test_iter99` bridge section updated. 29/29 passing.

## 6. Depends on the parent-app side being live
1. `verify-link-code` accepting `{professional_id, case_id}` and the two headers (otherwise linking fails with the neutral 400/404).
2. `export-assessments` returning `access_scope`; until then Align (flag ON) treats a missing scope as `legacy_unscoped` → summary only, no safety data imported.
3. `safe-contact`, `screening/assign`, `aggregate` endpoints existing (Align shows the neutral "not available / not released" messages until they do).
4. Both apps on the **same** `INTEGRATION_SHARED_SECRET` (rotation must be coordinated).
5. The parent app must bind link codes to the signed-in parent and verify parent↔case↔professional before releasing anything.

## 7. Fields Align still needs from the parent-app builder
- **`safe_contact` object**: Align currently renders `method`, `address`, `safe_times`, `voicemail_ok`, `code_word` if present. Please confirm exact keys, value types (free text vs enum), and whether `null` vs omitted means "prefer not to say".
- **Full `export-assessments` response**: exact shape of `assessments[]` (`assessment_id`, `type`/`title`, `completed_at`, `responses` key→value), `statements[]`, `safety_flags` (Align's importer expects `tier`, `concern_count`, `version`, `completed_at` and item responses — see `backend/safety_import.py`), `communication_readiness` if provided, and whether summaries appear under `summary` on `legacy_unscoped`.
- **`aggregate` response**: the exact `ratings` keys/scales so Align can label them.
- **`screening/assign` response** body and whether re-assigning a different version is allowed.
- Rate limits / IP allow-list, and the agreed secret-rotation procedure.
