/**
 * VerifySignature — public verification page for signed SA CoParents
 * PDFs. Reached by scanning the QR next to any signature line. The URL
 * carries the tuple (signature id + signer name + timestamp + optional
 * note) as query params; the backend re-hashes and returns whether the
 * hash matches under the current secret. Any tampering (edited name,
 * altered timestamp, forged id) breaks the hash so the page shows
 * "Could not verify" instead of "Untampered ✓".
 */
import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, ShieldAlert, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function VerifySignature() {
  const { sig_id: sigId } = useParams();
  const [params] = useSearchParams();
  const n = params.get("n") || "";
  const t = params.get("t") || "";
  const note = params.get("note") || "";
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const res = await api.get(`/verify/${encodeURIComponent(sigId)}`, {
          params: {
            ...(n ? { n } : {}),
            ...(t ? { t } : {}),
            ...(note ? { note } : {}),
          },
        });
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("verify signature", err);
        if (!cancelled) {
          setState({
            loading: false, data: null,
            error: err?.response?.data?.detail || "Could not check this signature.",
          });
        }
      }
    };
    run();
    return () => { cancelled = true; };
  }, [sigId, n, t, note]);

  const untampered = state.data && state.data.untampered;
  const formattedTime = (() => {
    if (!t) return "";
    try {
      const d = new Date(t);
      return isNaN(d.getTime()) ? t : d.toUTCString();
    } catch {
      return t;
    }
  })();

  return (
    <div className="min-h-screen bg-[#FCFBFE] flex flex-col items-center px-4 py-12"
      data-testid="verify-signature-root">
      <div className="w-full max-w-lg">
        <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] underline mb-6">
          ← SA CoParents
        </Link>
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Signature Verification
          </div>
          <h1 className="mt-1 font-serif text-2xl text-[#1A1330]">
            Was this SA CoParents report tampered with?
          </h1>

          {state.loading && (
            <div className="mt-6 text-sm text-[#4B4567] inline-flex items-center gap-2"
              data-testid="verify-signature-loading">
              <Loader2 className="animate-spin" size={14} /> Checking the signature…
            </div>
          )}

          {!state.loading && untampered && (
            <div className="mt-6 rounded-2xl border-2 border-[#B5DFC5] bg-[#F1F9F4] p-4 sm:p-5"
              data-testid="verify-signature-ok">
              <div className="flex items-start gap-3">
                <CheckCircle2 size={22} className="text-[#1F5C3B] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#1F5C3B]">Untampered</div>
                  <p className="text-xs text-[#1F5C3B] mt-1">
                    The signature block on this PDF matches its cryptographic
                    fingerprint. Nothing on the printed signature line has
                    been edited since the report was generated.
                  </p>
                </div>
              </div>
              <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs text-[#1A1330]">
                <dt className="text-[#6A5799] uppercase tracking-widest text-[0.625rem] font-semibold">Signed by</dt>
                <dd className="font-semibold" data-testid="verify-signature-name">{state.data.signed_by}</dd>
                <dt className="text-[#6A5799] uppercase tracking-widest text-[0.625rem] font-semibold">Signed at</dt>
                <dd data-testid="verify-signature-time">{formattedTime}</dd>
                {state.data.signed_note && (
                  <>
                    <dt className="text-[#6A5799] uppercase tracking-widest text-[0.625rem] font-semibold">Note</dt>
                    <dd className="italic">"{state.data.signed_note}"</dd>
                  </>
                )}
                <dt className="text-[#6A5799] uppercase tracking-widest text-[0.625rem] font-semibold">Signature ID</dt>
                <dd className="font-mono text-[0.6875rem] text-[#4B4567]">{state.data.signature_id}</dd>
              </dl>
            </div>
          )}

          {!state.loading && state.data && !untampered && (
            <div className="mt-6 rounded-2xl border-2 border-[#EFB4B4] bg-[#F8D7D7] p-4 sm:p-5"
              data-testid="verify-signature-tampered">
              <div className="flex items-start gap-3">
                <ShieldAlert size={22} className="text-[#B02A2A] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#B02A2A]">Could not verify</div>
                  <p className="text-xs text-[#B02A2A] mt-1">
                    The signature id in the QR code does not match the name,
                    timestamp, or note on the PDF. Either the report has been
                    edited since it was signed, or the QR was reprinted from
                    a different document.
                  </p>
                </div>
              </div>
              <div className="mt-3 text-[0.625rem] text-[#4B4567]">
                Signature ID: <span className="font-mono">{state.data.signature_id}</span>
              </div>
            </div>
          )}

          {!state.loading && state.error && (
            <div className="mt-6 text-sm text-[#B02A2A]" data-testid="verify-signature-error">
              {state.error}
            </div>
          )}

          <p className="mt-6 text-[0.6875rem] text-[#4B4567] italic">
            This verification only proves the signature block matches; it
            does not attest to the truth of any content in the report.
            SA CoParents reports are informational and not legal advice.
          </p>
        </div>
      </div>
    </div>
  );
}
