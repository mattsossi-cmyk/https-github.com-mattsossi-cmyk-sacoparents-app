/**
 * OpensSparkline — a tiny inline 7-day bar chart for the Share modal
 * history rows. Renders as pure SVG so it inherits the surrounding
 * font and never needs a chart library.
 *
 * `days` is a 7-element array of ints, oldest → today (matches the
 * shape returned by /foundation-statement/shares → daily_opens_7d).
 *
 * The chart auto-hides when every day is 0 (nothing to show).
 */
import React from "react";

const DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];  // Sun..Sat

function _dayLabelsForWindow(daysCount = 7) {
  // Build labels aligned to the 7-day window ending TODAY. Oldest
  // day sits at index 0. Weekday letter reflects the actual date so
  // a Monday-heavy engagement pattern is legible.
  const out = [];
  const today = new Date();
  for (let i = daysCount - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    out.push(DAY_LABELS[d.getDay()]);
  }
  return out;
}

export default function OpensSparkline({
  days = [],
  height = 28,
  testid,
}) {
  const safe = Array.isArray(days) && days.length === 7
    ? days.map((n) => Math.max(0, Number(n) || 0))
    : [0, 0, 0, 0, 0, 0, 0];
  const max = Math.max(...safe, 1);           // avoid div-by-zero
  const total = safe.reduce((a, b) => a + b, 0);

  if (total === 0) return null;               // nothing to show

  // Fixed-width layout: 7 bars, 6px each, 3px gap → 60px total.
  // Bar height scales linearly against the peak so a 1-open row
  // still shows a visible bar.
  const barW = 6;
  const gap = 3;
  const chartW = safe.length * barW + (safe.length - 1) * gap;
  const chartH = height;

  const labels = _dayLabelsForWindow(safe.length);
  const todayIdx = safe.length - 1;

  return (
    <svg
      viewBox={`0 0 ${chartW} ${chartH}`}
      width={chartW}
      height={chartH}
      role="img"
      aria-label={`7-day opens: ${safe.join(", ")}`}
      data-testid={testid}
      style={{ overflow: "visible" }}
    >
      {safe.map((n, i) => {
        const h = n === 0 ? 2 : Math.max(3, Math.round((n / max) * (chartH - 2)));
        const x = i * (barW + gap);
        const y = chartH - h;
        const isToday = i === todayIdx;
        // Purple accent for the peak day + today; softer neutrals
        // for the rest. Zero-days get a barely-there rail so the
        // 7-day rhythm stays legible.
        let fill = "#D6CFE8";  // default idle
        if (n === 0) fill = "#EEE8F7";
        else if (isToday) fill = "#3D1A78";
        else if (n === max) fill = "#5B27B8";
        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barW}
              height={h}
              rx={1.5}
              fill={fill}
            >
              <title>{`${labels[i]} · ${n} open${n === 1 ? "" : "s"}`}</title>
            </rect>
          </g>
        );
      })}
    </svg>
  );
}
