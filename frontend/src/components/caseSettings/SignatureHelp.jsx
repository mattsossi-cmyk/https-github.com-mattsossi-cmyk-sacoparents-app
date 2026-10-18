import React from "react";
import { Copy } from "lucide-react";
import { toast } from "sonner";

const WEBHOOK = `${process.env.REACT_APP_BACKEND_URL}/api/internal/safety-status`;

const RULES = [
  ["Address", `POST ${WEBHOOK}`],
  ["Header", "X-Align-Signature"],
  ["Value", "hex HMAC-SHA256 of the exact raw body bytes sent (a sha256= prefix is optional; no base64, nothing else signed)"],
  ["Key", "the shared secret named ALIGN_WEBHOOK_SECRET, same value in both apps"],
  ["Timestamp", "\"timestamp\" in the JSON body: Unix seconds or milliseconds, or an ISO date with a timezone, within 5 minutes"],
];

const COPY_TEXT = `How Align must sign updates to sacoparentsapp\n${RULES.map(([k, v]) => `- ${k}: ${v}`).join("\n")}\n- Enter the secret in each app's Secrets tab; never paste it into chat.`;

// Admin-only setup help for Align's builder. Shows names and formats, never the secret's value.
export function SignatureHelp({ badSignature, oldTimestamp }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(COPY_TEXT);
      toast.success("Copied. Paste it to Align's builder.");
    } catch {
      toast.error("Couldn't copy. Select the text and copy it instead.");
    }
  };
  return (
    <div className="mt-3 space-y-2">
      {oldTimestamp > 0 && (
        <p data-testid="align-timestamp-hint" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-[#7A4A00]">
          &ldquo;Too old&rdquo; refusals: send timestamp in the body as Unix seconds or milliseconds, or an ISO date with a timezone, within 5 minutes; check Align&apos;s server clock.
        </p>
      )}
      <details open={badSignature > 0} data-testid="align-signature-help" className="rounded-xl border border-[#E5E0EE] bg-[#FBFAFE] px-3 py-2">
        <summary className="cursor-pointer text-sm font-semibold text-[#3D1A78] min-h-6">How Align must sign updates</summary>
        {badSignature > 0 && (
          <p className="mt-2 text-xs text-[#8A5500]" data-testid="align-status-secret-hint">
            Wrong-signature refusals usually mean Align and this app are using different webhook secrets, or Align is signing something other than the raw body.
          </p>
        )}
        <dl className="mt-2 space-y-1.5 text-xs text-[#3B3552]">
          {RULES.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
              <dt className="font-semibold text-[#4B4567]">{k}</dt>
              <dd className="break-words font-mono text-[0.6875rem]">{v}</dd>
            </div>
          ))}
        </dl>
        <button type="button" onClick={copy} data-testid="align-signature-copy" className="mt-3 inline-flex min-h-6 items-center gap-1.5 rounded-full border border-[#D9D3EA] bg-white px-3 py-1.5 text-xs font-bold text-[#3D1A78] transition-colors hover:bg-[#F8F7FC]">
          <Copy size={13} aria-hidden="true" /> Copy for Align&apos;s builder
        </button>
      </details>
    </div>
  );
}
