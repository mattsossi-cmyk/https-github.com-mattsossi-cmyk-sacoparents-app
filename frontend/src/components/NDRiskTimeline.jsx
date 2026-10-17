/**
 * NDRiskTimeline — Full progression view for a parent's ND risk
 * re-assessments. Shows an area chart of overall score (1..16) over
 * time with tier bands, plus delta cards between each assessment.
 *
 * Empty state: nothing to show for a first-time assessor (a single data
 * point renders the chart with a helpful "re-assess to see movement" hint).
 */
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  Dot,
} from "recharts";
import { TrendingDown, TrendingUp, Minus, Loader2, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const TIER_META = {
  low:      { label: "Low",      color: "#1F5C3B", bg: "#E6F4EC" },
  medium:   { label: "Medium",   color: "#8A5B00", bg: "#FFF6E5" },
  high:     { label: "High",     color: "#B02A2A", bg: "#F8D7D7" },
  critical: { label: "Critical", color: "#6E1616", bg: "#F1B7B7" },
};

function tierColor(tier) {
  return (TIER_META[tier] || TIER_META.low).color;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const meta = TIER_META[p.tier] || TIER_META.low;
  return (
    <div className="rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 shadow-lg text-xs">
      <div className="font-bold text-[#1A1330]">{p.dateLong}</div>
      <div className="mt-1 text-[#4B4567]">
        Score <strong>{p.score}</strong> · T{p.threat} × V{p.vuln}
      </div>
      <div className="mt-1 inline-flex items-center gap-1.5">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{ background: meta.color }}
        />
        <span className="font-bold" style={{ color: meta.color }}>
          {meta.label} tier
        </span>
      </div>
    </div>
  );
}

function CustomDot(props) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  return (
    <Dot cx={cx} cy={cy} r={5} fill={tierColor(payload.tier)} stroke="#fff" strokeWidth={2} />
  );
}

function DeltaCard({ from, to }) {
  const delta = to.score - from.score;
  const tierChanged = from.tier !== to.tier;
  const arrow =
    delta < 0 ? <TrendingDown size={14} /> :
    delta > 0 ? <TrendingUp size={14} /> :
    <Minus size={14} />;
  // Improvement = score dropped; regression = score rose.
  const tone =
    delta < 0 ? { c: "#1F5C3B", bg: "#E6F4EC", label: "Improved" } :
    delta > 0 ? { c: "#B02A2A", bg: "#F8D7D7", label: "Regressed" } :
    { c: "#4B4567", bg: "#F0EEF8", label: "Held steady" };
  const fromMeta = TIER_META[from.tier] || TIER_META.low;
  const toMeta = TIER_META[to.tier] || TIER_META.low;
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
      data-testid={`nd-timeline-delta-${to.id}`}
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#6A5799]">
          {from.dateLong} → {to.dateLong}
        </div>
        <span
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.6875rem] font-bold"
          style={{ background: tone.bg, color: tone.c }}
        >
          {arrow}
          {tone.label} {delta === 0 ? "" : `${delta > 0 ? "+" : ""}${delta} pts`}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-sm text-[#1A1330]">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.6875rem] font-bold"
          style={{ background: fromMeta.bg, color: fromMeta.color }}
        >
          {fromMeta.label}
        </span>
        <span className="text-[#6A5799]">→</span>
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.6875rem] font-bold"
          style={{ background: toMeta.bg, color: toMeta.color }}
        >
          {toMeta.label}
        </span>
        {tierChanged && (
          <span className="text-[0.6875rem] text-[#4B4567] italic">tier changed</span>
        )}
      </div>
    </div>
  );
}

