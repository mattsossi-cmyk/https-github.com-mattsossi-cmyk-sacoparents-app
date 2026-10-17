# Safety-Status Webhook Contract — sacoparentsalign → sacoparentsapp.online

**Status: PAUSED (2026-10-17).** Flag `SAFETY_STATUS_WEBHOOK=false`, `ALIGN_WEBHOOK_SECRET` unset. Nothing is sent until the Align owner decides otherwise and both sides hold the same secret. This document is for the agent/builder working in the sacoparentsapp.online project.

This is a **separate** contract from the requester-context / import bridge described in `SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md` and `PARENT_APP_REQUESTER_CONTEXT_CONTRACT.md`. Different direction, different secret, different flag.

## Purpose
When an **assigned professional** in Align confirms a safety pathway for a case, Align tells the parent app which *mode* the case is in so the parent app can adjust its own behaviour (e.g. structured messaging). The message carries **no screening content of any kind**.

## Endpoint (parent app implements)
```
POST https://sacoparentsapp.online/api/internal/safety-status
```

## Headers (Align sends)
| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-Align-Signature` | `sha256=<hex HMAC-SHA256(secret, raw request body bytes)>` |
| `X-Align-Timestamp` | ISO-8601 UTC, same value as `timestamp` in the body |
| `X-Align-Version` | `1` |

Secret: `ALIGN_WEBHOOK_SECRET` — one shared value held in both apps' environment config. Never in code, logs, chat or git.

## Body (exactly these 8 keys — nothing else, ever)
Serialised as compact JSON with keys sorted (`json.dumps(payload, separators=(",", ":"), sort_keys=True)`). Verify the signature over the **raw bytes received**, not a re-serialised copy.

```json
{"case_id":"<Align case id>","professional_name":"<display name>","referral":false,"safety_mode":"standard","screening_offered":true,"set_by":"professional","timestamp":"2026-10-17T15:04:05.123456+00:00","version":"1"}
```

| Key | Type | Meaning |
|---|---|---|
| `case_id` | string | Align joint-report id. The test ping uses the literal `ALIGN-TEST-PING`. |
| `safety_mode` | `"standard"` \| `"structured"` \| `"protected"` | Pathway the professional confirmed. |
| `set_by` | `"professional"` | Always a human professional; never automation or AI. |
| `professional_name` | string | Display name of the confirming professional. |
| `referral` | boolean | `true` when mode is `structured` or `protected`. |
| `screening_offered` | boolean | Always `true` (the private check-in is offered to every parent). |
| `version` | `"1"` | Contract version. |
| `timestamp` | string | ISO-8601 UTC. |

### Never included
Screening answers, item responses, free text, tier colours or labels (Red/Amber/Green), triggered rules, which parent disclosed anything, the professional's reasons/notes, safe-contact details, locations, identity details.

## Verification (parent app)
1. Read raw body bytes.
2. Compute `hmac.new(secret, raw_body, sha256).hexdigest()`; compare with constant-time equality to the value after `sha256=` in `X-Align-Signature`.
3. Reject if `timestamp` is older than 5 minutes (replay guard).
4. Idempotency: Align may retry; treat `(case_id, timestamp)` as a de-duplication key.
5. Respond `2xx` with any small JSON body on success.

## Delivery semantics (Align side)
- Fire-and-forget after the professional's confirmation; up to **3 attempts** with back-off **1 s / 3 s / 9 s**.
- Any `4xx` other than `429` stops retries (treated as rejected).
- On final failure Align records the delivery as `failed` and emails its admin; **no case content** is in that alert.
- Every attempt is logged in Align (`webhook_deliveries`) with status and HTTP code only.
- While the flag is OFF, confirming a pathway sends **nothing**.

## Test ping
Align admins have a "Send signed test ping" button. It sends the real payload shape with `case_id = "ALIGN-TEST-PING"`, `safety_mode = "standard"`, `professional_name = "Align admin test ping"`, single attempt, and displays your HTTP status plus the first 300 characters of your response. The button is disabled until `ALIGN_WEBHOOK_SECRET` is set on the Align side.

## Open items before go-live
1. Both owners agree the shared secret and install it (Align: `ALIGN_WEBHOOK_SECRET` in backend env; parent app: equivalent).
2. Parent app confirms the endpoint path and response shape above.
3. Align admin runs the test ping and sees `2xx`.
4. Align owner explicitly approves turning `SAFETY_STATUS_WEBHOOK` on.
