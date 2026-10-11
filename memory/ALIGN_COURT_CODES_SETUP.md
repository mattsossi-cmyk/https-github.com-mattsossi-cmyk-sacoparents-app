# Align → SA CoParents: court codes with requested assessments

For the sacoparentsalign.com team. Base URL (live): `https://sacoparentsapp.online/api`

## Authentication
Every call is server-to-server and must send the header `X-Integration-Key: <INTEGRATION_SHARED_SECRET>`.
The value is the shared secret already configured for the existing Align integration (link codes, exports).
Never put it in browser code. Missing/wrong key → `401`; not configured on our side → `503`.

## 1. Create or update a court code — `POST /integrations/court-keys`
```json
{
  "key": "COURT-8842",
  "case_id": "ALIGN-CASE-123",
  "mediator_name": "Dana Reyes",
  "expires_at": "2026-12-31T23:59:59Z",
  "requested": ["coparent", "self", "medical"]
}
```
- `key` (3–80 chars): the code the parent types. We store only a SHA-256 hash (case-insensitive, trimmed).
- `case_id` (1–80 chars): your case reference; used to read progress back.
- `mediator_name` (optional): shown to the parent as "Professional: …".
- `expires_at` (optional, ISO 8601).
- `requested` (optional, up to 7): the assessments to tick for the parent. Allowed keys:

| key | Shown to the parent as |
|---|---|
| `coparent` | Co-Parenting Assessment |
| `self` | Self-Assessment |
| `educational` | Educational Assessment |
| `medical` | Medical Assessment |
| `psychological` | Psychological Assessment |
| `foundation` | Foundation Statement |
| `parallel` | Parallel Parenting Plan |

Calling again with the same `key` updates it (idempotent). Unknown keys → `422`.
Response: `{"case_id": "ALIGN-CASE-123", "requested": ["coparent", "self", "medical"]}`

## What the parent does
Sign in at sacoparentsapp.online → Court Ordered → "Accept Your Court-Ordered Invite" → enter the code as the
Court Reference Number. The requested items are ticked as "Asked by my professional". The parent may untick one; they see a
gentle note that the professional asked for it.

## 2. Read progress (status only) — `GET /integrations/court-keys/{case_id}/progress`
```json
{
  "case_id": "ALIGN-CASE-123",
  "requested": ["coparent", "self", "medical"],
  "revoked": false,
  "parents": [
    {"name": "Jordan Parent", "assessments": [
      {"key": "coparent", "title": "Co-Parenting Assessment", "status": "done", "finished_at": "2026-06-02T15:04:00+00:00"},
      {"key": "self", "title": "Self-Assessment", "status": "in_progress", "finished_at": null},
      {"key": "medical", "title": "Medical Assessment", "status": "todo", "finished_at": null}
    ]}
  ]
}
```
- `status` is `done` | `in_progress` | `todo` (show as Done / In progress / Not started).
- No answers, scores, reflections, child details or safety information are ever returned.
- `parents` lists only parents who have entered the code (empty until then). `name` is the legal name the parent typed on their Court page.
- Only codes created through endpoint 1 are readable here; codes professionals create inside SA CoParents return `404`.

## Weekly reminders (no action needed)
Mondays 9am Central, parents with requested-but-unfinished items get "You have N assessments waiting for you" with a
Sign in button and an unsubscribe link. No assessment names. Never sent to safety-flagged parents; stops once everything requested is done.