export default function NDRiskTimeline({ highlightId }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/nd-risk/assessments/me", {
          params: { limit: 50 },
        });
        setItems(data.items || []);
      } catch (err) {
        logError("Could not load ND risk timeline", err);
        setError("Could not load timeline.");
      }
    })();
  }, []);

  if (items === null && !error) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-6 inline-flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="nd-timeline-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Loading progression…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-3xl border border-[#F8D7D7] bg-[#FFF4F4] p-6 text-sm text-[#B02A2A]"
        data-testid="nd-timeline-error"
      >
        {error}
      </div>
    );
  }

  // Sort oldest → newest for charting
  const chrono = [...(items || [])]
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .map((row, idx) => {
      const s = row.scoring || {};
      return {
        id: row.assessment_id,
        idx: idx + 1,
        date: formatDate(row.created_at),
        dateLong: new Date(row.created_at).toLocaleString(),
        score: s.total_score || 0,
        threat: s.threat_score || 0,
        vuln: s.vulnerability_score || 0,
        tier: s.tier || "low",
      };
    });

  if (chrono.length === 0) {
    return (
      <div
        className="rounded-3xl border border-dashed border-[#E5E0EE] bg-[#FAF8FE] p-8 text-center"
        data-testid="nd-timeline-empty"
      >
        <div className="font-serif text-lg text-[#1A1330]">No timeline yet</div>
        <p className="text-sm text-[#4B4567] mt-1 max-w-md mx-auto">
          Once you complete your first ND Risk Assessment, this space will show
          your tier progression across every re-assessment so you can see
          whether interventions are working.
        </p>
        <Link
          to="/nd-risk-assessment"
          data-testid="nd-timeline-empty-cta"
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-semibold"
        >
          Take your first assessment
        </Link>
      </div>
    );
  }

  const latest = chrono[chrono.length - 1];
  const previous = chrono.length >= 2 ? chrono[chrono.length - 2] : null;
  const first = chrono[0];
  const lifetimeDelta = latest.score - first.score;
  const daysSinceLatest = Math.max(
    0,
    Math.floor((Date.now() - new Date(items[0].created_at)) / (1000 * 60 * 60 * 24)),
  );

  return (
    <div data-testid="nd-timeline">
      {/* Header stats */}
      <div className="grid sm:grid-cols-3 gap-3 mb-4">
        <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
          <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#6A5799]">
            Latest tier
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold"
              style={{
                background: (TIER_META[latest.tier] || TIER_META.low).bg,
                color:      (TIER_META[latest.tier] || TIER_META.low).color,
              }}
              data-testid="nd-timeline-latest-tier"
            >
              {(TIER_META[latest.tier] || TIER_META.low).label}
            </span>
            <span className="text-lg font-bold text-[#1A1330]">{latest.score}/16</span>
          </div>
          <div className="text-[0.6875rem] text-[#6A5799] mt-1">
            {daysSinceLatest === 0
              ? "Assessed today"
              : `${daysSinceLatest} day${daysSinceLatest === 1 ? "" : "s"} ago`}
          </div>
        </div>

        <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
          <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#6A5799]">
            Since first assessment
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            {lifetimeDelta < 0 && <TrendingDown size={18} className="text-[#1F5C3B]" />}
            {lifetimeDelta > 0 && <TrendingUp size={18} className="text-[#B02A2A]" />}
            {lifetimeDelta === 0 && <Minus size={18} className="text-[#4B4567]" />}
            <span
              className="text-lg font-bold"
              style={{
                color:
                  lifetimeDelta < 0 ? "#1F5C3B" :
                  lifetimeDelta > 0 ? "#B02A2A" : "#4B4567",
              }}
              data-testid="nd-timeline-lifetime-delta"
            >
              {lifetimeDelta > 0 ? "+" : ""}
              {lifetimeDelta} pts
            </span>
          </div>
          <div className="text-[0.6875rem] text-[#6A5799] mt-1">
            {chrono.length} assessment{chrono.length === 1 ? "" : "s"} logged
          </div>
        </div>

        <Link
          to="/nd-risk-assessment"
          className="rounded-2xl border border-[#3D1A78] bg-[#3D1A78] p-4 text-white hover:bg-[#2E1258] transition"
          data-testid="nd-timeline-reassess-cta"
        >
          <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold opacity-80">
            Re-assess
          </div>
          <div className="mt-1 inline-flex items-center gap-2 text-sm font-bold">
            <RefreshCw size={14} /> Take a new assessment
          </div>
          <div className="text-[0.6875rem] opacity-80 mt-1">
            Recommended every 30 days.
          </div>
        </Link>
      </div>

      {/* Chart */}
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-4 sm:p-6">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
          <div>
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Tier progression
            </div>
            <div className="font-serif text-lg text-[#1A1330]">
              Overall score over time (lower = safer)
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 text-[0.625rem]">
            {(["low", "medium", "high", "critical"]).map((t) => (
              <span
                key={t}
                className="px-2 py-0.5 rounded-full font-semibold"
                style={{ background: TIER_META[t].bg, color: TIER_META[t].color }}
              >
                {TIER_META[t].label}
              </span>
            ))}
          </div>
        </div>

        <div className="w-full h-64" data-testid="nd-timeline-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chrono} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EFECF6" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#8471B3", fontSize: 11 }}
                axisLine={{ stroke: "#E5E0EE" }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 16]}
                ticks={[0, 3, 8, 12, 16]}
                tick={{ fill: "#8471B3", fontSize: 11 }}
                axisLine={{ stroke: "#E5E0EE" }}
                tickLine={false}
              />
              {/* Tier bands as colored ReferenceAreas */}
              <ReferenceArea y1={0}  y2={3}  fill={TIER_META.low.bg}      fillOpacity={0.5} />
              <ReferenceArea y1={3}  y2={8}  fill={TIER_META.medium.bg}   fillOpacity={0.5} />
              <ReferenceArea y1={8}  y2={12} fill={TIER_META.high.bg}     fillOpacity={0.5} />
              <ReferenceArea y1={12} y2={16} fill={TIER_META.critical.bg} fillOpacity={0.5} />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3D1A78"
                strokeWidth={2.5}
                dot={<CustomDot />}
                activeDot={{ r: 7, stroke: "#fff", strokeWidth: 2 }}
                isAnimationActive
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {chrono.length === 1 && (
          <div className="mt-3 text-xs text-[#6A5799] italic text-center">
            One data point so far. Re-assess in 30 days to start tracking movement.
          </div>
        )}
      </div>

      {/* Delta cards between consecutive assessments (newest → oldest pair) */}
      {previous && (
        <div className="mt-6">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Movement between assessments
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            {chrono
              .slice(1)
              .reverse()
              .map((to, i) => {
                const from = chrono[chrono.length - 2 - i];
                return <DeltaCard key={to.id} from={from} to={to} />;
              })}
          </div>
        </div>
      )}
    </div>
  );
}
