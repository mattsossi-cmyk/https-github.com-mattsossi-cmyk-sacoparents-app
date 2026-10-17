import React, { useEffect, useMemo, useState } from "react";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { CONTENT, SECTIONS, bandFor } from "./content";
import { CoachBubble } from "./ChatBubbles";
import { CentralMessage, CycleStrip, ProgressHistory, ScoreCards } from "./ProgressPanel";

const pick = (e) => ({
  completed_at: e.completed_at,
  parent_name: e.parent_name || "",
  answers: e.answers,
  reflections: e.reflections || {},
  tips: e.tips || {},
  goal: e.goal || "",
});

function TipHistory({ tips }) {
  const items = [
    ...SECTIONS.map((s) => [s.key, CONTENT.tips.step_label.replace("{number}", s.number).replace("{title}", s.title)]),
    ["overall", CONTENT.tips.overall_label],
  ].filter(([k]) => (tips?.[k] || "").trim());
  if (!items.length) return null;
  return (
    <div data-testid="sa-tip-history" className="rounded-2xl border border-purple-100 bg-purple-50/60 px-4 py-3 space-y-2">
      <div className="text-[0.625rem] uppercase font-bold tracking-wider text-purple-800">
        <i className="fa-solid fa-lightbulb mr-1.5"></i>
        {CONTENT.tips.title}
      </div>
      {items.map(([k, label]) => (
        <div key={k} data-testid={`sa-tip-history-${k}`}>
          <div className="text-[0.6875rem] font-bold text-[#3B1C6B]">{label}</div>
          <p className="text-xs text-slate-700 leading-relaxed">{tips[k]}</p>
        </div>
      ))}
    </div>
  );
}

function useDownloadPdf() {
  const [busy, setBusy] = useState(false);
  const download = async (entry, history) => {
    setBusy(true);
    try {
      const res = await api.post(
        "/self-assessment/pdf",
        { entry: pick(entry), history: history.map(pick) },
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Self_Assessment.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Self-Assessment PDF is ready.");
    } catch {
      toast.error("Couldn't build the PDF right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return { busy, download };
}

const bandRank = (score) => CONTENT.bands.findIndex((b) => score >= b.min);

// Areas (and overall) that moved up a band vs the previous assessment.
export const growthMoves = (history) => {
  if (history.length < 2) return [];
  const [prev, cur] = history.slice(-2);
  return [
    { key: "overall", label: CONTENT.chart.overall_label, from: prev.scores.overall, to: cur.scores.overall },
    ...SECTIONS.map((s) => ({ key: s.key, label: s.score_label, from: prev.scores.sections[s.key], to: cur.scores.sections[s.key] })),
  ]
    .filter((m) => bandRank(m.to) < bandRank(m.from))
    .map((m) => ({ ...m, fromBand: bandFor(m.from).label, toBand: bandFor(m.to).label }));
};

function GrowthMoment({ moves }) {
  useEffect(() => {
    const opts = { particleCount: 90, spread: 80, startVelocity: 45, colors: ["#40a040", "#4c2889", "#e67e22", "#0284c7"] };
    const t = setTimeout(() => {
      confetti({ ...opts, angle: 60, origin: { x: 0, y: 0.75 } });
      confetti({ ...opts, angle: 120, origin: { x: 1, y: 0.75 } });
    }, 400);
    return () => clearTimeout(t);
  }, []);
  return (
    <div data-testid="sa-growth-moment" className="rounded-2xl border-2 border-emerald-300 bg-gradient-to-br from-emerald-50 to-white p-4 animate-in fade-in zoom-in-95 duration-500">
      <div className="flex items-center gap-2">
        <span className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center">
          <i className="fa-solid fa-arrow-trend-up"></i>
        </span>
        <h4 className="text-base font-extrabold text-emerald-900">{CONTENT.growth.title}</h4>
      </div>
      <p className="text-[12.5px] text-slate-700 mt-1.5">{CONTENT.growth.lead}</p>
      <ul className="mt-2 space-y-1">
        {moves.map((m) => (
          <li key={m.key} data-testid={`sa-growth-row-${m.key}`} className="text-[0.8125rem] text-slate-800">
            <span className="font-bold">{m.label}:</span> {m.fromBand} <span className="text-emerald-700 font-bold">→ {m.toBand}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StrengthsGrowth({ scores }) {
  const ranked = [...SECTIONS].sort((a, b) => scores.sections[b.key] - scores.sections[a.key]);
  const half = Math.ceil(ranked.length / 2);
  const block = (testid, title, icon, tone, list) => (
    <div data-testid={testid} className={`rounded-2xl border px-4 py-3 ${tone}`}>
      <div className="text-[0.625rem] uppercase font-bold tracking-wider mb-1.5">
        <i className={`fa-solid ${icon} mr-1.5`}></i>
        {title}
      </div>
      {list.map((s) => (
        <div key={s.key} className="flex justify-between text-[0.8125rem] text-slate-800">
          <span>{s.score_label}</span>
          <span className="font-bold">{scores.sections[s.key]}/100</span>
        </div>
      ))}
    </div>
  );
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {block("sa-strengths", "Your strengths", "fa-star", "border-emerald-200 bg-emerald-50 text-emerald-800", ranked.slice(0, half))}
      {block("sa-growth-areas", "Growth areas", "fa-seedling", "border-amber-200 bg-amber-50 text-amber-800", ranked.slice(half))}
    </div>
  );
}

export function OverviewPanel({ history, celebrate, onStartNew, onClose }) {
  const { busy, download } = useDownloadPdf();
  const latest = history[history.length - 1];
  const moves = useMemo(() => (celebrate ? growthMoves(history) : []), [celebrate, history]);
  if (!latest) return null;
  return (
    <div data-testid="sa-overview" className="space-y-4">
      {celebrate && <CoachBubble testid="sa-completion-message">{CONTENT.completion_message}</CoachBubble>}
      {moves.length > 0 && <GrowthMoment moves={moves} />}
      <ScoreCards scores={latest.scores} />
      <StrengthsGrowth scores={latest.scores} />
      <ProgressHistory history={history} />
      <TipHistory tips={latest.tips} />
      <CentralMessage />
      {latest.goal && (
        <div data-testid="sa-current-goal" className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <div className="text-[0.625rem] uppercase font-bold tracking-wider text-emerald-800">{CONTENT.goal.label}</div>
          <p className="text-sm font-semibold text-slate-900 mt-0.5 break-words">{latest.goal}</p>
        </div>
      )}
      <CycleStrip />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
        <button
          type="button"
          data-testid="sa-download-pdf"
          disabled={busy}
          onClick={() => download(latest, history)}
          className="py-2.5 rounded-full bg-[#4c2889] hover:bg-[#371a68] disabled:opacity-60 text-white text-xs font-bold transition-colors"
        >
          <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-file-pdf"} mr-1.5`}></i>
          {busy ? "Building PDF…" : "Download PDF"}
        </button>
        <button
          type="button"
          data-testid="sa-start-new"
          onClick={onStartNew}
          className="py-2.5 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-xs font-bold transition-colors"
        >
          <i className="fa-solid fa-rotate mr-1.5"></i>
          Start my next Self-Assessment
        </button>
      </div>
      <button
        type="button"
        data-testid="sa-close"
        onClick={onClose}
        className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
      >
        Close
      </button>
    </div>
  );
}
