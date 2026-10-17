import React from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SECTIONS, SERIES_COLORS, chartLabel } from "./content";
import { GoalTimeline } from "./GoalTimeline";

const fmt = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

function AreaChart({ section, history }) {
  const data = history.map((h, i) => ({ label: chartLabel(history, i), score: h.scores.sections[section.key] }));
  const first = data[0].score;
  const latest = data[data.length - 1].score;
  const d = latest - first;
  const color = SERIES_COLORS[section.key];
  return (
    <div data-testid={`sa-pot-area-${section.key}`} className="rounded-2xl border border-purple-100 bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <h5 className="text-[0.75rem] font-bold text-slate-800 leading-tight">{section.score_label}</h5>
        <span data-testid={`sa-pot-area-${section.key}-latest`} className="text-lg font-extrabold leading-none" style={{ color }}>
          {latest}
        </span>
      </div>
      <p data-testid={`sa-pot-area-${section.key}-change`} className={`text-[10.5px] font-semibold ${d > 0 ? "text-emerald-700" : d < 0 ? "text-rose-700" : "text-slate-500"}`}>
        {history.length < 2 ? "Starting point" : d === 0 ? "No change since your first" : `${d > 0 ? "+" : ""}${d} since your first`}
      </p>
      <div className="h-28 -ml-4 mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#ede9fe" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false} axisLine={false} width={30} />
            <Tooltip contentStyle={{ fontSize: 11, borderRadius: 10, borderColor: "#ddd6fe" }} />
            <Line type="monotone" dataKey="score" name={section.score_label} stroke={color} strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// "Progress over time" tab: one line chart per area across every attempt, then the goal timeline.
export function ProgressOverTime({ history, onReached }) {
  return (
    <div data-testid="sa-progress-over-time" className="space-y-5">
      <div>
        <h4 className="text-base font-extrabold text-slate-900">My progress over time</h4>
        <p data-testid="sa-pot-summary" className="text-[0.75rem] text-slate-600">
          {history.length} Self-Assessment{history.length === 1 ? "" : "s"} since {fmt(history[0].completed_at)}
          {history.length < 2 && ". Your next one will start drawing your lines."}
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SECTIONS.map((s) => (
          <AreaChart key={s.key} section={s} history={history} />
        ))}
      </div>
      <GoalTimeline history={history} onReached={onReached} />
    </div>
  );
}
