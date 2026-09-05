# Integration Spec — sacoparentsapp.online → sacoparentsalign

**For the agent working in the sacoparentsapp.online Emergent project.**

sacoparentsalign (the Joint Alignment Report app) lets parents import their existing
sacoparentsapp.online assessments when creating a Joint Report, so they never redo an
assessment. This document specifies exactly what sacoparentsapp.online must implement.

## Shared Secret

Both projects authenticate server-to-server with one shared secret.
Add this exact line to sacoparentsapp.online's `backend/.env` (and its production env):

```
INTEGRATION_SHARED_SECRET="2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d"
```

Every integration endpoint must compare the `X-Integration-Key` header against this value
using a constant-time comparison (e.g. `hmac.compare_digest`) and return 401 on mismatch.
Never log the key. Never accept requests without it.

## Endpoint 1 — User generates a link code (session-authenticated)

```
POST /api/link-codes
Auth: the app's existing user session (cookie/JWT)
Response 200: {"code": "AB3K7Q2Z"}
```

- Generate an 8-character uppercase alphanumeric code (avoid ambiguous chars: 0/O, 1/I).
- Store ONLY a hash (SHA-256) of the code with: user id/email, `expires_at` = now + 15 minutes, `used` = false.
- UI: add a "Link to SA CoParents Align — Generate link code" button in the account/settings area that calls this and displays the code to the user.

## Endpoint 2 — Verify a link code (server-to-server)

```
POST /api/integrations/verify-link-code
Headers: X-Integration-Key: <shared secret>
Body: {"code": "AB3K7Q2Z"}
Response 200: {"email": "parent@example.com"}
Response 404: {"detail": "Invalid or expired link code"}
```

- Look up by code hash; must be unused and unexpired.
- On success: mark the code used (single-use) and return the owning account's email.
- sacoparentsalign stores that email as the account link.

## Endpoint 3 — Export assessments (server-to-server)

```
GET /api/integrations/export-assessments?email=parent@example.com
Headers: X-Integration-Key: <shared secret>
Response 200:
{
  "email": "parent@example.com",
  "assessments": [
    {"title": "...", "completed_at": "ISO-8601", "responses": {"<question/field>": "<answer text>", ...}}
  ],
  "statements": [
    {"title": "...", "content": "...", "created_at": "ISO-8601"}
  ]
}
Response 404: {"detail": "No completed assessments found"}
```

- Return ONLY completed assessments and finalized statements for that account.
- All response values should be plain text (strings). Non-text values are stringified by the importer.
- Do NOT include other users' data or any credentials.

## How sacoparentsalign uses this

1. Parent generates a link code on sacoparentsapp.online, pastes it in sacoparentsalign
   (Joint Assessment page → "Link Accounts").
2. sacoparentsalign calls Endpoint 2 and stores `{user_id, external_email}` in `account_links`.
3. During a Joint Report, the parent clicks "Import My Assessment"; sacoparentsalign calls
   Endpoint 3 and stores the payload as that parent's completed side (`imported: true`).
4. The report engine compares both parents' material (free-text or imported) via theme
   analysis and produces the Joint Parenting Alignment Report. Parents never see each
   other's raw imported material — only the generated comparison.

## Notes

- All calls are server-to-server over HTTPS; parents never handle tokens.
- Link codes are single-use and expire in 15 minutes.
- The same confidentiality rules apply: imported material stays private to the importing
  parent until they choose to participate in a Joint Report comparison.
- sacoparentsalign also uses Endpoint 3 to pre-fill private (individual) assessments with the
  parent's saved answers (Wizard "Load my saved answers" panel), so parents never re-enter material.

## Case-based flow (added 2026-09-05) — Align creates the case, App delivers the assessment

Professionals create a Joint Alignment Case in Align (`POST /api/joint/reports/professional`).
Align generates the case/invitation code (`SA-XXX-NNNNNN`, e.g. SA-EDU-482731) and one secure
invitation token per parent. Parents never type anything: the invitation email's
"Complete My Assessment" button links to the App when `SACOPARENTS_APP_ASSESSMENT_URL` is set
(`{SACOPARENTS_APP_ASSESSMENT_URL}/assessment?invite=<token>`), otherwise to Align's /join page.
The case code is the backup method.

Align exposes two server-to-server endpoints (header `X-Integration-Key: <INTEGRATION_SHARED_SECRET>`):

1. `GET /api/integrations/case-invite/{token}` — resolve an invite token. Returns
   `{case_id, report_id, assessment_type, child_name, parent_role, parent_name, parent_email,
   professional_name, requested_by, invitation_status, case_status}` so the App can render
   "Requested by [professional]" and know which case → parent → assessment.
2. `POST /api/integrations/case-update` — App pushes status. Body:
   `{token, status: "started"|"completed", assessment_id, responses: {…comparison fields…}}`.
   "started" moves the case to in_progress; "completed" stores the parent's comparison fields as
   their private completed side (`imported: true`). When both sides are complete the case becomes
   "ready" and the professional is emailed a "Generate Joint Alignment Report" link.

The App keeps raw assessment answers in its own database; Align only receives the comparison
fields. One parent's material is never exposed to the other — only the generated comparison
appears in the Joint Alignment Report. Align case data model additions on joint_reports:
`case_code` (shown to participants), `case_reference` (optional, professional-only, never
returned to parents), responses.{a|b}.imported/external as with account-link imports.
