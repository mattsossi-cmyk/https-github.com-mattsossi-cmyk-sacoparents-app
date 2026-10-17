/**
 * ForPortalEngineers — public documentation page for the
 * sacoparentsalign.com portal engineering team.
 *
 * Mirrors the CLI at /app/scripts/portal_handshake_simulator.py
 * so sibling engineers can validate their portal implementation
 * against the same contract without cloning our repo.
 */
import { Link } from "react-router-dom";
import {
  ArrowLeft, ShieldCheck, Terminal, FileCode, Send, KeyRound, Copy,
} from "lucide-react";
import { toast } from "sonner";

function Code({ children, testid }) {
  const raw = typeof children === "string" ? children : "";
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(raw);
      toast.success("Copied to clipboard.");
    } catch {
      toast.error("Couldn't copy.");
    }
  };
  return (
    <div className="relative group max-w-full overflow-hidden">
      <pre
        tabIndex={0}
        aria-label="Code example"
        className="rounded-2xl bg-[#1A1330] text-[#F1EEF7] text-[12.5px] leading-relaxed p-4 overflow-x-auto font-mono max-w-full whitespace-pre"
        data-testid={testid}
      >
        <code className="block">{children}</code>
      </pre>
      {raw && (
        <button
          type="button"
          onClick={handleCopy}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity inline-flex items-center gap-1 rounded-full bg-[#3D1A78] text-white text-[10px] font-semibold px-2 py-1"
          data-testid={testid ? `${testid}-copy` : undefined}
          aria-label="Copy code"
        >
          <Copy size={10} /> Copy
        </button>
      )}
    </div>
  );
}

function Section({ id, icon: Icon, title, children }) {
  return (
    <section id={id} className="mt-10" data-testid={`section-${id}`}>
      <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] flex items-center gap-2 mb-4">
        {Icon && <Icon size={22} className="text-[#3D1A78]" />} {title}
      </h2>
      <div className="text-[14px] leading-relaxed text-[#4B4567] space-y-3">
        {children}
      </div>
    </section>
  );
}

