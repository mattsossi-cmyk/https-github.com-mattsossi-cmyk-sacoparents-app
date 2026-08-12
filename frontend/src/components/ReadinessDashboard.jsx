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
  const { overall = 0, label = "", dimensions, profile, caveats, readiness_disclaimer } = readiness;
  const overallTone = scoreTone(overall);
  const profileOrder = ["communication", "trust", "child_alignment", "conflict"];

  return (
    <section
      className="bg-white rounded-3xl border border-[#E5E0EE] shadow-sm p-6 sm:p-8"
      data-testid="readiness-dashboard"
    >
      <div className="mb-3">
        <div className="eyebrow text-[#3D1A78]">Mediation-readiness profile</div>
        <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1">
          Your four-domain profile
        </h2>
      </div>

      {readiness_disclaimer && (
        <div
          className="rounded-2xl border border-[#3D1A78]/25 bg-[#F5F1FB] p-4 mb-4 text-sm text-[#1A1330] leading-relaxed"
          data-testid="readiness-disclaimer"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Read this first
          </div>
          {readiness_disclaimer}
        </div>
      )}

      {Array.isArray(caveats) && caveats.length > 0 && (
        <div
          className="rounded-2xl border border-[#9A3A23]/25 bg-[#FDF3F0] p-4 mb-4 text-sm text-[#1A1330] leading-relaxed space-y-2"
          data-testid="readiness-caveats"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#9A3A23] mb-1">
            Important caveats
          </div>
          {caveats.map((c, i) => (
            <p key={`cav-${i}`}>{c}</p>
          ))}
        </div>
      )}

      {profile ? (
        <div className="space-y-4">
          {profileOrder.map((k) => {
            const p = profile[k];
            if (!p) return null;
            const levelTone =
              p.level === "solid"
                ? { hex: "#1F7A3A", label: "Solid" }
                : p.level === "developing"
                ? { hex: "#B98211", label: "Developing" }
                : { hex: "#8B1A1A", label: "Emerging" };
            return (
              <div
                key={k}
                className="rounded-2xl border border-[#E5E0EE] bg-[#FAF9FD] p-4 sm:p-5"
                data-testid={`readiness-profile-${k}`}
              >
                <div className="flex items-baseline justify-between gap-3 mb-1">
                  <div className="font-semibold text-[#1A1330] text-lg">{p.label}</div>
                  <div
                    className="text-[10px] uppercase tracking-[0.18em] font-bold px-2.5 py-0.5 rounded-full"
                    style={{ background: levelTone.hex + "18", color: levelTone.hex }}
                  >
                    {levelTone.label}
                  </div>
                </div>
                <div className="text-xs italic text-[#857E9C] mb-2">
                  {p.core_question}
                </div>
                <div className="text-sm font-semibold text-[#1A1330] mb-1.5">{p.headline}</div>
                <p className="text-sm text-[#4B4567] leading-relaxed">{p.narrative}</p>
                {p.strengths?.length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#1F7A3A] mb-1">
                      What&rsquo;s working
                    </div>
                    <ul className="text-sm text-[#1A1330] space-y-0.5 list-disc list-inside">
                      {p.strengths.map((s, i) => (
                        <li key={`str-${k}-${i}`}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {p.growth_areas?.length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#B98211] mb-1">
                      Growth areas
                    </div>
                    <ul className="text-sm text-[#1A1330] space-y-0.5 list-disc list-inside">
                      {p.growth_areas.map((s, i) => (
                        <li key={`gr-${k}-${i}`}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {p.preparation_recommendations?.length > 0 && (
                  <div className="mt-3 rounded-xl bg-white border border-[#3D1A78]/15 p-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1.5">
                      Specific preparation recommendations
                    </div>
                    <ol className="text-sm text-[#1A1330] space-y-1 list-decimal list-inside">
                      {p.preparation_recommendations.map((r, i) => (
                        <li key={`rec-${k}-${i}`}>{r}</li>
                      ))}
                    </ol>
                  </div>
                )}
                <div
                  className="mt-3 text-[11px] uppercase tracking-[0.14em] text-[#857E9C]"
                  data-testid={`readiness-profile-${k}-secondary-score`}
                >
                  Secondary score · {Math.round(p.secondary_score)}/100
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        // Fallback for legacy consumers that don't yet have the profile.
        <div className="mt-4">
          {profileOrder.map((k) => (
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
      )}

      {/* Overall number — deprioritised, appears after the profile. */}
      <div
        className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-4 flex items-center justify-between gap-3"
        data-testid="readiness-overall"
      >
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#857E9C] mb-0.5">
            Secondary indicator only
          </div>
          <div className="text-sm text-[#4B4567] leading-relaxed">
            {readiness.secondary_score?.note ||
              "Numerical scores reflect completeness of preparation, not readiness."}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-[10px] uppercase tracking-[0.16em] text-[#4B4567]">Overall</div>
          <div className="text-3xl font-serif font-bold" style={{ color: overallTone.hex }}>
            {overall}
          </div>
          <div className="text-[10px] text-[#857E9C]">/ 100 · {label}</div>
        </div>
      </div>

      {narrative && (
        <p className="text-[#1A1330] leading-relaxed mt-4 text-sm italic">{narrative}</p>
      )}
    </section>
  );
}
