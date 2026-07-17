import { Zap, ShieldCheck, Heart, MessageCircle } from "lucide-react";

/**
 * ReadinessDashboard — court-quality visualisation of the deterministic
 * readiness scores. Renders four dimension bars + an overall composite,
 * each accompanied by a one-sentence AI narrative.
 *
 * Props
 *   readiness         — the compute_readiness() bundle from the backend:
 *                         { overall, label, dimensions: {communication, trust, child_alignment, conflict} }
 *   dimensionNarratives — optional dict of one-liners keyed by dimension id
 */

const DIM_META = {
  communication: { label: "Communication", Icon: MessageCircle, color: "#3D1A78" },
  trust:         { label: "Trust",         Icon: ShieldCheck,   color: "#5E2DB5" },
  child_alignment: { label: "Child alignment", Icon: Heart,     color: "#B84EBB" },
  conflict:      { label: "Conflict (managed)", Icon: Zap,       color: "#2DB5B5" },
};

function scoreTone(score) {
  if (score >= 75) return { hex: "#1F7A3A", label: "Strong" };
  if (score >= 55) return { hex: "#B98211", label: "Developing" };
  return { hex: "#8B1A1A", label: "Needs focus" };
}

function DimensionBar({ id, dim, narrative }) {
  const meta = DIM_META[id] || { label: id, Icon: MessageCircle, color: "#3D1A78" };
  const { Icon, color } = meta;
  const score = Math.max(0, Math.min(100, Number(dim?.score ?? 0)));
  const tone = scoreTone(score);
  return (
    <div className="py-4 border-b border-[#E5E0EE] last:border-b-0" data-testid={`readiness-dim-${id}`}>
      <div className="flex items-center gap-3">
        <div className="shrink-0 w-9 h-9 rounded-full grid place-items-center" style={{ background: `${color}18`, color }}>
          <Icon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2">
            <div className="font-semibold text-[#1A1330]">{meta.label}</div>
            <div className="text-sm font-mono text-[#4B4567]">
              <span data-testid={`readiness-dim-${id}-score`}>{Math.round(score)}</span>
              <span className="text-[#857E9C]">/100</span>
              <span className="ml-2 text-xs font-semibold" style={{ color: tone.hex }}>
                · {tone.label}
              </span>
            </div>
          </div>
          <div className="mt-1.5 h-2 rounded-full bg-[#E5E0EE] overflow-hidden">
            <div
              className="h-full transition-all"
              style={{
                width: `${score}%`,
                background: `linear-gradient(90deg, ${color} 0%, ${color}DD 100%)`,
              }}
            />
          </div>
          {narrative && (
            <div className="text-xs text-[#4B4567] mt-1.5 italic leading-relaxed">
              {narrative}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReadinessDashboard({ readiness, dimensionNarratives = {}, narrative }) {
  if (!readiness || !readiness.dimensions) return null;
  const { overall = 0, label = "", dimensions } = readiness;
  const overallTone = scoreTone(overall);

  return (
    <section
      className="bg-white rounded-3xl border border-[#E5E0EE] shadow-sm p-6 sm:p-8"
      data-testid="readiness-dashboard"
    >
      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <div className="eyebrow text-[#3D1A78]">Readiness assessment</div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1">
            {label}
          </h2>
        </div>
        <div
          className="shrink-0 flex flex-col items-center rounded-2xl px-4 py-3 border-2"
          style={{ borderColor: overallTone.hex + "40", background: overallTone.hex + "0A" }}
          data-testid="readiness-overall"
        >
          <div className="text-xs uppercase tracking-wider text-[#4B4567]">Overall</div>
          <div className="text-3xl font-serif font-bold" style={{ color: overallTone.hex }}>
            {overall}
          </div>
          <div className="text-[10px] text-[#857E9C]">/ 100</div>
        </div>
      </div>

      {narrative && (
        <p className="text-[#1A1330] leading-relaxed mt-3 mb-4">{narrative}</p>
      )}

      <div className="mt-4">
        {["communication", "trust", "child_alignment", "conflict"].map((k) => (
          dimensions[k] ? (
            <DimensionBar
              key={k}
              id={k}
              dim={dimensions[k]}
              narrative={dimensionNarratives?.[k]}
            />
          ) : null
        ))}
      </div>

      <p className="text-[11px] text-[#857E9C] mt-4 leading-relaxed">
        These scores are computed from your actual answers using a transparent,
        deterministic formula. The narrative is written by an AI coach interpreting
        those numbers — never inventing them.
      </p>
    </section>
  );
}
