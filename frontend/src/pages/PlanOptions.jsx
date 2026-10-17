import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Check } from "lucide-react";
import { toast } from "sonner";

import { api } from "../lib/api";

function OptionTile({ o, picked, onToggle }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={picked}
      onClick={() => onToggle(o.id)}
      data-testid={`plan-option-${o.id}`}
      className={`text-left w-full rounded-xl border-2 p-4 flex items-start gap-3 transition-[border-color,background-color] ${
        picked ? "border-[#4a2574] bg-[#f4f0fa]" : "border-slate-200 bg-white hover:border-purple-300"
      }`}
    >
      <span className={`mt-0.5 shrink-0 w-5 h-5 rounded-md border-2 grid place-items-center ${picked ? "border-[#4a2574] bg-[#4a2574] text-white" : "border-slate-300"}`}>
        {picked && <Check size={12} strokeWidth={3} />}
      </span>
      <span>
        <span className="block text-sm font-semibold text-slate-900">{o.title}</span>
        <span className="block text-xs text-slate-500 mt-1 leading-relaxed">{o.description}</span>
      </span>
    </button>
  );
}

export default function PlanOptionsPage() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState(null);
  const [picks, setPicks] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get("/plan-options").then((r) => setCategories(r.data.categories)).catch(() => setCategories([]));
    api.get("/plan-options/picks").then((r) => setPicks(r.data.picks)).catch(() => {});
  }, []);
  const toggle = (id) => setPicks((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const save = async () => {
    setBusy(true);
    try {
      const r = await api.put("/plan-options/picks", { picks });
      setPicks(r.data.picks);
      toast.success("Your picks are saved.");
    } catch {
      toast.error("Couldn't save. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <main data-testid="plan-options-page" className="min-h-screen gentle-bg py-8 sm:py-12 pb-28">
      <div className="max-w-2xl mx-auto px-4">
        <button type="button" onClick={() => navigate(-1)} data-testid="plan-options-back" className="inline-flex min-h-6 items-center gap-1.5 text-sm font-semibold text-[#3D1A78] mb-6">
          <ArrowLeft size={15} /> Back
        </button>
        <h1 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">Parenting plan options</h1>
        <p className="text-sm text-[#4B4567] mt-2 max-w-lg">Tick the options you&apos;d like in your parenting plan. Your picks are saved to your account and aren&apos;t shared.</p>
        {!categories ? (
          <p className="text-sm text-[#6E6787] mt-8" data-testid="plan-options-loading">Loading…</p>
        ) : (
          categories.map((c) => (
            <section key={c.key} className="mt-8" data-testid={`plan-options-cat-${c.key}`}>
              <h2 className="text-base md:text-lg font-bold text-[#1A1330] mb-3">{c.label}</h2>
              <div className="grid gap-3">
                {c.options.map((o) => (
                  <OptionTile key={o.id} o={o} picked={picks.includes(o.id)} onToggle={toggle} />
                ))}
              </div>
            </section>
          ))
        )}
      </div>
      <div className="fixed bottom-0 inset-x-0 bg-white/95 border-t border-purple-100 px-4 py-3 backdrop-blur">
        <div className="max-w-2xl mx-auto flex items-center justify-between gap-3">
          <span className="text-xs text-[#6E6787]" data-testid="plan-options-count">{picks.length} picked</span>
          <button type="button" onClick={save} disabled={busy || !categories} data-testid="plan-options-save" className="btn-gradient px-6 disabled:opacity-50">
            {busy ? "Saving…" : "Save my picks"}
          </button>
        </div>
      </div>
    </main>
  );
}
