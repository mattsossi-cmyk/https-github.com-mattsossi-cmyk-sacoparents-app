# Align ↔ sacoparentsapp link test (for the SACOparentsAlign builder)

Purpose: let a sacoparentsapp admin confirm, right after setup, that Align can reach sacoparentsapp's safety webhook
with the shared secret. No case data is sent, and nothing about any case changes.

## 1. Align adds one endpoint (its "test address")
`POST https://<align-domain>/api/internal/parents-test-ping` (any path is fine; give the full https URL to the
sacoparentsapp admin, who saves it as `ALIGN_PING_URL` in sacoparentsapp's Secrets).

Request from sacoparentsapp:
- Header `X-SACO-Signature: <hex HMAC-SHA256 of the raw request body, key = the shared ALIGN_WEBHOOK_SECRET>`
- JSON body: `{"test_id": "align-<32 hex>", "timestamp": <unix seconds>, "callback_url": "https://<parents-domain>/api/internal/safety-status"}`

Align must:
1. Verify the signature (constant-time compare) and that `timestamp` is within 5 minutes. Otherwise reply 401.
2. Reply `202` straight away (within 10 seconds).
3. Then send the test message (below) to its usual sacoparentsapp webhook address. Use Align's configured webhook URL;
   `callback_url` is only for a cross-check. Don't send to an address you haven't configured.

## 2. The test message Align sends back
`POST <sacoparentsapp webhook>/api/internal/safety-status`, signed exactly like a real update:
- Header `X-Align-Signature: <hex HMAC-SHA256 of the raw body, same shared secret>`
- JSON body: `{"test": true, "test_id": "<the test_id it received>", "timestamp": <unix seconds now>}`

sacoparentsapp replies 200 and shows "Align's test message arrived after N s. The link works both ways." on its
admin page. A test message never changes a case and isn't counted as an update. It's refused (401) if the signature is wrong or the
timestamp is older than 5 minutes, and refused (409) if the exact same body is sent twice.

## 3. Signature and timestamp rules (same for real updates and tests)
- Header name: `X-Align-Signature`. Value: hex HMAC-SHA256 of the exact raw body bytes sent; an optional `sha256=` prefix is fine.
- Don't sign anything else (no "timestamp.body", no re-serialised JSON) and don't use base64.
- `timestamp` goes in the JSON body: Unix seconds or milliseconds (number or digits in quotes), or an ISO date with a
  timezone (e.g. `2026-10-18T10:00:00Z`). Must be within 5 minutes of now.

## 4. Secrets
Both apps use the same `ALIGN_WEBHOOK_SECRET` value. Enter it in each app's Secrets tab; never paste it into chat.
Note: sacoparentsapp also has an older, separate key named `SACOPARENTSALIGN_WEBHOOK_SECRET` used by an earlier
integration; the Safety Gate and this test use `ALIGN_WEBHOOK_SECRET` only.
