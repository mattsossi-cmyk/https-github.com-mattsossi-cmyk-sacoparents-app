/**
 * CaseAnalyticsCard.jsx — aggregate stats card shown at the top of
 * `/professional/joint-alignment/mine`. Fetches from
 * `GET /api/professional/joint-alignment/analytics` and renders a
 * 4-tile stat grid plus an assessment-lane breakdown.
 *
 * Data-minimisation: the endpoint only returns rollups, so this
 * card is safe to show to any authenticated caller — they never
 * see raw per-parent detail.
 */
import React, { useEffect, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  Timer,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

function fmtHours(h) {
  if (h === null || h === undefined) return "—";
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 24) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

function fmtPct(p) {
  if (p === null || p === undefined) return "—";
  return `${p}%`;
}

function fmtLane(lane) {
  if (!lane) return "—";
  return lane.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function CaseAnalyticsCard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/professional/joint-alignment/analytics")
      .then((r) => setStats(r.data))
      .catch((err) => {
        logError("analytics load failed", err);
        setError("Could not load analytics right now.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        className="rounded-2xl border border-[#E5E0EE] bg-white p-4 mb-4 text-xs text-[#6E6787]"
        data-testid="pj-analytics-loading"
      >
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-2xl border border-[#F1B0A9] bg-[#FEE4E2] px-4 py-3 mb-4 text-xs text-[#8A2C1E]"
        role="alert"
        aria-live="polite"
        data-testid="pj-analytics-error"
      >
        {error}
      </div>
    );
  }

  if (!stats || stats.total_cases === 0) {
    // Empty state — nothing to analyse yet.
    return null;
  }

  const tiles = [
    {
      key: "total",
      icon: BarChart3,
      label: "Total cases",
      value: String(stats.total_cases),
      hint: `${stats.active_cases} active · ${stats.completed_cases} complete · ${stats.cancelled_cases} cancelled`,
    },
    {
      key: "acceptance",
      icon: TrendingUp,
      label: "Acceptance rate",
      value: fmtPct(stats.acceptance_rate),
      hint: "Parents who opened their invitation.",
    },
    {
      key: "first_accept",
      icon: Timer,
      label: "Time to first accept",
      value: fmtHours(stats.avg_hours_to_first_accept),
      hint: "From mint to a parent clicking their link.",
    },
    {
      key: "complete",
      icon: CheckCircle2,
      label: "Time to both complete",
      value: fmtHours(stats.avg_hours_to_both_complete),
      hint: "From mint to both parents finishing.",
    },
  ];

  const laneEntries = Object.entries(stats.assessment_type_breakdown || {})
    .sort((a, b) => b[1] - a[1]);
  const laneMax = laneEntries.length > 0 ? laneEntries[0][1] : 0;

  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 mb-4"
      data-testid="pj-analytics-card"
    >
      <div className="flex items-baseline gap-2 flex-wrap mb-3">
        <BarChart3 size={14} className="text-[#3D1A78]" />
        <div className="text-[11px] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
          Intake funnel · at a glance
        </div>
        {stats.most_common_assessment_type && (
          <div
            className="ml-auto text-[11px] text-[#4B4567] inline-flex items-center gap-1"
            data-testid="pj-analytics-top-lane"
          >
            <Sparkles size={11} className="text-[#3D1A78]" />
            Top lane · <span className="font-semibold text-[#1A1330]">{fmtLane(stats.most_common_assessment_type)}</span>
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => {
          const Icon = t.icon;
          return (
            <div
              key={t.key}
              className="rounded-xl border border-[#E5E0EE] bg-[#FAF8FD] p-3"
              data-testid={`pj-analytics-tile-${t.key}`}
            >
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-white text-[#3D1A78] grid place-items-center shrink-0">
                  <Icon size={14} />
                </div>
                <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#4B4567]">
                  {t.label}
                </div>
              </div>
              <div
                className="mt-2 font-serif text-2xl text-[#1A1330]"
                data-testid={`pj-analytics-value-${t.key}`}
              >
                {t.value}
              </div>
              <div className="text-[11px] text-[#6E6787] leading-relaxed">
                {t.hint}
              </div>
            </div>
          );
        })}
      </div>

      {laneEntries.length > 1 && (
        <div className="mt-4" data-testid="pj-analytics-lane-breakdown">
          <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#4B4567] mb-2">
            Assessment lane breakdown
          </div>
          <ul className="space-y-1.5">
            {laneEntries.map(([lane, count]) => {
              const pct = laneMax > 0 ? Math.round((count / laneMax) * 100) : 0;
              return (
                <li key={lane} className="flex items-center gap-3" data-testid={`pj-analytics-lane-${lane}`}>
                  <div className="text-xs text-[#1A1330] w-40 shrink-0 truncate">
                    {fmtLane(lane)}
                  </div>
                  <div className="flex-1 h-2 rounded-full bg-[#F5F1FB] overflow-hidden">
                    <div
                      className="h-full bg-[#3D1A78] rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="text-xs text-[#4B4567] w-8 text-right shrink-0">{count}</div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