export default function ForPortalEngineers() {
  return (
    <div className="min-h-screen bg-[#FAF8FD]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-16" data-testid="for-portal-engineers-page">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="portal-eng-back-link"
        >
          <ArrowLeft size={14} /> Back to sacoparentsapp.online
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <Terminal size={12} /> For sacoparentsalign.com engineers
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
          data-testid="portal-eng-title"
        >
          Report-Share portal handshake
        </h1>
        <p className="text-[#4B4567] mt-4 leading-relaxed">
          This page documents the contract your professional portal
          must implement to render reports parents share with your
          site. Two endpoints on our side; two callbacks from you.
          There&rsquo;s a CLI simulator at{" "}
          <code className="bg-white border border-[#E5E0EE] rounded px-1 py-0.5 font-mono text-[12px]">
            scripts/portal_handshake_simulator.py
          </code>{" "}
          if you want to test byte-for-byte.
        </p>

        <div className="mt-6 rounded-2xl border border-[#F5D0C5] bg-[#FEF5F0] p-4">
          <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#9A3A23] mb-1 flex items-center gap-1.5">
            <ShieldCheck size={11} /> Contract rule zero
          </div>
          <p className="text-[13px] text-[#4B4567] leading-relaxed">
            <strong>Never render a report body without a fresh
            permission check.</strong> Every view AND every download
            MUST first call <code>GET /report-permissions/&#123;id&#125;</code>{" "}
            in the same request cycle. Cached auth is a liability —
            parents can revoke at any moment and we return the
            revocation immediately.
          </p>
        </div>

        {/* ------- 1. Auth ------- */}
        <Section id="auth" icon={KeyRound} title="1 · Authentication">
          <p>
            All calls between our two apps carry an{" "}
            <code>X-Integration-Key</code> header. The key is a
            shared secret provisioned via secure channel — never
            checked into source, never logged. On our side we
            compare it with <code>hmac.compare_digest</code> so
            timing attacks are moot.
          </p>
          <Code testid="code-header">
{`X-Integration-Key: <shared-secret-32-chars-plus>
Content-Type: application/json
Accept: application/json`}
          </Code>
          <p className="text-[13px] text-[#857E9C]">
            Missing or wrong key → <code>401 Invalid integration key</code>.
            Missing secret on our environment → <code>503 Integration not configured</code>{" "}
            (this should never happen in production; if you see it,
            open a support ticket).
          </p>
        </Section>

        {/* ------- 2. Permission check ------- */}
        <Section id="permission-check" icon={FileCode} title="2 · Permission check (GET)">
          <p>
            Call this on every view / download attempt to confirm the
            parent hasn&rsquo;t revoked access:
          </p>
          <Code testid="code-permission-check-req">
{`GET https://sacoparentsapp.online/api/integrations/report-permissions/{permission_id}
X-Integration-Key: $INTEGRATION_SHARED_SECRET`}
          </Code>
          <p>
            <strong>Response shape</strong> — always JSON, always
            <code>200</code> even on inactive permissions:
          </p>
          <Code testid="code-permission-check-resp">
{`// Active
{
  "active": true,
  "permission_id": "6f5a41d2b8e9…",
  "invitation_id": "ab12cd34ef56",
  "report_id": "foundation:user_abc",
  "lane": "foundation",
  "title": "Foundation Statement",
  "version": 1,
  "download_permission": true,
  "expires_at": "2026-10-08T12:00:00Z"
}

// Inactive — always includes a machine-parseable reason
{ "active": false, "reason": "revoked",  "permission_id": "…" }
{ "active": false, "reason": "expired",  "permission_id": "…" }
{ "active": false, "reason": "unknown" }`}
          </Code>
          <p className="text-[13px] text-[#857E9C]">
            When <code>active</code> is <code>false</code>, your portal
            must show the professional a "This access has ended" screen
            and stop. Never fall back to a cached previous response.
          </p>
        </Section>

        {/* ------- 3. Event recording ------- */}
        <Section id="events" icon={Send} title="3 · Event recording (POST)">
          <p>
            After a successful permission check, record what the
            professional actually did. We use these events to power
            the parent&rsquo;s notification digest and their per-invite
            audit trail.
          </p>
          <Code testid="code-event-req">
{`POST https://sacoparentsapp.online/api/integrations/report-permissions/{permission_id}/events
X-Integration-Key: $INTEGRATION_SHARED_SECRET
Content-Type: application/json

{
  "event": "view" | "download" | "accepted" | "declined",
  "occurred_at": "2026-09-08T14:22:03Z",   // optional; we default to server time
  "user_agent": "Mozilla/5.0 …"            // optional
}`}
          </Code>
          <p><strong>Which event when</strong>:</p>
          <ul className="list-disc list-inside space-y-1 text-[13.5px]">
            <li>
              <code>accepted</code> — professional has completed
              identity verification on your side and clicked Accept
              on the invite landing page. Fires <em>once</em> per
              invitation.
            </li>
            <li>
              <code>declined</code> — professional clicked Decline
              on the invite landing page.
            </li>
            <li>
              <code>view</code> — professional opened the report
              body for reading. One event per open (not per scroll).
            </li>
            <li>
              <code>download</code> — professional saved a copy.
              Only send when <code>download_permission=true</code>{" "}
              from the permission-check response.
            </li>
          </ul>
          <p className="text-[13px] text-[#857E9C]">
            Response is <code>{`{ "event_id": "…", "recorded": true }`}</code>.
            Non-200 → retry once with backoff, then log locally.
            Missing X-Integration-Key → <code>401</code>. Unknown
            permission_id → <code>404</code>.
          </p>
        </Section>

        {/* ------- 4. Accept webhook — the other direction ------- */}
        <Section id="accept-webhook" icon={ShieldCheck} title="4 · Directory invite accept (POST) — the other direction">
          <p>
            This is the OTHER direction: SA CoParents Align (you)
            calls US when a professional accepts a directory-style
            invitation (case-bind flow, not the parent-share flow).
            Present for completeness — separate from the report-share
            handshake above.
          </p>
          <Code testid="code-accept-webhook-req">
{`POST https://sacoparentsapp.online/api/professional/directory/invite/accept-webhook
X-Sacoparentsalign-Signature: sha256=<hex HMAC-SHA256 of raw body>
Content-Type: application/json

{
  "token": "<invite_token minted at invite time>",
  "accepted_at": "2026-09-08T14:22:03Z",   // optional
  "professional_id": "sacpa-002",           // your canonical id
  "professional_name": "Dr. Nomsa Dlamini",
  "professional_email": "nomsa@sacoparentsalign.com"
}`}
          </Code>
          <p className="text-[13px] text-[#857E9C]">
            Signature key is <code>SACOPARENTSALIGN_WEBHOOK_SECRET</code> —
            a DIFFERENT shared secret from <code>INTEGRATION_SHARED_SECRET</code>{" "}
            above. Idempotent: second call returns
            <code>200 {`{"applied": false}`}</code>. Unknown token →{" "}
            <code>404</code>.
          </p>
        </Section>

        {/* ------- 5. CLI simulator ------- */}
        <Section id="cli" icon={Terminal} title="5 · CLI simulator to validate your portal">
          <p>
            The fastest way to sanity-check your portal implementation
            is to run the CLI shipped in our repo. Ask us for a
            valid <code>permission_id</code> against staging:
          </p>
          <Code testid="code-cli-run">
{`export SACOPARENTSAPP_BASE_URL="https://sacoparentsapp.online"
export INTEGRATION_SHARED_SECRET="<your-shared-key>"

python scripts/portal_handshake_simulator.py \\
  --permission-id 6f5a41d2b8e94e10a92cc4b1d43b7a2f \\
  --events view download`}
          </Code>
          <p>
            The CLI prints every request + response and a copy-pasteable
            redacted curl replay for each hop. If our tool succeeds
            against a permission_id and your portal fails against the
            SAME permission_id, the delta is your implementation —
            not the contract.
          </p>
        </Section>

        {/* ------- 6. Error contract ------- */}
        <Section id="errors" title="6 · Error contract">
          <p>
            Every error body follows FastAPI&rsquo;s{" "}
            <code>{`{"detail": "…"}`}</code> shape (or an array of
            validation errors on 422). Never rely on HTTP status alone —
            <em>always</em> parse <code>detail</code> for user-facing
            copy when appropriate.
          </p>
          <Code testid="code-errors">
{`400  { "detail": "Both consent boxes must be checked." }
401  { "detail": "Invalid integration key." }
404  { "detail": "Unknown permission_id." }
422  { "detail": [ { "loc": [...], "msg": "…", "type": "…" } ] }
502  { "detail": "Delivery failed." }
503  { "detail": "Integration not configured." }`}
          </Code>
        </Section>

        <div className="mt-12 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-5">
          <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
            Questions?
          </div>
          <p className="text-[13.5px] text-[#4B4567] mt-1 leading-relaxed">
            Reach out on our shared Slack channel or email{" "}
            <a
              href="mailto:integrations@sacoparentsapp.online"
              className="text-[#3D1A78] underline"
              data-testid="portal-eng-contact-email"
            >
              integrations@sacoparentsapp.online
            </a>.
            We&rsquo;ll ship a versioned changelog on this page as
            the contract evolves.
          </p>
        </div>
      </div>
    </div>
  );
}
