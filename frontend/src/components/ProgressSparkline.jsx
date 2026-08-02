import React, { useMemo } from "react";

/**
 * ProgressSparkline — tiny inline SVG sparkline showing the parent's
 * `completed_count` over the last N days. Used inside `ProgressDashboardCard`
 * next to the "N/5" count so parents see momentum at a glance.
 *
 * Props:
 *   history  Array<{date: "YYYY-MM-DD", done: int, total: int, ready: bool}>
 *   width    number, default 96
 *   height   number, default 28
 */
export default function ProgressSparkline({
  history,
  width = 96,
  height = 28,
}) {
  const points = useMemo(() => {
    if (!Array.isArray(history) || history.length === 0) return null;
    const total = Math.max(1, history[history.length - 1].total || 5);
    // Vertical scale: 0..total. Pad top/bottom so a flat line isn't clipped.
    const padY = 3;
    const usableH = height - padY * 2;
    const stepX = history.length > 1 ? width / (history.length - 1) : 0;
    const pts = history.map((row, i) => {
      const y = padY + usableH - (Math.min(row.done, total) / total) * usableH;
      const x = i * stepX;
      return { x, y, done: row.done, total: total, ready: row.ready, date: row.date };
    });
    return pts;
  }, [history, width, height]);

  if (!points || points.length < 2) {
    // Degenerate case (fresh account, no history yet) — just draw a
    // flat baseline so the layout stays stable.
    return (
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        data-testid="progress-sparkline-empty"
        role="img"
        aria-label="Not enough history for a sparkline yet."
      >
        <line
          x1="0" y1={height - 4} x2={width} y2={height - 4}
          stroke="#D6CFE8" strokeWidth="2" strokeLinecap="round"
        />
      </svg>
    );
  }

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");
  const areaD = `${pathD} L${width} ${height} L0 ${height} Z`;
  const lastPoint = points[points.length - 1];
  const firstPoint = points[0];
  const delta = lastPoint.done - firstPoint.done;
  const trendLabel =
    delta > 0
      ? `Up ${delta} milestone${delta === 1 ? "" : "s"} in the last ${points.length} days`
      : delta < 0
        ? `Down ${Math.abs(delta)} milestone${Math.abs(delta) === 1 ? "" : "s"} in the last ${points.length} days`
        : `Steady — no change in the last ${points.length} days`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-testid="progress-sparkline"
      data-trend={delta > 0 ? "up" : delta < 0 ? "down" : "flat"}
      role="img"
      aria-label={trendLabel}
    >
      <title>{trendLabel}</title>
      <defs>
        <linearGradient id="sacop-spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3D1A78" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#3D1A78" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#sacop-spark-fill)" />
      <path
        d={pathD}
        fill="none"
        stroke="#3D1A78"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Endpoint dot — gold if today is a ready-day, purple otherwise. */}
      <circle
        cx={lastPoint.x}
        cy={lastPoint.y}
        r="2.6"
        fill={lastPoint.ready ? "#C69C42" : "#3D1A78"}
        stroke="#fff"
        strokeWidth="1"
      />
    </svg>
  );
}
