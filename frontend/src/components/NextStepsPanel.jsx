import { CheckCircle2, Calendar, TrendingUp } from "lucide-react";

/**
 * NextStepsPanel — closes every report with actionable, dated recommendations.
 * Renders three columns (This Week / Before Mediation / Long-Term) so the
 * parent leaves with clarity on what to do next.
 */

const SECTION_META = [
  {
    key: "this_week",
    fallbackKey: null,
    title: "This week",
    subtitle: "Momentum in the next 7 days",
    Icon: CheckCircle2,
    color: "#3D1A78",
  },
  {
    key: "before_mediation",
    fallbackKey: "before_next_conversation",
    title: "Before mediation",
    subtitle: "Prepare before the next session",
    Icon: Calendar,
    color: "#5E2DB5",
  },
  {
    key: "long_term",
    fallbackKey: "for_the_mediator",
    title: "Long-term",
    subtitle: "Intentions to hold for 3+ months",
    Icon: TrendingUp,
    color: "#0F7676",
  },
];

export default function NextStepsPanel({ nextSteps, title = "Your next three steps" }) {
  if (!nextSteps) return null;
  const sections = SECTION_META
    .map((meta) => {
      const items = nextSteps[meta.key] || (meta.fallbackKey ? nextSteps[meta.fallbackKey] : null);
      return items && items.length ? { meta, items } : null;
    })
    .filter(Boolean);

  if (sections.length === 0) return null;

  return (
    <section
      className="bg-gradient-to-br from-[#F5F2FA] to-white rounded-3xl border border-[#E5E0EE] p-6 sm:p-8"
      data-testid="next-steps-panel"
    >
      <div className="eyebrow text-[#3D1A78]">Momentum</div>
      <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1 mb-1">
        {title}
      </h2>
      <p className="text-sm text-[#4B4567] mb-6">
        Concrete actions — each one starts with a verb, each one moves you forward.
      </p>

      <div className="grid md:grid-cols-3 gap-4">
        {sections.map(({ meta, items }) => {
          const { Icon, color } = meta;
          return (
            <div
              key={meta.key}
              className="bg-white rounded-2xl border border-[#E5E0EE] p-5"
              data-testid={`next-steps-${meta.key}`}
            >
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-8 h-8 rounded-full grid place-items-center"
                  style={{ background: `${color}18`, color }}
                >
                  <Icon size={14} />
                </div>
                <div>
                  <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold" style={{ color }}>
                    {meta.title}
                  </div>
                  <div className="text-[0.6875rem] text-[#6E6787]">{meta.subtitle}</div>
                </div>
              </div>
              <ul className="space-y-2.5">
                {items.map((item, i) => (
                  <li key={`${meta.key}-${i}-${String(item).slice(0, 32)}`} className="flex gap-2 text-sm text-[#1A1330] leading-snug">
                    <span className="mt-0.5 shrink-0" style={{ color }}>✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
