import { useState } from "react";

const METHODS = ["email", "phone call", "text", "through my professional only", "in person only", "Prefer not to say"];
const F = "w-full rounded-md border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-purple";

export const SafeContactStep = ({ value, onChange }) => {
  const [open, setOpen] = useState(false);
  const v = value || {};
  const set = (k, val) => onChange({ ...v, [k]: val });
  return (
    <section className="space-y-3 rounded-lg border border-border bg-white p-4" data-testid="screening-safe-contact">
      <h2 className="text-base md:text-lg font-semibold text-brand-purple">Optional · Safe way to reach you</h2>
      <p className="text-sm text-muted-foreground">If a professional needs to reach you about your safety, what is the safest way? Only the professionals assigned to your case can see this. You can skip it.</p>
      {!open ? (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setOpen(true)} className="rounded-full border border-brand-purple px-4 py-1.5 text-sm font-semibold text-brand-purple hover:bg-brand-purple/5" data-testid="safe-contact-add-btn">Add a safe contact method</button>
          <button type="button" onClick={() => onChange(null)} className="rounded-full px-4 py-1.5 text-sm text-muted-foreground hover:underline" data-testid="safe-contact-skip-btn">Skip</button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm sm:col-span-2">Preferred method
            <select className={F} value={v.method || ""} onChange={(e) => set("method", e.target.value)} data-testid="safe-contact-method">
              <option value="">Choose…</option>{METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
          <label className="text-sm">Address or number<input className={F} value={v.address || ""} onChange={(e) => set("address", e.target.value)} data-testid="safe-contact-address" /></label>
          <label className="text-sm">Safe times<input className={F} value={v.safe_times || ""} onChange={(e) => set("safe_times", e.target.value)} placeholder="e.g. weekdays 9–3" data-testid="safe-contact-times" /></label>
          <label className="text-sm">Safe to leave a voicemail or message?
            <select className={F} value={v.voicemail_ok || ""} onChange={(e) => set("voicemail_ok", e.target.value)} data-testid="safe-contact-voicemail">
              <option value="">Choose…</option><option>Yes</option><option>No</option><option>Prefer not to say</option>
            </select>
          </label>
          <label className="text-sm">Code word (optional)<input className={F} value={v.code_word || ""} onChange={(e) => set("code_word", e.target.value)} data-testid="safe-contact-codeword" /></label>
          <button type="button" onClick={() => { onChange(null); setOpen(false); }} className="text-left text-xs text-muted-foreground hover:underline sm:col-span-2" data-testid="safe-contact-clear-btn">Clear and skip</button>
        </div>
      )}
    </section>
  );
};
