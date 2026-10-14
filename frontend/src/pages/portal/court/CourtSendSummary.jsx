import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

// Send the completion summary to a known professional (no email typed), or type one for Align-made codes.
export function CourtSendSummary() {
  const [opts, setOpts] = useState(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    api.get("/court-path/completion-summary/recipients").then((r) => setOpts(r.data)).catch(() => setOpts({ professionals: [], can_type_email: true }));
  }, []);

  const send = async (payload, key) => {
    setBusy(key);
    try {
      const { data } = await api.post("/court-path/completion-summary/send", payload);
      toast.success(`Sent securely to ${data.sent_to}. They'll get a private link and a one-time code to open it.`);
      setEmail("");
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === "string" ? d : "Please enter a valid email address.");
    } finally {
      setBusy("");
    }
  };
  if (!opts) return null;
  const btn = "inline-flex items-center gap-2 rounded-full border border-emerald-700 text-emerald-800 hover:bg-emerald-50 px-4 py-2 text-sm font-bold transition-colors disabled:opacity-60";
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="court-send-summary">
      {opts.professionals.map((p) => (
        <button key={p.ref} type="button" onClick={() => send({ ref: p.ref }, p.ref)} disabled={!!busy} className={btn} data-testid={`court-send-summary-${p.ref}`}>
          <i className={`fa-solid ${busy === p.ref ? "fa-spinner fa-spin" : "fa-paper-plane"}`} aria-hidden /> Send to my professional ({p.name})
        </button>
      ))}
      {opts.can_type_email && (
        <form onSubmit={(e) => { e.preventDefault(); send({ email: email.trim() }, "typed"); }} className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Your professional's email"
            aria-label="Your professional's email" data-testid="court-send-summary-email"
            className="min-w-0 flex-1 sm:w-64 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm focus:outline-none focus:border-emerald-700" />
          <button type="submit" disabled={!!busy || !email.trim()} className={btn} data-testid="court-send-summary-email-submit">
            <i className={`fa-solid ${busy === "typed" ? "fa-spinner fa-spin" : "fa-paper-plane"}`} aria-hidden /> Send securely
          </button>
        </form>
      )}
      <p className="w-full text-xs text-slate-500">Sent as a private link with a one-time code, never as an attachment. You can cancel it from Shared with professionals.</p>
    </div>
  );
}
