# SA CoParents Align — Build Spec (Companion to sacoparentsapp.online)

This is the **Align-side build brief**. It pairs with the SA CoParents
App integration surface documented in
`/app/backend/SACOPARENTS_INTEGRATION_API.md`.

**Golden rule**: Align **must not** touch the SA CoParents App
database directly. Every read/write goes through the four HTTP
endpoints listed under "Integration surface" below. This is what
keeps the two systems independently deployable and independently
auditable.

---

## 1. What Align owns

Align is the professional-facing platform. It owns:

- **Professional accounts** (mediators, attorneys, therapists,
  parenting facilitators). Auth is Align's problem.
- **Joint Alignment Cases** — Align is the source of truth for the
  case identifier, the two parent invitations, the professional's
  private case reference, and the case status timeline.
- **Joint Alignment Reports** — the 10-page comparison artefact
  Align generates *after* both parents have completed on the App.
- **Email delivery of parent invitations** — the emails go out
  from Align's transactional email provider, never from the App.

## 2. What the App owns (do not touch)

The SA CoParents App owns:

- Parent user accounts and credentials.
- Every parent's private assessment answers, reflections, and
  journal entries.
- The individual (single-parent) reports.
- The `/join/:token` and `/join` landing pages parents see when
  they click the invitation email or enter the code.

Align **never** logs the parent in, never mints password reset
tokens for them, and never receives the raw assessment answers of
either parent unless the App explicitly returns them on the
data-minimised export.

---

## 3. Professional workflow (build this on Align)

### 3.1 Professional dashboard — "New Joint Report"

Form the professional fills in:

| Field | Type | Required |
|---|---|---|
| Assessment type | Select: Co-Parenting / Communication / Educational / Medical / Psychological / Special Needs | Yes |
| Parent A email | Email | Yes |
| Parent A display name | Text | Optional |
| Parent B email | Email | Yes |
| Parent B display name | Text | Optional |
| Private case reference | Text (visible only to the professional) | Optional |

Server-side, Align:

1. Calls `POST https://sacoparentsapp.online/api/integrations/joint-alignment/cases`
   with header `X-Integration-Key: <shared secret>` and body:
   ```json
   {
     "assessment_type": "educational",
     "professional": {
       "id": "align-pro-<uuid>",
       "name": "Jane Smith, LPC",
       "email": "jane@example.com"
     },
     "align_case_reference": "Smith / v. / Jones — March 2026",
     "parents": [
       {"email": "parent-a@example.com", "name": "Alex Parent"},
       {"email": "parent-b@example.com", "name": "Blake Parent"}
     ]
   }
   ```
2. Receives back the `case_id` (`SA-XXXXXX`, 6 digits) and two
   `invitation_url` values, one per parent.
3. Persists the case in its own DB **with the `case_id` from step 2 as
   the primary identifier** — never mints its own.
4. Sends two separate emails (see 3.2). Each parent's email contains
   *only that parent's* `invitation_url` and the same
   human-readable `case_id` as a backup.

### 3.2 Parent invitation email (Align sends)

Subject: `Invitation to Complete Your SA CoParents Assessment`

Body:

> You have been invited to participate in an SA CoParents Joint
> Alignment Report.
>
> Your private participation code is: **SA-482731**
>
> [Complete My Assessment] ← button links to the parent-specific
> `invitation_url` returned by the App
>
> Your individual responses are completed privately. Your co-parent
> will complete their own assessment separately. The Joint
> Alignment process is designed to identify areas of shared
> understanding, differences in perspective, and issues that may
> benefit from further discussion.
>
> Please do not forward this invitation or share your sign-in
> credentials.

**Never** put the parent's user_id, token, or any assessment
content in the email body. The invitation_url alone is enough.

### 3.3 Professional case dashboard row

Poll (or subscribe to Phase C webhook) the App's
`GET /api/integrations/joint-alignment/cases/{case_id}` endpoint.
Render on the professional's dashboard:

```
Assessment:            Educational
Case ID:               SA-482731
Status:                In progress
Parent A — Alex        Completed ✓
Parent B — Blake       Awaiting completion
Joint Report:          Pending
[Send Reminder]        [Generate Report — disabled until both complete]
```

Reminder button on Align's side re-sends the invitation email —
**the App has no reminder endpoint**; Align owns email delivery.

### 3.4 Report generation (when both complete)

When the case status returned by the App is `both_complete`, the
same status endpoint additionally returns:

```json
{
  "status": "both_complete",
  "assessments": [
    {"email": "parent-a@example.com", "parent_slot": "A", "assessment": { ... }},
    {"email": "parent-b@example.com", "parent_slot": "B", "assessment": { ... }}
  ],
  "schema_version": 1
}
```

The `assessment` objects contain **only the lane the case was
opened for** — never the parent's other assessments, foundation
statement, mediation prep answers, or free-text notes.

Align then generates the 10-page Joint Alignment Report:

1. Alignment (shared understanding)
2. Differing perspectives
3. Child needs
4. Options & resources
5. Questions to discuss
6. Suggested action steps

Report artefacts stay on Align — the App never renders them.

---

## 4. Integration surface (App HTTP endpoints)

**Base URL:** `https://sacoparentsapp.online`
**Auth for server-to-server:** `X-Integration-Key: <shared secret>`
The secret is a 64-char hex value shared out of band. Constant-time
compared server-side.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/integrations/joint-alignment/cases` | Create case, receive `case_id` + invitation URLs. |
| GET | `/api/integrations/joint-alignment/cases/{case_id}` | Poll case status. Payload includes assessments only when both parents complete. |

Full schemas: see `/app/backend/SACOPARENTS_INTEGRATION_API.md`.

---

## 5. Non-negotiable guardrails

1. **Data minimisation** — do not request assessments Align does
   not need. If a case is for the Educational lane, only the
   Educational report comes back.
2. **No shared DB** — every read/write between the two systems is
   an HTTP call authenticated with the shared secret.
3. **The visible `SA-XXXXXX` code alone is never sufficient.**
   The App only associates an invitation with an account when the
   parent is authenticated and their email matches the invitation
   email.
4. **Do not leak PII in preview** — the App's public
   `/api/joint-alignment/invitation/{token}` endpoint deliberately
   does not include email addresses or the other parent's name.
   Align must not reintroduce that leakage from its side.
5. **Reminders and emails live on Align.** The App does not send
   Joint Alignment reminders. If Align cancels a case, it must
   inform the App (Phase C — cancellation endpoint TBD).
6. **Rotate the shared secret annually** and coordinate the swap
   with 7 days notice to `mattsossi@bsossi.com`.

---

## 6. What's coming in Phase C

Currently missing (to be built together in the next phase):

- **App → Align completion webhook**: the App posts to Align the
  moment a parent finishes an eligible assessment. Requires Align
  to publish an inbound webhook URL and a secret. Env var on the
  App side: `ALIGN_COMPLETION_WEBHOOK_URL` (placeholder).
- **Align → App cancellation endpoint**: when a professional
  cancels a case, mark all invitations expired.
- **Reminder cadence** for Align to re-send invitations.

---

## 7. Branding rules

The two domains present as one connected system:

- **SA CoParents App** — "Reflect"
- **SA CoParents Align** — "Compare • Understand • Align"
- Umbrella tagline: **Start With Alignment. End With Agreement.**

Use the same purple `#3D1A78`, the same serif headline treatment,
and the same neutral, mediator-ready copy. When the parent lands
on the App from an Align email, they should never feel like they
crossed a domain boundary.
