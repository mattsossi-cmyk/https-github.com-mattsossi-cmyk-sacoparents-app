import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Compass,
  Sparkles,
} from "lucide-react";

/**
 * NextStepJourney — the "What do I do next?" home.
 *
 * The app has grown to hold assessments, videos, badges, reports, IPV tools,
 * special-needs modules, Foundation Statements, and mediation prep — all
 * competing for attention. This component collapses that noise into a
 * single linear pathway of 6 stages, auto-highlights where the parent
 * actually is, and shows one big "Do this next" card.
 *
 * Journey (in order):
 *   1. Assess               — Readiness Check + Communication Style
 *   2. Understand Your Child — Child-centered goals + Special Needs
 *   3. Set Priorities        — Priority & Agenda ranking
 *   4. Build Your Foundation — Reflection / Foundation Statement
 *   5. Prepare for Mediation — Issues, Alignment Statement, Summary
 *   6. Review Progress       — My Plan, Growth, Certificate
 *
 * The auto-detect logic reads `prep_data.completed` and picks the first
 * stage that still has an outstanding required task.
 *
 * Props:
 *   completed:      { [step_key]: boolean } — from prep_data.completed
 *   summariesCount: number                  — count of generated summaries
 *   hasCertificate: boolean                 — from eligibility endpoint
 */

const CATEGORY_STYLES = {
  assessment: {
    chip: "bg-[#EEF3FE] text-[#2E4B8A] border-[#C9D9F5]",
    label: "Assessment",
  },
  reflection: {
    chip: "bg-[#E8F2ED] text-[#1F5C3B] border-[#C6DECF]",
    label: "Reflection & Wellness",
  },
  preparation: {
    chip: "bg-[#EFE9F9] text-[#3D1A78] border-[#D7C9F0]",
    label: "Mediation Preparation",
  },
  review: {
    chip: "bg-[#FFF6EC] text-[#8C5A2C] border-[#EED3B5]",
    label: "Review & Progress",
  },
};

const STAGES = [
  {
    id: "assess",
    number: 1,
    title: "Assess",
    category: "assessment",
    blurb:
      "Take a short honest read on where you are today — your readiness and how you tend to communicate.",
    activities: [
      { label: "Readiness Check", path: "/prep/readiness", requires: "readiness" },
      { label: "Communication Style", path: "/prep/communication", requires: "comm_style" },
    ],
    // Stage is complete when ALL required keys are set.
    requires: ["readiness", "comm_style"],
    ctaPath: "/prep/readiness",
    ctaLabel: "Start the Readiness Check",
  },
  {
    id: "understand_child",
    number: 2,
    title: "Understand Your Child",
    category: "reflection",
    blurb:
      "Name what your child actually needs from you — separate from what feels urgent in the conflict.",
    activities: [
      { label: "Child-Centered Goals", path: "/prep/child-goals", requires: "child_goals" },
      { label: "Special Needs Assessment (optional)", path: "/neurodivergent" },
    ],
    requires: ["child_goals"],
    ctaPath: "/prep/child-goals",
    ctaLabel: "Name your child's needs",
  },
  {
    id: "priorities",
    number: 3,
    title: "Set Priorities",
    category: "preparation",
    blurb:
      "Rank what matters most for mediation — where you'll hold firm, and where you can flex.",
    activities: [
      { label: "Priority & Agenda", path: "/prep/priority", requires: "priority" },
    ],
    requires: ["priority"],
    ctaPath: "/prep/priority",
    ctaLabel: "Set your priorities",
  },
  {
    id: "foundation",
    number: 4,
    title: "Build Your Foundation",
    category: "reflection",
    blurb:
      "Write the Foundation Statement your future self can lean on — the parent you're becoming.",
    activities: [
      { label: "Foundation Statement", path: "/prep/reflection", requires: "reflection" },
      { label: "Journal / Reflection Space", path: "/reflection" },
    ],
    requires: ["reflection"],
    ctaPath: "/prep/reflection",
    ctaLabel: "Write your Foundation",
  },
  {
    id: "prepare",
    number: 5,
    title: "Prepare for Mediation",
    category: "preparation",
    blurb:
      "Map the specific issues you'll bring, then generate your court-quality Mediation Summary.",
    activities: [
      { label: "Issues & Concerns", path: "/prep/issues", requires: "issues" },
      { label: "Generate Mediation Summary", path: "/summary" },
      { label: "Alignment Statement", path: "/summary?tab=agreement" },
    ],
    // "Complete" here means the parent has generated at least one summary.
    requiresSummary: true,
    ctaPath: "/prep/issues",
    ctaLabel: "Map your issues",
  },
  {
    id: "review",
    number: 6,
    title: "Review Progress",
    category: "review",
    blurb:
      "See how you've grown, download your certificate, and revisit anything that needs updating.",
    activities: [
      { label: "My Plan & Growth", path: "/my-plan" },
      { label: "Certificate of Completion", path: "/my-plan#certificate" },
      { label: "Personal Growth Plan", path: "/summary?tab=improve" },
    ],
    requiresCertificate: true,
    ctaPath: "/my-plan",
    ctaLabel: "Review your growth",
  },
];

function isStageDone({ stage, completed, summariesCount, hasCertificate }) {
  if (stage.requiresSummary) return summariesCount > 0;
  if (stage.requiresCertificate) return !!hasCertificate;
  return (stage.requires || []).every((k) => !!completed[k]);
}

function pickCurrentStage({ completed, summariesCount, hasCertificate }) {
  for (const stage of STAGES) {
    if (!isStageDone({ stage, completed, summariesCount, hasCertificate })) {
      return stage;
    }
  }
  // Everything done — celebrate on the last stage.
  return STAGES[STAGES.length - 1];
}

