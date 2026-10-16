# Email authentication for `sacoparentsalign.com` (Resend)

The app sends from `RESEND_FROM_EMAIL` on `sacoparentsalign.com` via Resend. I cannot change DNS from the app; these records are
pasted at your DNS provider. Values marked **(from Resend dashboard)** are generated per account — copy them from
Resend → Domains → `sacoparentsalign.com`. Everything else below is exact.

## 1. Add the domain in Resend
Resend → Domains → Add Domain → `sacoparentsalign.com` → Region: **US East (N. Virginia)** (keep whatever region Resend shows; the MX/SPF host names below assume `us-east-1`).
Resend will list three records. They correspond to the rows below.

## 2. DNS records

| Purpose | Type | Host / Name | Value | TTL |
|---|---|---|---|---|
| SPF (bounce domain) | TXT | `send` | `v=spf1 include:amazonses.com ~all` | 3600 |
| Return-path | MX | `send` | `feedback-smtp.us-east-1.amazonses.com` priority **10** | 3600 |
| DKIM | TXT | `resend._domainkey` | `p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQ…` **(from Resend dashboard — one long string starting with `p=`)** | 3600 |
| DMARC | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@sacoparentsalign.com; fo=1; adkim=s; aspf=r` | 3600 |

Notes
- `send` is the subdomain Resend uses for the envelope/return-path (`send.sacoparentsalign.com`). Your `From` stays `@sacoparentsalign.com`.
- If your root domain already has an SPF TXT record (e.g. for Google Workspace), leave it as is — Resend's SPF lives on `send`, not the root. Never create two SPF records on the same host.
- If Resend shows a different region (e.g. `eu-west-1`), use that region in the MX value: `feedback-smtp.<region>.amazonses.com`.
- Some DNS providers want the host as `send.sacoparentsalign.com` / `_dmarc.sacoparentsalign.com` (fully qualified). Use whichever form your provider expects; do not enter both.

## 3. DMARC roll-out (recommended sequence)
1. Start with `p=none` (above) for 2–4 weeks and read the aggregate reports sent to `dmarc@sacoparentsalign.com` (create that mailbox or an alias).
2. When reports show only legitimate senders, move to `p=quarantine; pct=25` → `pct=100`.
3. Finish at `p=reject` once you are confident.

## 4. Verify
- Resend → Domains → click **Verify** (SPF/MX/DKIM each turn green; propagation can take up to 48 h, usually minutes).
- Send a test from Align: Admin → Email test (`POST /api/admin/email-test`). Open the message in Gmail → "Show original" → confirm `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`.
- Optional: `dig TXT send.sacoparentsalign.com`, `dig TXT resend._domainkey.sacoparentsalign.com`, `dig TXT _dmarc.sacoparentsalign.com`.

## 5. Reply-to
Invitation and reminder emails set `Reply-To` to the assigned professional's address, so parent replies go to the professional, not to the sending domain. No DNS change is needed for that.
