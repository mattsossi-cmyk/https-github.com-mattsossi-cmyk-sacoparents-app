# Foundation Statements from the parent app → Align (PREVIEW ONLY — not deployed, notice NOT published)

Owner request 2026-10-27. Status: implemented in preview, tests green (`backend/tests/test_iter124_foundation_push.py`, 4 tests).

## 1. Endpoint and exact body accepted

`POST https://<align>/api/integrations/case-update` · header `x-integration-key: <INTEGRATION_SHARED_SECRET>` (same key as readiness push; value never printed)

```json
{
  "token": "<the parent's own invitation token>",
  "status": "foundation",
  "foundation_statement": {
    "completed_at": "2026-10-26T10:00:00Z",
    "title": "Mother's Foundation Statement",
    "content": "Free text, up to 5000 characters (truncated, not rejected)",
    "fields": {
      "child_name": "Avery",
      "shared_purpose": "...", "vision": "...", "strengths": "...", "child_may_need": "...", "future": "...", "parent_commitment": "...",
      "priorities": ["one per item"], "needs": ["..."], "concerns": ["..."], "wellness_tech": ["..."], "commitments": ["..."], "goals": ["..."]
    }
  }
}
```

Rules
- `token` is the ONLY thing that decides parent + case: Align reads the invitation record (`invitations.token → role a|b, report_id`). Any `parent`, `role`, `author`, `parent_email` in the body is ignored (test proves a body claiming "Father" with Mother's token lands on Mother's side only).
- `status` may be omitted when `foundation_statement` is present and `responses`/`communication_readiness` are absent.
- `content` and/or `fields` required; `fields` is whitelisted to the 13 Foundation keys (anything else dropped); `title` ≤120 chars, default "Child-Focused Foundation Statement"; `completed_at` normalised to YYYY-MM-DD.
- Responses: 200 `{"ok": true, "case_status": "<unchanged>"}` · 401 wrong/missing key · 404 unknown token or case · 400 nothing usable / unknown status.
- Overwrite: a new push for the same token replaces that parent's held statement only. The other parent's held statement, answers and case status are never touched.
- Audit: `access_events` gets `kind: integration_write, role, fields: ["foundation_imports"]` (no content) and the admin inbox email "Bridge write on Case …" (no content).

## 2. Before / after (storage)

| | Before | After |
|---|---|---|
| Push arrives | No route for Foundation Statements (`status` other than started/completed/readiness → 400) | Stored at `joint_reports.foundation_imports.<role>` = `{title, content, structured|null, completed_at, received_at, source: "sacoparentsapp.online", invitation_id}` |
| Shared into the case | Only via the parent's Align Foundation editor (`/foundation` → Share) or typing text in the agreement form | Unchanged paths **plus** the parent's explicit choice to use the held statement: `POST /joint/reports/{id}/foundation/use-import` or `PUT …/responses` with `"foundation": [{"use_import": true}]` (server copies the held text; client text ignored) |
| Push itself shares anything | n/a | **No.** The push never writes `responses.<role>.foundation`, never changes case status, never notifies the professional |

## 3. Who in Align can see each statement today

| Viewer | Held statement (received, not yet included) | After the parent includes it (same as any shared Foundation Statement today) |
|---|---|---|
| The parent it belongs to | Yes — own case page shows "arrived on <date>", text, Use/Include button (`my_foundation_import`) | Yes |
| The other parent | **No** (never serialised for the other side; test asserts Mother's text absent from Father's views and vice-versa) | **Yes, verbatim** — once both sides are complete, the Co-Parenting Agreement / Joint Report shows included Foundation Statements to both parents (screen + PDF "Foundation Statements" block) |
| Assigned professional / case creator | **No** (not in `foundation_statements`, not in `/report`, not in the PDF; no "arrived" flag either) | Yes — case page "Foundation Statements" panel, report, PDF, per-side Foundation PDF; each day's view is logged ("Viewed Foundation Statement(s) on case page") |
| SA CoParents administrators | Database only (no admin screen reads `foundation_imports`) | Same as professional when they open the case |
| Justice Portal / court | **No** | Only inside a frozen court submission the professional authorises — the frozen Agreement/Joint Report PDF includes any Foundation Statements that were included at that time; the Professional Legal Report may quote up to 2000 chars under "Foundation Statement (parent's own words)" |
| AI tools | **No** | Agreement clause drafting (gpt-5.4-mini) receives proposals/follow-ups only — not Foundation text. Jev safety-language scoring runs only on statements written in the Align editor, not on pushed ones |
| Emails | Never | Never (no Foundation text in any email) |

