import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  Loader2,
  Lightbulb,
  Calendar,
} from "lucide-react";
import { api } from "../lib/api";

/**
 * GrowthTracker — Longitudinal readiness growth for a single parent.
 *
 * Renders three layers of insight, in order of what a parent will read first:
 *   1. A short coach-authored narrative ("Since 30 days ago you're up 8
 *      points in Communication…")
 *   2. A line chart of overall readiness over time with a "Prepared" (75)
 *      threshold line.
 *   3. A grid of dimension-level delta chips (Communication, Trust, Child
 *      alignment, Conflict) showing +/- movement per window.
 *
 * Empty and "single snapshot" states are handled explicitly — we never
 * fabricate movement when there's no history to compare against.
 */

const DIMENSION_ORDER = ["communication", "trust", "child_alignment", "conflict"];
const DIMENSION_LABELS = {
  communication: "Communication",
  trust: "Trust",
  child_alignment: "Child alignment",
  conflict: "Conflict",
};

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

function DeltaBadge({ delta, size = "sm" }) {
  if (delta === null || delta === undefined) {
    return (
      <span
        className={`inline-flex items-center gap-0.5 text-[#857E9C] ${
          size === "lg" ? "text-sm" : "text-xs"
        }`}
      >
        <Minus size={size === "lg" ? 14 : 11} /> —
      </span>
    );
  }
  const positive = delta > 0;
  const negative = delta < 0;
  const color = positive
    ? "text-[#1F7A5A] bg-[#E4F4EC]"
    : negative
    ? "text-[#C2481F] bg-[#FEF1EC]"
    : "text-[#857E9C] bg-[#F5F2FA]";
  const Icon = positive ? TrendingUp : negative ? TrendingDown : Minus;
  const sign = positive ? "+" : "";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold ${
        size === "lg" ? "text-sm" : "text-xs"
      } ${color}`}
    >
      <Icon size={size === "lg" ? 14 : 11} />
      {sign}
      {delta}
    </span>
  );
}

function DimensionRow({ label, from, to, delta }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-[#F0EBF7] last:border-0">
      <div className="flex-1 text-sm text-[#1A1330]">{label}</div>
      <div className="text-xs text-[#857E9C] tabular-nums">
        {from ?? "—"} → <span className="text-[#1A1330] font-semibold">{to ?? "—"}</span>
      </div>
      <div className="w-16 text-right">
        <DeltaBadge delta={delta} />
      </div>
    </div>
  );
}

function WindowCard({ window, title }) {
  if (!window) {
    return (
      <div className="rounded-2xl border border-dashed border-[#E5E0EE] bg-white p-4 text-center">
        <div className="text-xs uppercase tracking-[0.16em] font-bold text-[#857E9C] mb-1">
          {title}
        </div>
        <p className="text-xs text-[#857E9C]">
          Not enough history yet. Complete another Mediation Summary to unlock
          this comparison.
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="eyebrow text-[#3D1A78]">{title}</div>
          <div className="text-[11px] text-[#857E9C] mt-0.5">
            {formatDate(window.from_at)} → {formatDate(window.to_at)}
          </div>
        </div>
        <DeltaBadge delta={window.overall.delta} size="lg" />
      </div>
      <div>
        {DIMENSION_ORDER.map((k) => (
          <DimensionRow
            key={k}
            label={DIMENSION_LABELS[k]}
            from={window.dimensions[k]?.from}
            to={window.dimensions[k]?.to}
            delta={window.dimensions[k]?.delta}
          />
        ))}
      </div>
    </div>
  );
}

function InsightsPanel({ insights }) {
  if (!insights?.length) return null;
  return (
    <div
      className="rounded-2xl bg-gradient-to-br from-[#F5F2FA] to-white border border-[#E5E0EE] p-4"
      data-testid="growth-insights"
    >
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb size={14} className="text-[#3D1A78]" />
        <h3 className="text-xs uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
          What your growth is telling us
        </h3>
      </div>
      <ul className="space-y-1.5">
        {insights.map((ins, i) => (
          <li
            key={i}
            className="text-sm text-[#1A1330] leading-relaxed"
            data-testid={`growth-insight-${ins.kind}`}
          >
            {ins.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function GrowthChart({ points }) {
  const data = points.map((p) => ({
    at: p.at,
    date: formatDate(p.at),
    overall: p.overall,
  }));
  return (
    <div className="rounded-2xl bg-white border border-[#E5E0EE] p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="eyebrow text-[#3D1A78]">Readiness over time</div>
          <div className="text-[11px] text-[#857E9C] mt-0.5">
            Higher is more prepared. Threshold to &ldquo;Prepared&rdquo; is 75.
          </div>
        </div>
      </div>
      <div className="h-56" data-testid="growth-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#EFEAF7" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "#857E9C" }}
              stroke="#E5E0EE"
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fontSize: 11, fill: "#857E9C" }}
              stroke="#E5E0EE"
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: "1px solid #E5E0EE",
                fontSize: 12,
              }}
              formatter={(v) => [`${v}/100`, "Overall"]}
            />
            <ReferenceLine
              y={75}
              stroke="#1F7A5A"
              strokeDasharray="4 4"
              label={{
                value: "Prepared",
                fontSize: 10,
                fill: "#1F7A5A",
                position: "insideTopRight",
              }}
            />
            <ReferenceLine
              y={55}
              stroke="#C28771"
              strokeDasharray="4 4"
              label={{
                value: "Moderately ready",
                fontSize: 10,
                fill: "#C28771",
                position: "insideTopRight",
              }}
            />
            <Line
              type="monotone"
              dataKey="overall"
              stroke="#3D1A78"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#3D1A78" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function GrowthTracker() {
  const [state, setState] = useState({
    loading: true,
    data: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    api
      .get("/analytics/growth")
      .then((r) => {
        if (!cancelled) setState({ loading: false, data: r.data, error: null });
      })
      .catch((e) => {
        if (!cancelled)
          setState({ loading: false, data: null, error: e?.message || "load failed" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-6 flex items-center gap-2 text-sm text-[#857E9C]"
        data-testid="growth-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Loading your growth
        timeline…
      </div>
    );
  }

  if (state.error || !state.data) {
    return (
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 text-sm text-[#857E9C]">
        Couldn&apos;t load growth tracking. Try refreshing.
      </div>
    );
  }

  const { has_history, points, windows, insights, current, days_tracked } =
    state.data;

  if (!current) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-[#FFF9F1] to-white p-6"
        data-testid="growth-empty"
      >
        <div className="flex items-start gap-4">
          <div className="shrink-0 w-12 h-12 rounded-2xl bg-[#3D1A78]/12 grid place-items-center">
            <TrendingUp size={20} className="text-[#3D1A78]" />
          </div>
          <div>
            <div className="eyebrow text-[#3D1A78]">Growth over time</div>
            <h3 className="font-serif text-xl text-[#1A1330] mt-1">
              Your growth story starts here
            </h3>
            <p className="text-sm text-[#4B4567] mt-2 max-w-xl">
              Generate your first Mediation Summary from the Reports tab to
              start tracking your readiness. Each summary saves a snapshot so
              you can see how you&apos;re growing — dimension by dimension —
              across the weeks and months ahead.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-6 space-y-5"
      data-testid="growth-tracker"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
            <Sparkles size={12} /> Longitudinal growth
          </div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-1 leading-tight">
            How you&apos;re growing over time
          </h2>
          <p className="text-sm text-[#4B4567] mt-1 flex items-center gap-1.5">
            <Calendar size={12} className="text-[#857E9C]" />
            {days_tracked > 0
              ? `${days_tracked} day${days_tracked === 1 ? "" : "s"} of tracked prep · ${points.length} snapshot${points.length === 1 ? "" : "s"}`
              : `${points.length} snapshot${points.length === 1 ? "" : "s"} so far`}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-[0.16em] font-bold text-[#857E9C]">
            Current
          </div>
          <div
            className="font-serif text-4xl text-[#3D1A78] leading-none mt-1"
            data-testid="growth-current-score"
          >
            {current.overall}
            <span className="text-lg text-[#857E9C] font-sans">/100</span>
          </div>
          {current.label && (
            <div className="text-xs text-[#4B4567] mt-1">{current.label}</div>
          )}
        </div>
      </div>

      <InsightsPanel insights={insights} />

      {points.length >= 2 ? (
        <GrowthChart points={points} />
      ) : (
        <div className="rounded-2xl bg-[#F5F2FA] border border-[#E5E0EE] p-4 text-sm text-[#4B4567]">
          You&apos;ve got your first snapshot. Generate a new Mediation
          Summary in a few weeks to unlock the growth chart and comparisons.
        </div>
      )}

      {has_history && (
        <div>
          <h3 className="text-xs uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-3">
            Compared to earlier windows
          </h3>
          <div className="grid gap-3 md:grid-cols-3" data-testid="growth-windows">
            <WindowCard window={windows["30d"]} title="Last 30 days" />
            <WindowCard window={windows["60d"]} title="Last 60 days" />
            <WindowCard window={windows["90d"]} title="Last 90 days" />
          </div>
        </div>
      )}
    </div>
  );
}
