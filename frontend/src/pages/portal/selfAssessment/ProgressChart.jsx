import React, { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CONTENT, SECTIONS, SERIES_COLORS, chartLabel } from "./content";

const SERIES = [
  { key: "overall", label: CONTENT.chart.overall_label },
  ...SECTIONS.map((s) => ({ key: s.key, label: s.score_label })),
];

function Legend({ series }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] font-semibold text-slate-600">
      {series.map((s) => (
        <span key={s.key} className="inline-flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: SERIES_COLORS[s.key] }} />
          {s.label}
        </span>
      ))}
    </div>
  );
}

export function ProgressChart({ history }) {
  const [showAreas, setShowAreas] = useState(false);
  const data = history.map((h, i) => ({
    label: chartLabel(history, i),
    overall: h.scores.overall,
    ...h.scores.sections,
  }));
  const series = showAreas ? SERIES : SERIES.slice(0, 1);
  return (
    <div data-testid="sa-progress-chart" className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h5 className="text-[0.75rem] font-bold text-slate-800">{CONTENT.chart.title}</h5>
        <button
          type="button"
          role="switch"
          aria-checked={showAreas}
          data-testid="sa-chart-toggle-areas"
          onClick={() => setShowAreas((v) => !v)}
          className="inline-flex items-center gap-1.5 text-[0.6875rem] font-semibold text-purple-900"
        >
          <span className={`w-8 h-[18px] rounded-full p-0.5 transition-colors ${showAreas ? "bg-purple-700" : "bg-slate-300"}`}>
            <span className={`block w-3.5 h-3.5 rounded-full bg-white shadow transition-transform ${showAreas ? "translate-x-3.5" : ""}`} />
          </span>
          {CONTENT.chart.toggle_label}
        </button>
      </div>
      <div className="h-48 -ml-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#ede9fe" strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} width={34} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 12, borderColor: "#ddd6fe" }} />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={SERIES_COLORS[s.key]}
                strokeWidth={s.key === "overall" ? 3 : 2}
                dot={{ r: s.key === "overall" ? 4 : 3 }}
                isAnimationActive
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend series={series} />
    </div>
  );
}