Safety: inclusion is refused (409, safety-pathway message) when that parent's side is safety-flagged on the case (`safety_flags.<role>` or `responses.<role>.safety_route`). The push itself is still accepted and held.

## 4. How it appears when building the Co-Parenting Agreement

Before the parent submits (`/joint/{id}/assess`): the "Foundation Statement (optional)" card shows a purple notice — "Your Foundation Statement from the SA CoParents app arrived on 2026-10-26. **Nobody in Align can see it until you include it.**" with **Use this statement** (loads the text, editable). The include checkbox stays OFF by default with the existing warning: "If you include it, your co-parent will see it in the agreement. The professional on your case can also read it there." Unedited text is sent as `{"use_import": true}` (server copy, source = sacoparentsapp.online); edited text is sent as the parent's own words.

After submitting (`/joint/{id}`): the "Your Child-Focused Foundation Statement" block shows "A Foundation Statement from the SA CoParents app arrived for you on <date>. Nobody in Align can see it until you include it." with **Include it in this case**. Once included the block disappears and the statement appears to the professional immediately and to both parents in the generated agreement (section "Foundation Statements" on screen and in the PDF; structured items such as wellness/strengths/commitments also feed the court-style agreement PDF panels like "Raised in the parents' Foundation Statements").

## 5. DRAFT Notification wording — NOT published, NOT wired

### Parent Privacy Notification — proposed version `2026-10-27.1` (current live: 2026-10-20.1)
Point 1 "Your individual answers remain private." — replace body with:
> Your co-parent never sees your assessment answers or your safety check-in. Your Foundation Statement stays private unless you choose to share it. If you write a Foundation Statement in the SA CoParents app and send it to Align, Align holds it for you alone: your co-parent, the professional and the court cannot see it until you choose to include it in your case. Once you include it, it appears in the joint report or co-parenting agreement that both parents and the professional can read, and it can be part of a report a professional submits to a court. You can send an updated statement from the app at any time; it replaces only your own earlier one.

### Professional Notice — proposed version `2026-10-27.1` (current live: 2026-10-22.1)
Add to "Access Is Visible to Parents" (or a new point "Foundation Statements"):
> A parent may send a Foundation Statement from the SA CoParents app. It is held privately for that parent and is not shown to you, the other parent or the court until the parent includes it in the case. You are not told that one has arrived. Once included, it appears on the case page, in the report and in the PDF exactly like a statement written in Align, and your views are recorded in the case activity log.

### Public Privacy Policy (`/privacy-policy`) — one sentence to add under data we receive from the SA CoParents app
> With your choice in the SA CoParents app, your Foundation Statement can be sent to Align, where it is held privately for you until you include it in your case.

## 6. Tests (`backend/tests/test_iter124_foundation_push.py`, all passing in preview)
1. `test_auth_and_validation` — 401 wrong key; 404 unknown token; 400 missing/blank statement; 400 unknown status; nothing stored.
2. `test_stored_against_invitation_parent_never_request_fields` — Mother's token + body claiming Father → stored on side a only; whitelist drops `ssn`/`role`; `invitation_id` recorded; Father's push lands on b with a untouched; Mother's second push overwrites a only; 9000-char content truncated to 5000; audit event has no content; push shares nothing.
3. `test_private_until_parent_includes_then_visible_to_case` — professional view/report/PDF contain neither statement before inclusion; each parent sees only their own; Father's `use-import` writes `responses.b.foundation` only (source sacoparentsapp.online), Mother's stays private; professional → 403, outsider → 404/403; after inclusion professional + both parents see Father's only.
4. `test_use_import_requires_statement_and_respects_safety_flag` — 404 when nothing held; 409 when side is safety-flagged; `{"use_import": true}` on the agreement form copies the held text and ignores client text; Father asking to use a statement he never sent → 404 and his answers are not saved.

## 7. Still open (not done here)
- The older pull import (`POST /joint/reports/{id}/import` / `export-assessments`) still stores the parent app's broader payload; unchanged and still flagged as a privacy concern.
- Parent-app side: keep sending OFF until coordinated preview-to-preview test with one test family.
- Counsel review of the draft wording above before any publish.
