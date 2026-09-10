# Case ID Architecture — SA CoParents Align ⇄ SA CoParents App

Align owns the **case**; the App owns each parent's **private reflection**. The Case ID is the only thread that reconnects them.

## Identifiers

| Thing | Format | Who sees it |
|---|---|---|
| Master Case ID (`joint_reports.case_code`) | `SA-YY-PFX-XXXXXX` e.g. `SA-26-COP-K7M4Q2` (PFX = subject: COP, COM, EDU, MED, PSY, SAF, MDN, ALN=multi, AGR=agreement; 6 chars from an unambiguous alphabet, non-sequential) | Professional; printed on reports + QR verification |
| Professional case reference (`case_reference`) | free text | Professional only — never sent to parents or the App |
| Parent invitation token (`invitations.token`) | 32-char URL-safe secret, **one per parent** | Only that parent (inside their link) |
| Parent short code (`invitations.code`) | shared case code (owner choice) — email-matched on entry | Parent |

Parents never type or see each other's token. The backend maps `token → (case_code, parent_role)`.

## Collections (MongoDB)

```
joint_reports  (CASES)          invitations  (INVITATIONS)         joint_reports.responses.{a|b}  (ASSESSMENTS)
  id, case_code, case_reference    id, report_id → joint_reports.id     answers{}, completed_at, imported,
  professional_id, subject(s)      role a|b, invitee_name/email         assessment_id (App), source
  participants.a/.b (name,email,   token, code, status pending|accepted
    user_id)                       |cancelled, created_at, expires (14d)
  status, report_generated_at
  created_at
```

Derived `case_status` (returned on every report object): `DRAFT → INVITED → ONE_COMPLETE → READY_FOR_ALIGNMENT → REPORT_GENERATED` (`CLOSED` reserved).

## Handoff: Align → App (invitation)

Invitation email link: `https://sacoparentsapp.online/?invite=<token>` (or Align's `/join/<token>` which forwards).
The App resolves it server-side:

```
GET {ALIGN}/api/integrations/case-invite/{token}
X-Integration-Key: <INTEGRATION_SHARED_SECRET>
→ { case_id: "SA-26-COP-K7M4Q2", report_id, assessment_type, child_name, parent_role: "a"|"b",
    parent_name, parent_email, professional_name, invitation_status, case_status }
```
The App must only let the signed-in user whose email matches `parent_email` proceed, and must not display the other parent's identity beyond the first name already in the case.

## Handoff: App → Align (completed assessment)

```
POST {ALIGN}/api/integrations/case-update
X-Integration-Key: <INTEGRATION_SHARED_SECRET>
{ token, status: "started" | "completed", assessment_id, responses: { question_key: answer } }
```
Align stores the answers under `responses.<role>` of the case identified by the token, marks the invitation accepted, and recomputes status. When both roles are complete → `READY_FOR_ALIGNMENT` and the professional's dashboard enables **Generate Joint Alignment Report**. The first on-screen view or PDF download stamps `report_generated_at` → `REPORT_GENERATED`.

## Privacy invariants
- `responses.a` is never returned to parent B and vice-versa; the comparison engine only emits neutral alignment/difference statements.
- Safety subjects (`SAF`, `RSK`, …) never auto-generate a joint report; they route to the professional.
- Tokens are single-purpose, expire after 14 days (reissue = new token), and are hashed-equivalent secrets — never logged.
