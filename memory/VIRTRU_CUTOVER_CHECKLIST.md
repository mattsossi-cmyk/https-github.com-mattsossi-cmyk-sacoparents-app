# Virtru Hosted Gateway — Provisioning & Cutover Checklist

> Pattern A (SMTP relay) is wired into the codebase. This checklist is
> what the operator does with Virtru + the sending domain to actually
> turn it on. Nothing here requires additional code changes.

## 1. What we've already built

- `/app/backend/virtru_mailer.py` — SMTP submitter, per-message
  `X-Virtru-Auth` + optional `X-Virtru-Encrypt: 1` MIME headers,
  attachment safety cap, redacted error logging.
- `/app/backend/email_service.py::_send()` — auto-routes through
  Virtru when `VIRTRU_ENABLED=true`, falls back to Resend cleanly
  when Virtru isn't ready OR when a send fails (unless
  `VIRTRU_FORCE_ENCRYPT_REQUIRED=true`, which fails closed).
- `send_joint_professional_report` + `send_joint_agreement_draft`
  are marked `require_encrypted=True` — every HIPAA-scoped joint
  email honours the fail-closed flag.
- Env vars are pre-declared in `/app/backend/.env` with safe defaults
  (`VIRTRU_ENABLED=false`).
- Tests: `test_iter122_virtru_mailer.py` — 6/6 pass, all mocked.

## 2. Before you flip the flag — obtain from Virtru

1. Signed **Business Associate Agreement (BAA)**.
2. **Tenant provisioning confirmation** for the Hosted Gateway with
   your sending domain (e.g. `sacoparentsapp.online`).
3. **Organisation-specific `X-Virtru-Auth` code** — treat as a live
   secret. Never log, never commit, never return in an HTTP response.
4. **DNS-verified sending address** — most likely `reports@sacoparentsapp.online`
   or similar. Confirm DKIM/SPF records are in place (Virtru will
   supply the exact values).
5. **Outbound Security Rule** on the Virtru tenant that triggers
   TDF encryption whenever `X-Virtru-Encrypt: 1` is present. Without
   this rule, our header is a no-op.
6. Optional: **subject-line marker** (Virtru calls it `#secure#`) if
   you want a redundant trigger. If enabled, set `VIRTRU_SUBJECT_MARKER=#secure#`.

## 3. Env vars to flip in `/app/backend/.env`

| Variable | While pre-provisioning | Once BAA + tenant live |
| --- | --- | --- |
| `VIRTRU_ENABLED` | `false` | `true` |
| `VIRTRU_AUTH_HEADER` | (empty) | *the Virtru-provided code* |
| `VIRTRU_FROM_EMAIL` | (empty) | `reports@sacoparentsapp.online` |
| `VIRTRU_FROM_NAME` | `SA CoParents` | `SA CoParents` |
| `VIRTRU_FORCE_ENCRYPT` | `false` | `true` |
| `VIRTRU_FORCE_ENCRYPT_REQUIRED` | `false` | `true` |
| `VIRTRU_SMTP_HOST` | `smtp.virtrugateway.com` | `smtp.virtrugateway.com` |
| `VIRTRU_SMTP_PORT` | `587` | `587` |
| `VIRTRU_SMTP_STARTTLS` | `true` | `true` |
| `VIRTRU_SMTP_TIMEOUT_SECONDS` | `30` | `30` |
| `VIRTRU_SUBJECT_MARKER` | (empty) | (optional `#secure#`) |

Then `sudo supervisorctl restart backend` (only .env changes need a
restart — code changes hot-reload).

## 4. Cutover verification (staged)

1. Connectivity test **before** touching env vars:

    ```bash
    openssl s_client -starttls smtp -crlf \
      -connect smtp.virtrugateway.com:587 \
      -servername smtp.virtrugateway.com
    ```

    Expect a successful TLS handshake.

2. **Dry-run**: set `VIRTRU_ENABLED=true` but leave
   `VIRTRU_FORCE_ENCRYPT_REQUIRED=false`. Send one joint report to a
   test mediator address. Confirm the mail arrived encrypted.

3. **Fail-closed drill**: set `VIRTRU_FORCE_ENCRYPT_REQUIRED=true`.
   Deliberately break `VIRTRU_AUTH_HEADER` to a garbage value. Attempt
   a joint report send from the UI. Expected: user sees
   *"Couldn't send the joint report right now. Please try again in a moment."*
   and **no** Resend delivery occurs. Restore the header.

4. **Full production**: leave both flags on. Monitor
   `/var/log/supervisor/backend.err.log` for `Virtru submission failed`
   entries.

## 5. Ongoing operational rules

- The `X-Virtru-Auth` value is a secret. It never appears in any log
  line, error response, or MongoDB document. Rotate it through
  Virtru at least annually, or whenever a workforce member with
  access to `.env` leaves.
- Never move Virtru credentials into MongoDB or expose them via any
  HTTP endpoint. They live in `.env` only.
- SMTP acceptance is not proof of final recipient delivery. Track
  bounces via the DSN mailbox on `reply_to` — usually the parent
  who initiated the send. If final-delivery telemetry is needed,
  ask Virtru whether your tenant exposes gateway reporting.
- Aggregate attachment cap is 100 MB raw (below Virtru's 150 MB
  base64-encoded ceiling). Enforced in `virtru_mailer.py`.

## 6. Rollback

Set `VIRTRU_ENABLED=false` in `.env`, restart backend, and Resend
resumes automatically. No code change needed. If you ever roll back
after users have been notified of secure email, keep the tenant
provisioned so you can flip it back on inside minutes.

_Last reviewed: 2026-02-21._
