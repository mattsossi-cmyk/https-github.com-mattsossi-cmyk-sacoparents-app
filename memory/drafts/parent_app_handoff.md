# Handoff to the SA CoParents parent app — Foundation Statement push to Align

Status: Align side is built and tested in PREVIEW. Production (sacoparentsalign.com) is currently returning 503 at the edge — keep SENDING SWITCHED OFF until Align confirms the go-ahead. For the coordinated test, send to the Align PREVIEW URL first.

## Endpoint
- Preview (coordinated test): `POST https://align-report.preview.emergentagent.com/api/integrations/case-update`
- Production (later, only when told): `POST https://sacoparentsalign.com/api/integrations/case-update`
- Header: `x-integration-key: <value of INTEGRATION_SHARED_SECRET>` — same key you already use for the readiness push. The value is exchanged out-of-band, never in chat/tickets/code. Preview and production have different values.
- `Content-Type: application/json`
- There is NO `/api/integrations/import` route (404). Everything goes through `case-update`.

## Body (one request per parent, using THAT parent's own invitation token)
```json
{
  "token": "<the parent's own Align invitation token>",
  "status": "foundation",
  "foundation_statement": {
    "completed_at": "2026-10-27T15:04:05Z",
    "title": "Mother's Foundation Statement",
    "content": "The statement as free text (max 5000 characters; longer is truncated, not rejected).",
    "fields": {
      "child_name": "Sam",
      "shared_purpose": "…",
      "vision": "…",
      "priorities": ["one item per entry"],
      "strengths": "…",
      "needs": ["…"],
      "concerns": ["…"],
      "wellness_tech": ["…"],
      "child_may_need": "…",
      "commitments": ["…"],
      "goals": ["…"],
      "future": "…",
      "parent_commitment": "…"
    }
  }
}
```
- Required: `token`, and at least one of `content` or a non-empty `fields` section.
- `fields` is optional; only the 13 keys above are kept (anything else is dropped). If you only have free text, send `content` alone.
- Text fields: `shared_purpose, vision, strengths, child_may_need, future, parent_commitment, child_name` (≤ 4000 chars each). List fields: `priorities, needs, concerns, wellness_tech, commitments, goals` (arrays of strings, ≤ 40 items, ≤ 500 chars each).
- `title` optional (≤ 120 chars; default "Child-Focused Foundation Statement"). `completed_at` optional (ISO date or datetime).
- Do NOT send `parent`, `role`, `author`, `parent_email`, `case_id` — Align ignores them. The invitation token alone decides which parent and which case the statement belongs to. Mother's token can never write to Father's side and vice versa.
- Re-sending for the same token replaces that parent's earlier statement only.

## Responses
| Code | Meaning |
|---|---|
| 200 `{"ok": true, "case_status": "…"}` | Stored privately for that parent (case status unchanged) |
| 401 | Missing/wrong `x-integration-key` |
| 404 | Unknown token / case |
| 400 | No usable `content`/`fields`, or unknown `status` |
| 413 / 422 | Body too large or not valid JSON |

## What Align does with it
- Holds it privately for that parent (`foundation_imports.<role>`). The professional, the other parent, the court and Align's AI tools do NOT see it.
- Sends the parent a content-free email ("Something you sent has arrived - SA CoParents") to the invitation address.
- The parent includes it themselves from their Align case page ("Include it in this case") or on the agreement form. Only then does it appear in the shared agreement/report.

## Sample code (JavaScript, fetch)
```js
async function pushFoundationStatement({ baseUrl, integrationKey, token, statement }) {
  const res = await fetch(`${baseUrl}/api/integrations/case-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-integration-key": integrationKey },
    body: JSON.stringify({
      token,                          // this parent's own Align invitation token
      status: "foundation",
      foundation_statement: {
        completed_at: statement.completedAt,   // ISO string
        title: statement.title,                // optional
        content: statement.text,               // free text, ≤ 5000 chars
        fields: statement.fields,              // optional structured sections (see list)
      },
    }),
  });
  if (!res.ok) throw new Error(`Align case-update failed: ${res.status} ${await res.text()}`);
  return res.json(); // { ok: true, case_status: "..." }
}
```
`integrationKey` must come from the app's secret store / environment (e.g. `ALIGN_INTEGRATION_KEY`), never hard-coded. Wrap the call behind a feature flag that stays OFF until Align confirms.

## Coordinated test plan (preview → preview)
1. Align provides one test case with a Mother token and a Father token (preview).
2. App sends Mother's statement with Mother's token, Father's with Father's.
3. Align confirms: each landed on the correct side; nothing visible to the professional; each parent sees only their own on their case page; arrival emails received.
4. Then, and only then, discuss switching on production sending.
