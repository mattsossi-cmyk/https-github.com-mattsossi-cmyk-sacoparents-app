# SA CoParents App ↔ SA CoParents Align — Requester-Context Contract (for review)

Status: **DRAFT — flag `BRIDGE_REQUESTER_CONTEXT` is OFF.** Nothing below is enabled until both builders confirm and the tests in §7 pass.
Source of truth for Align's side: `backend/integrations.py`. Secret values are never written in this file.

## 1. Authentication (current, both directions)
| Item | Value |
|---|---|
| Scheme | Static shared key, one per environment |
| Header | `X-Integration-Key: <INTEGRATION_SHARED_SECRET>` |
| Verification (Align inbound) | constant-time compare (`secrets.compare_digest`); mismatch → `401 {"detail":"Invalid integration key"}` |
| Env var (Align) | `INTEGRATION_SHARED_SECRET` (rotation: both apps together) |
| Transport | HTTPS only; Align calls `SACOPARENTS_APP_URL = https://sacoparentsapp.online` |

Open dependency: the parent app must also verify this header on `verify-link-code` and `export-assessments` and MUST reply `401/403` (not 200) when the requester is not authorized for that parent/case. Align maps any 401/403 to the neutral message in §5.

## 2. Requester context Align will send when the flag is ON
Headers (added to every outbound call):
```
X-Requester-App: sacoparentsalign.com
X-Requester-Professional-Id: <Align user id of the assigned professional>   (omitted if not a professional)
X-Requester-Case-Id: <Align joint_reports.id>                                 (omitted at link stage)
X-Requester-Parent-Role: a | b                                                (omitted at link stage)
```
Nothing else is added: no names, no answers, no child details, no safety data.

## 3. Outbound calls (Align → Parent app)
### 3a. `POST {SACOPARENTS_APP_URL}/api/integrations/verify-link-code`
Request body:
```json
{ "code": "ABCD1234",
  "requester": { "app": "sacoparentsalign.com", "professional_id": "<id>" } }   // "requester" only when flag ON
```
Expected response `200`: `{ "email": "parent@domain" }` (email is the only field Align reads).
Other: `401/403` → Align `403` neutral; any other non-200 → Align `400 Invalid or expired link code`.

### 3b. `GET {SACOPARENTS_APP_URL}/api/integrations/export-assessments`
Query: `email=<linked parent email>` plus, when flag ON: `professional_id`, `case_id`, `parent_role`.
Expected response `200`:
```json
{ "assessments": [ { "assessment_id": "...", "type": "...", "completed_at": "...", "responses": {...} } ],
  "statements":  [ ... ] }
```
`404` → Align `404 No completed assessments found…`; `401/403` → neutral `403`; other → `502`.

## 4. Inbound calls (Parent app → Align) — header `X-Integration-Key` required
| Route | Request | Response |
|---|---|---|
| `GET /api/integrations/safety-screening-spec` | — | canonical Version A/B/C spec (wording, tiers) |
| `GET /api/integrations/case-invite/{token}` | path token | `{case_id, report_id, assessment_type, child_name, parent_role, parent_name, parent_email, professional_name, requested_by, invitation_status, case_status}`; `404` invalid, `410` expired |
| `POST /api/integrations/case-update` | `{token, status, assessment_id?, responses?}` | `{ok, case_status}`; every write is logged (`access_events.kind="integration_write"`, no PII) and an admin alert email is sent |

## 5. Neutral denial (Align → user)
`403 {"detail": "The SA CoParents service did not release this parent's data for this case. Ask the parent to confirm the link with you, then try again."}`

## 6. Identity, membership and permission checks
| Check | Align | Parent app (to confirm) |
|---|---|---|
| Parent identity | Align JWT session; link stored in `account_links{user_id, external_email}` | Link code issued to a signed-in parent; must bind code → parent account |
| Professional identity | `X-Requester-Professional-Id` = Align user with role professional/admin | Must verify the parent has confirmed *this* professional (consent record) |
| Case membership | Import route checks the caller's role on `joint_reports` (`report_role`) | Must verify `case_id` ↔ parent ↔ professional mapping before releasing data |
| Other parent isolation | Imported responses are stored under `responses.<role>` only; the other parent never reads them | Must never return Parent A's data for a `parent_role=b` request |
| Safety-sensitive cases | Safety screenings are never exported over the bridge in either direction; safe-contact data never leaves Align | Confirm no family-violence/safety data is included in `export-assessments` |
| Separation of layers | Raw imports → `responses`; AI summaries → joint engine; court output only after professional review (court submission gate) | — |
| Audit | `access_events` on every bridge write; report access log on every read | Must log every release with requester identifiers |

## 7. Required tests before enabling the flag
1. Valid key + valid requester → 200 and data for the correct parent only.
2. Valid key, requester professional not confirmed by parent → 401/403 → Align shows neutral 403.
3. Valid key, `parent_role` mismatch → 401/403.
4. Missing/invalid key → 401 both directions.
5. `case-update` with `responses` → `access_events` record + admin alert; no answer content in the alert.
6. Safety screening / safe-contact fields absent from every bridge payload (schema assertion).
7. Flag OFF regression: current behaviour unchanged (`test_iter99_pause_safecontact_bridge.py`).

## 8. Outstanding items for the parent-app builder
- Confirm header names in §2 or publish alternatives (Align changes them in one place: `REQUESTER_HEADERS`).
- Publish the consent model: how a parent confirms a professional, and how long that authorization lasts.
- Publish exact JSON schemas for `verify-link-code` and `export-assessments` responses.
- Confirm rate limiting / IP allow-list on the parent-app side (Align has a single static key today).
- Agree a joint rotation procedure for `INTEGRATION_SHARED_SECRET`.
