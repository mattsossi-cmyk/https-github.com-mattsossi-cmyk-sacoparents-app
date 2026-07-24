import { useEffect, useState } from "react";
import { Loader2, TrendingUp, AlertCircle, Compass } from "lucide-react";
import { api } from "../lib/api";

/**
 * SpecialNeedsScoreDashboard — the 7-coordination-score dashboard that
 * lives above the AI narrative reports.
 *
 * Fetches from `GET /api/neurodivergent/scores` and renders:
 *   - The recommended co-parenting structure (Cooperative / Structured /
 *     Parallel) with an accompanying blurb.
 *   - Seven dimension bars, one per coordination score. Bars with
 *     `no_signal: true` render as "not enough answers yet" so we never
 *     imply a 0 score when the parent simply didn't answer.
 *   - A short "flags" line summarising how many domain items came back
 *     as "I don't know" / "Parents disagree" / "Not applicable".
 */

const BUCKET_COLOR = {
  "Strong coordination":         "bg-[#1F7A5A]",
  "Working coordination":        "bg-[#4a8f5f]",
  "Inconsistent coordination":   "bg-[#C28771]",
  "Coordination breaking down":  "bg-[#C2481F]",
  "Coordination has broken down":"bg-[#8C2410]",
};

const STRUCTURE_STYLES = {
  cooperative: {
    bg: "bg-[#E4F4EC]",
    accent: "text-[#1F5C3B]",
    chip: "bg-[#1F5C3B] text-white",
  },
  structured: {
    bg: "bg-[#EFE9F9]",
    accent: "text-[#3D1A78]",
    chip: "bg-[#3D1A78] text-white",
  },
  parallel: {
    bg: "bg-[#FEF1EC]",
    accent: "text-[#8C3A1B]",
    chip: "bg-[#8C3A1B] text-white",
  },
};

function DimensionBar({ label, dim }) {
  const barColor = BUCKET_COLOR[dim.bucket] || "bg-[#857E9C]";
  return (
    <div className="py-2.5 border-b border-[#F0EBF7] last:border-0" data-testid={`nd-dim-${label}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="text-sm text-[#1A1330] font-semibold">{dim.label}</div>
        <div className="text-xs text-[#857E9C] tabular-nums">
          {dim.no_signal ? "—" : `${dim.score}/100`}
        </div>
      </div>
      {dim.no_signal ? (
        <div className="text-xs text-[#857E9C] italic">
          Not enough answers yet — {dim.items_total} question
          {dim.items_total === 1 ? "" : "s"} in this dimension.
        </div>
      ) : (
        <>
          <div className="h-1.5 rounded-full bg-[#EFE9F9] overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all`}
              style={{ width: `${dim.score}%` }}
            />
          </div>
          <div className="text-[11px] text-[#4B4567] mt-1">{dim.bucket}</div>
        </>
      )}
    </div>
  );
}

function FlagsLine({ dimensions }) {
  const totals = Object.values(dimensions || {}).reduce(
    (a, d) => {
      const t = d.tags || {};
      a.na += t.na || 0;
      a.dont_know += t.dont_know || 0;
      a.disagree += t.disagree || 0;
      a.unanswered += t.unanswered || 0;
      return a;
    },
    { na: 0, dont_know: 0, disagree: 0, unanswered: 0 }
  );
  const chips = [];
  if (totals.disagree)
    chips.push(`${totals.disagree} where parents disagree`);
  if (totals.dont_know)
    chips.push(`${totals.dont_know} "I do not know"`);
  if (totals.unanswered)
    chips.push(`${totals.unanswered} not answered yet`);
  if (chips.length === 0) return null;
  return (
    <div
      className="mt-4 rounded-2xl bg-[#FFF6EC] border border-[#EED3B5] p-3 text-xs text-[#8C5A2C] flex items-start gap-2"
      data-testid="nd-flags-line"
    >
      <AlertCircle size={13} className="shrink-0 mt-0.5" />
      <span>
        Items to bring to your coach or mediator: {chips.join(" · ")}.
      </span>
    </div>
  );
}

export default function SpecialNeedsScoreDashboard() {
  const [state, setState] = useState({ loading: true, data: null });

  useEffect(() => {
    let cancelled = false;
    api
      .get("/neurodivergent/scores")
      .then((r) => {
        if (!cancelled) setState({ loading: false, data: r.data });
      })
      .catch(() => {
        if (!cancelled) setState({ loading: false, data: null });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-6 flex items-center gap-2 text-sm text-[#857E9C]"
        data-testid="nd-scores-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Loading your
        coordination dashboard…
      </div>
    );
  }

  if (!state.data) return null;

  const { dimensions, structure, overall_signal, consistency_can_flex } = state.data;
  const dimEntries = Object.entries(dimensions || {});
  const hasAny = dimEntries.some(([, d]) => !d.no_signal);
  const structureStyle =
    (structure && STRUCTURE_STYLES[structure.id]) || STRUCTURE_STYLES.structured;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8"
      data-testid="nd-scores-dashboard"
    >
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
            <TrendingUp size={12} /> Coordination dashboard
          </div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-1 leading-tight">
            Seven coordination scores — one plan for your child
          </h2>
          <p className="text-sm text-[#4B4567] mt-1 max-w-2xl">
            These are not &ldquo;good parent / bad parent&rdquo; numbers. Each score
            measures a specific pattern of coordination between the two
            homes. Higher means smoother — for your child.
          </p>
        </div>
        {overall_signal !== null && overall_signal !== undefined && (
          <div className="text-right shrink-0">
            <div className="text-xs uppercase tracking-[0.16em] font-bold text-[#857E9C]">
              Overall signal
            </div>
            <div className="font-serif text-3xl text-[#3D1A78] leading-none mt-1 tabular-nums">
              {overall_signal}
              <span className="text-base text-[#857E9C]">/100</span>
            </div>
          </div>
        )}
      </div>

      {structure && (
        <div
          className={`rounded-2xl ${structureStyle.bg} p-4 mb-5 flex items-start gap-3`}
          data-testid="nd-structure-recommendation"
        >
          <Compass size={16} className={`shrink-0 mt-0.5 ${structureStyle.accent}`} />
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[10px] uppercase tracking-[0.16em] font-bold px-2 py-0.5 rounded-full ${structureStyle.chip}`}
              >
                Recommended
              </span>
              <span className={`text-sm font-bold ${structureStyle.accent}`}>
                {structure.label}
              </span>
            </div>
            <p className="text-sm text-[#1A1330] leading-relaxed">
              {structure.blurb}
            </p>
          </div>
        </div>
      )}

      {hasAny ? (
        <div>
          {dimEntries.map(([key, dim]) => (
            <DimensionBar key={key} label={key} dim={dim} />
          ))}
        </div>
      ) : (
        <div className="text-sm text-[#857E9C] italic py-4">
          Answer the coordination questions in the assessment to see your
          seven scores here.
        </div>
      )}

      <FlagsLine dimensions={dimensions} />

      {consistency_can_flex && consistency_can_flex.length > 0 && (
        <div
          className="mt-3 rounded-2xl bg-[#E4F4EC] border border-[#C6DECF] p-3 text-xs text-[#1F5C3B]"
          data-testid="nd-flex-areas"
        >
          <span className="font-bold">Areas your child can hold flexibly:</span>{" "}
          {consistency_can_flex.join(" · ")}. Identical homes aren&apos;t the
          goal — this list won&apos;t drag your Consistency score.
        </div>
      )}
    </section>
  );
}
