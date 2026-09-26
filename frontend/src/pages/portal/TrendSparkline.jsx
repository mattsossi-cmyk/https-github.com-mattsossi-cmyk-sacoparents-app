import React, { useMemo } from "react";

/**
 * TrendSparkline — tiny SVG line chart showing the last N reassessment
 * averages plus the current one. Renders a helpful hint if fewer than 2
 * data points exist so the parent knows what to do next.
 */
export function TrendSparkline({ series, currentAvg }) {
  const points = useMemo(() => {
    const base = Array.isArray(series) ? [...series] : [];
    if (Number.isFinite(currentAvg)) base.push(Number(currentAvg));
    return base.filter((v) => Number.isFinite(v));
  }, [series, currentAvg]);

  if (points.length < 2) {
    return (
      <div
        data-testid="trend-sparkline-empty"
        className="text-[10px] text-slate-500 italic mt-2 flex items-center gap-1"
      >
        <i className="fa-solid fa-chart-line text-purple-700"></i>
        Log at least one Reassessment above to unlock your trend line.
      </div>
    );
  }

  const width = 240;
  const height = 40;
  const step = points.length > 1 ? width / (points.length - 1) : width;
  const toY = (v) => height - (Math.max(0, Math.min(10, v)) / 10) * height;
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${toY(v).toFixed(1)}`)
    .join(" ");

  const first = points[0];
  const last = points[points.length - 1];
  const delta = last - first;
  const deltaLabel =
    delta > 0.05
      ? `▲ +${delta.toFixed(1)} vs first point`
      : delta < -0.05
      ? `▼ ${delta.toFixed(1)} vs first point`
      : "◆ Flat";
  const deltaColor =
    delta > 0.05 ? "text-emerald-700" : delta < -0.05 ? "text-rose-700" : "text-slate-500";

  return (
    <div
      className="mt-2 p-2.5 bg-white rounded-lg border border-purple-200"
      data-testid="trend-sparkline"
    >
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] font-bold text-purple-800 uppercase">
          Trend (last {points.length - 1} reassessment{points.length - 1 === 1 ? "" : "s"} + now)
        </span>
        <span
          data-testid="trend-delta"
          className={`text-[10px] font-bold ${deltaColor}`}
        >
          {deltaLabel}
        </span>
      </div>
      <svg
        viewBox={`-2 -2 ${width + 4} ${height + 4}`}
        preserveAspectRatio="none"
        className="w-full h-10"
        aria-label="Trend line of reassessment scores"
      >
        <line
          x1="0"
          y1={toY(5)}
          x2={width}
          y2={toY(5)}
          stroke="#E9DFF6"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <path d={path} fill="none" stroke="#6D28D9" strokeWidth="2" strokeLinejoin="round" />
        {points.map((v, i) => (
          <circle
            key={i}
            cx={(i * step).toFixed(1)}
            cy={toY(v).toFixed(1)}
            r="2.5"
            fill={i === points.length - 1 ? "#4A1A6E" : "#6D28D9"}
          />
        ))}
      </svg>
      <div className="text-[9px] text-slate-400 text-center mt-1">
        {points.map((v) => v.toFixed(1)).join(" → ")}
      </div>
    </div>
  );
}