function ProgressRail({ current, doneMap }) {
  return (
    <ol
      className="grid grid-cols-3 sm:grid-cols-6 gap-2"
      data-testid="journey-progress-rail"
    >
      {STAGES.map((s) => {
        const isDone = doneMap[s.id];
        const isCurrent = s.id === current.id;
        return (
          <li
            key={s.id}
            className="flex flex-col items-start"
            data-testid={`journey-rail-${s.id}`}
          >
            <div
              className={`w-full h-1 rounded-full mb-2 ${
                isDone
                  ? "bg-[#3D1A78]"
                  : isCurrent
                  ? "bg-[#3D1A78]/50"
                  : "bg-[#E5E0EE]"
              }`}
            />
            <div className="flex items-center gap-1.5">
              {isDone ? (
                <CheckCircle2
                  size={12}
                  className="text-[#3D1A78] shrink-0"
                />
              ) : (
                <Circle
                  size={12}
                  className={
                    isCurrent ? "text-[#3D1A78] shrink-0" : "text-[#857E9C] shrink-0"
                  }
                />
              )}
              <span
                className={`text-[10px] uppercase tracking-[0.14em] font-bold ${
                  isCurrent
                    ? "text-[#3D1A78]"
                    : isDone
                    ? "text-[#4B4567]"
                    : "text-[#857E9C]"
                }`}
              >
                {s.number}. {s.title}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function StageHero({ stage, isFirstEver, allDone }) {
  const cat = CATEGORY_STYLES[stage.category];
  return (
    <div
      className="rounded-3xl bg-gradient-to-br from-[#3D1A78] via-[#4A2688] to-[#2D0F63] text-white p-6 sm:p-8 shadow-lg relative overflow-hidden"
      data-testid="journey-stage-hero"
    >
      <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/5" />
      <div className="absolute -bottom-16 -left-16 w-48 h-48 rounded-full bg-white/5" />

      <div className="relative">
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <span
            className="text-[10px] uppercase tracking-[0.2em] font-bold text-white/80"
            data-testid="journey-stage-number"
          >
            Step {stage.number} of {STAGES.length}
          </span>
          <span
            className={`text-[10px] uppercase tracking-[0.14em] font-bold px-2 py-0.5 rounded-full border ${cat.chip}`}
            data-testid="journey-stage-category"
          >
            {cat.label}
          </span>
        </div>

        <div className="flex items-center gap-2 mb-2">
          <Compass size={16} className="text-[#FFD9A8]" />
          <span
            className="text-xs uppercase tracking-[0.2em] font-bold text-[#FFD9A8]"
          >
            {allDone
              ? "You've completed the journey"
              : isFirstEver
              ? "Start here"
              : "Do this next"}
          </span>
        </div>

        <h2
          className="font-serif text-3xl sm:text-4xl leading-tight mb-3"
          data-testid="journey-stage-title"
        >
          {stage.title}
        </h2>
        <p className="text-white/85 text-sm sm:text-base max-w-2xl leading-relaxed">
          {stage.blurb}
        </p>

        {stage.activities?.length > 0 && (
          <ul
            className="mt-5 space-y-1.5 max-w-xl"
            data-testid="journey-stage-activities"
          >
            {stage.activities.map((a, i) => (
              <li key={`${a.label}-${i}`} className="flex items-center gap-2 text-sm text-white/85">
                <span className="w-1.5 h-1.5 rounded-full bg-[#FFD9A8] shrink-0" />
                {a.label}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            to={stage.ctaPath}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-white text-[#3D1A78] font-bold text-sm hover:bg-[#FFF6EC] transition-colors"
            data-testid="journey-stage-cta"
          >
            <Sparkles size={14} />
            {allDone ? "Revisit this step" : stage.ctaLabel}
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}

function UpNextTeaser({ nextStage }) {
  if (!nextStage) return null;
  const cat = CATEGORY_STYLES[nextStage.category];
  return (
    <div
      className="mt-4 flex items-center gap-3 text-sm text-[#4B4567]"
      data-testid="journey-up-next"
    >
      <span className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
        Up next
      </span>
      <span
        className={`text-[10px] uppercase tracking-[0.14em] font-bold px-2 py-0.5 rounded-full border ${cat.chip}`}
      >
        {cat.label}
      </span>
      <Link
        to={nextStage.ctaPath}
        className="font-semibold text-[#3D1A78] hover:underline"
      >
        {nextStage.number}. {nextStage.title} →
      </Link>
    </div>
  );
}

export default function NextStepJourney({
  completed = {},
  summariesCount = 0,
  hasCertificate = false,
}) {
  const current = pickCurrentStage({ completed, summariesCount, hasCertificate });
  const doneMap = Object.fromEntries(
    STAGES.map((s) => [s.id, isStageDone({ stage: s, completed, summariesCount, hasCertificate })])
  );
  const allDone = STAGES.every((s) => doneMap[s.id]);
  const isFirstEver = Object.keys(completed).length === 0 && summariesCount === 0;
  const currentIdx = STAGES.findIndex((s) => s.id === current.id);
  const nextStage = allDone ? null : STAGES[currentIdx + 1] || null;

  return (
    <section
      className="mt-6 mb-10"
      data-testid="next-step-journey"
      aria-labelledby="next-step-journey-title"
    >
      <h1 id="next-step-journey-title" className="sr-only">
        Your co-parenting preparation journey
      </h1>

      <StageHero stage={current} isFirstEver={isFirstEver} allDone={allDone} />
      <UpNextTeaser nextStage={nextStage} />

      <div className="mt-6">
        <div className="text-xs uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-3">
          Your full 6-step pathway
        </div>
        <ProgressRail current={current} doneMap={doneMap} />
      </div>
    </section>
  );
}
