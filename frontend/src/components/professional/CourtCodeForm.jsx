import React, { useState } from "react";
import { Check, Copy, KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

export const ASSESSMENTS = [
  ["coparent", "Co-Parenting Assessment"],
  ["self", "Self-Assessment"],
  ["educational", "Educational Assessment"],
  ["medical", "Medical Assessment"],
  ["psychological", "Psychological Assessment"],
  ["foundation", "Foundation Statement"],
  ["parallel", "Parallel Parenting Plan"],
];
const DAYS = [30, 60, 90, 180];

export const parentNote = (code) =>
  `Please sign in to SA CoParents (sacoparentsapp.online), choose Court Ordered, tap "Accept Your Court-Ordered Invite" and enter ${code} as the Court Reference Number. The assessments I asked for will already be ticked for you. Your answers stay private; I only see whether each one is done.`;

const copy = (text, label) =>
  navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied`), () => toast.error("Copy failed. Select the text to copy it."));

export const CourtCodeForm = ({ onCreated }) => {
  const [picked, setPicked] = useState([]);
  const [label, setLabel] = useState("");
  const [days, setDays] = useState(90);
  const [busy, setBusy] = useState(false);
  const [made, setMade] = useState(null);
  const toggle = (k) => setPicked((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k]));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/professional/court-codes", { label, requested: picked, valid_days: days });
      setMade(data.code);
      setPicked([]);
      setLabel("");
      onCreated();
    } catch (err) {
      toast.error(String(err?.response?.data?.detail?.[0]?.msg || err?.response?.data?.detail || "Could not create the code."));
    } finally {
      setBusy(false);
    }
  };

  if (made) return <CodeCreated code={made} onDone={() => setMade(null)} />;
  return (
    <form onSubmit={submit} className="rounded-xl border border-[#D6CFE8] bg-[#FBF9FE] p-4 space-y-3" data-testid="court-code-form">
      <fieldset>
        <legend className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-2">Assessments you&rsquo;re asking for</legend>
        <div className="grid sm:grid-cols-2 gap-1.5">
          {ASSESSMENTS.map(([k, t]) => (
            <label key={k} className="flex items-center gap-2 text-sm text-[#1A1330] cursor-pointer">
              <input type="checkbox" checked={picked.includes(k)} onChange={() => toggle(k)} className="accent-[#3D1A78]" data-testid={`court-code-pick-${k}`} />
              {t}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid sm:grid-cols-[1fr_auto] gap-3">
        <input value={label} onChange={(e) => setLabel(e.target.value)} maxLength={80} placeholder="Your private reference (optional, never shown to the parent)"
          className="rounded-lg border border-[#E5E0EE] bg-white text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]" data-testid="court-code-label" />
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded-lg border border-[#E5E0EE] bg-white text-sm px-3 py-2" data-testid="court-code-days">
          {DAYS.map((d) => <option key={d} value={d}>{`Valid ${d} days`}</option>)}
        </select>
      </div>
      <button type="submit" disabled={busy || !picked.length} data-testid="court-code-create"
        className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold transition-colors disabled:bg-[#C9C0DC] disabled:cursor-not-allowed">
        {busy ? <Loader2 size={13} className="animate-spin" /> : <KeyRound size={13} />} Create court code
      </button>
    </form>
  );
};

const CodeCreated = ({ code, onDone }) => (
  <div className="rounded-xl border border-[#B5DFC5] bg-[#F2FAF5] p-4 space-y-3" data-testid="court-code-created">
    <div className="flex items-center justify-between gap-3 flex-wrap">
      <span className="font-mono text-xl font-bold tracking-wider text-[#1F5C3B]" data-testid="court-code-value">{code}</span>
      <button type="button" onClick={() => copy(code, "Code")} className="inline-flex items-center gap-1 text-xs font-semibold text-[#1F5C3B] hover:underline" data-testid="court-code-copy">
        <Copy size={12} /> Copy code
      </button>
    </div>
    <p className="text-[12px] text-[#8A5B00] font-semibold">Copy it now. For privacy we only keep a scrambled version, so it can&rsquo;t be shown again.</p>
    <div className="rounded-lg bg-white border border-[#E5E0EE] p-3 text-[13px] text-[#4B4567] leading-relaxed" data-testid="court-code-parent-note">
      <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-1">What to tell the parent</div>
      {parentNote(code)}
    </div>
    <div className="flex gap-3 flex-wrap">
      <button type="button" onClick={() => copy(parentNote(code), "Parent note")} className="inline-flex items-center gap-1 rounded-full border border-[#D6CFE8] bg-white px-3 py-1.5 text-xs font-semibold text-[#3D1A78]" data-testid="court-code-copy-note">
        <Copy size={12} /> Copy note
      </button>
      <button type="button" onClick={onDone} className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] text-white px-3 py-1.5 text-xs font-semibold" data-testid="court-code-done">
        <Check size={12} /> Done
      </button>
    </div>
  </div>
);
