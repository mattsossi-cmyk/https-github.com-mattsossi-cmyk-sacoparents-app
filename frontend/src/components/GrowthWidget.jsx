import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { api } from "../lib/api";

/**
 * GrowthWidget — Compact dashboard chip showing readiness + best delta.
 *
 * Reuses `GET /api/analytics/growth`. Picks the best window to display in
 * this order: 30d → 60d → 90d → all-time (whichever has a comparable
 * baseline). Hides itself entirely when the parent has no snapshots yet
 * so the dashboard stays clean for first-time visitors.
 */

const WINDOW_LABEL = { 30: "this month", 60: "since 60 days ago", 90: "this quarter" };

function pickBestWindow(windows) {
  // Prefer the shortest window that actually has a comparison.
  for (const d of [30, 60, 90]) {
    const w = windows?.[`${d}d`];
    if (w && w.overall && w.overall.delta !== null && w.overall.delta !== undefined) {
      return w;
    }
  }
  return null;
}

function DeltaChip({ delta }) {
  if (delta === null || delta === undefined) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#6E6787] bg-[#F5F2FA] px-2 py-0.5 rounded-full">
        <Minus size={11} /> —
      </span>
    );
  }
  const positive = delta > 0;
  const negative = delta < 0;
  const styles = positive
    ? "text-[#1F7A5A] bg-[#E4F4EC]"
    : negative
    ? "text-[#C2481F] bg-[#FEF1EC]"
    : "text-[#6E6787] bg-[#F5F2FA]";
  const Icon = positive ? TrendingUp : negative ? TrendingDown : Minus;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${styles}`}
      data-testid="growth-widget-delta"
    >
      <Icon size={11} />
      {positive ? "+" : ""}
      {delta}
    </span>
  );
}

export default function GrowthWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/analytics/growth")
      .then((r) => {
        if (!cancelled) setData(r.data);
      })
      .catch(() => {
        /* silent — widget just doesn't render */
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || !data || !data.current) return null;

  const { current, windows, days_tracked, points } = data;
  const bestWindow = pickBestWindow(windows);
  const windowLabel = bestWindow ? WINDOW_LABEL[bestWindow.days] : null;

  return (
    <Link
      to="/my-plan#growth"
      className="block rounded-3xl bg-gradient-to-br from-[#F5F2FA] via-white to-[#FFF9F1] border border-[#E5E0EE] p-5 sm:p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all mb-8"
      data-testid="dashboard-growth-widget"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="eyebrow mb-2 flex items-center gap-1.5 text-[#3D1A78]">
            <Sparkles size={12} /> Your growth
          </div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <div className="font-serif text-3xl text-[#1A1330] leading-none">
              <span data-testid="growth-widget-score">{current.overall}</span>
              <span className="text-base text-[#6E6787]">/100</span>
            </div>
            {bestWindow && <DeltaChip delta={bestWindow.overall.delta} />}
            {current.label && (
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-[0.1em]">
                {current.label}
              </span>
            )}
          </div>
          <div className="text-sm text-[#4B4567] mt-2">
            {bestWindow ? (
              bestWindow.overall.delta > 0 ? (
                <>
                  You&apos;re up{" "}
                  <span className="font-bold text-[#1F7A5A]">
                    {bestWindow.overall.delta} points
                  </span>{" "}
                  {windowLabel}. Real, measurable movement.
                </>
              ) : bestWindow.overall.delta < 0 ? (
                <>
                  You&apos;ve dipped{" "}
                  <span className="font-bold text-[#C2481F]">
                    {Math.abs(bestWindow.overall.delta)} points
                  </span>{" "}
                  {windowLabel} — a good moment to sit with your coach.
                </>
              ) : (
                <>Steady {windowLabel}. Consistency is its own kind of growth.</>
              )
            ) : (
              <>
                {points.length} snapshot{points.length === 1 ? "" : "s"} on file.{" "}
                Generate another Mediation Summary to unlock trend comparisons.
              </>
            )}
          </div>
          {days_tracked > 0 && (
            <div className="text-[11px] text-[#6E6787] mt-1">
              Tracking for {days_tracked} day{days_tracked === 1 ? "" : "s"}.
            </div>
          )}
        </div>
        <div className="shrink-0 inline-flex items-center gap-1 text-sm text-[#3D1A78] font-bold">
          See your growth
          <ChevronRight size={14} />
        </div>
      </div>
    </Link>
  );
}
