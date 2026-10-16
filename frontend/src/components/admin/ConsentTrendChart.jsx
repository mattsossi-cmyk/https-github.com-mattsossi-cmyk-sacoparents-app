import React from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const short = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });

// Daily count of people who ticked both boxes (last 30 days, UTC). Counts only.
export function ConsentTrendChart({ daily }) {
  const total = daily.reduce((n, d) => n + d.people, 0);
  return (
    <section className="space-y-2" data-testid="admin-consent-trend">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="text-sm font-bold text-[#1A1330]">People who consented each day</h2>
        <span className="text-xs text-[#4B4567]" data-testid="admin-consent-trend-total">
          {total} in the last {daily.length} days (UTC)
        </span>
      </div>
      <div className="rounded-2xl border border-[#E5E0EE] bg-white p-3 h-56" data-testid="admin-consent-trend-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={daily} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
            <XAxis dataKey="date" tickFormatter={short} tick={{ fontSize: 10, fill: "#857E9C" }} interval="preserveStartEnd" minTickGap={24} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#857E9C" }} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: "#F2EBFC" }} labelFormatter={short} formatter={(v) => [v, "People"]} />
            <Bar dataKey="people" fill="#3D1A78" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
