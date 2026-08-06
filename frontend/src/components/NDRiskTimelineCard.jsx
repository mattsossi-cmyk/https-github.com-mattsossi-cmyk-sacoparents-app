/**
 * NDRiskTimelineCard — Compact stepped-timeline for the Dashboard.
 * Hides itself for parents who have never assessed. Otherwise shows the
 * latest tier, a stepped list of the last 3 assessments (newest first)
 * with tier chips, and a deep-link to the full timeline.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
} from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const TIER_META = {
  low:      { label: "Low",      color: "#1F5C3B", bg: "#E6F4EC" },
  medium:   { label: "Medium",   color: "#8A5B00", bg: "#FFF6E5" },
  high:     { label: "High",     color: "#B02A2A", bg: "#F8D7D7" },
  critical: { label: "Critical", color: "#6E1616", bg: "#F1B7B7" },
};

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric", year: "numeric",
    });
  } catch {
    return "";
  }
}

export default function NDRiskTimelineCard() {
  const [items, setItems] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/nd-risk/assessments/me", { params: { limit: 5 } });
        setItems(data.items || []);
      } catch (err) {
        logError("Could not load ND risk timeline card", err);
        setItems([]);
      }
    })();
  }, []);

  // Loading or empty — hide entirely so we don't clutter first-time visitors.
  if (items === null || items.length === 0) return null;

  const chronoDesc = items; // API already returns newest-first
  const latest = chronoDesc[0];
  const previous = chronoDesc[1];
  const latestScoring = latest.scoring || {};
  const latestTier = TIER_META[latestScoring.tier] || TIER_META.low;

  const delta = previous
    ? (latestScoring.total_score || 0) - ((previous.scoring || {}).total_score || 0)
    : null;

  let trend = null;
  if (delta !== null) {
    if (delta < 0)      trend = { icon: <TrendingDown size={14} />, tone: "text-[#1F5C3B] bg-[#E6F4EC]", label: `Improved ${delta} pts` };
    else if (delta > 0) trend = { icon: <TrendingUp size={14} />,   tone: "text-[#B02A2A] bg-[#F8D7D7]", label: `Regressed +${delta} pts` };
    else                trend = { icon: <Minus size={14} />,        tone: "text-[#4B4567] bg-[#F0EEF8]", label: "Held steady" };
  }

  return (
    <Link
      to={`/nd-risk-assessment/result/${latest.assessment_id}#timeline`}
      className="block rounded-3xl border border-[#E5E0EE] bg-white p-5 hover:border-[#3D1A78] transition"
      data-testid="nd-risk-timeline-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="inline-flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#F0EEF8] text-[#3D1A78]">
            <ShieldCheck size={16} />
          </span>
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              ND Risk · Progression
            </div>
            <div className="font-serif text-lg text-[#1A1330]">
              Your tier over time
            </div>
          </div>
        </div>
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold"
          style={{ background: latestTier.bg, color: latestTier.color }}
          data-testid="nd-risk-timeline-card-latest-tier"
        >
          {latestTier.label}
        </span>
      </div>

      {trend && (
        <div className="mt-3">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold ${trend.tone}`}
            data-testid="nd-risk-timeline-card-trend"
          >
            {trend.icon}
            {trend.label} since previous
          </span>
        </div>
      )}

      {/* Stepped list — up to last 3 assessments */}
      <ol className="mt-4 space-y-3 relative">
        {chronoDesc.slice(0, 3).map((row, idx, arr) => {
          const s = row.scoring || {};
          const meta = TIER_META[s.tier] || TIER_META.low;
          const isLast = idx === arr.length - 1;
          return (
            <li key={row.assessment_id} className="relative pl-6" data-testid={`nd-risk-timeline-step-${idx}`}>
              {/* connector line */}
              {!isLast && (
                <span
                  aria-hidden
                  className="absolute left-[7px] top-4 bottom-[-14px] w-px bg-[#E5E0EE]"
                />
              )}
              {/* dot */}
              <span
                aria-hidden
                className="absolute left-0 top-1 w-4 h-4 rounded-full border-2 border-white"
                style={{ background: meta.color }}
              />
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="text-sm font-semibold text-[#1A1330]">
                  {fmtDate(row.created_at)}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold"
                    style={{ background: meta.bg, color: meta.color }}
                  >
                    {meta.label}
                  </span>
                  <span className="text-[11px] text-[#4B4567]">
                    {s.total_score}/16
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-4 inline-flex items-center gap-1.5 text-sm font-bold text-[#3D1A78]">
        See full timeline <ArrowRight size={14} />
      </div>
    </Link>
  );
}
