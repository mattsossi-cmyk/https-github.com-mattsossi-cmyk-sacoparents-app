import { Link } from "react-router-dom";
import {
  ClipboardList, Heart, Compass, MessagesSquare, FileText, ChevronRight, CheckCircle2,
} from "lucide-react";

/**
 * FivePillarJourney — the new organising principle for the Dashboard.
 *
 * Instead of a flat grid of "preparation modules", the parent's tools are
 * arranged into 5 pillars that match how a co-parenting journey actually
 * unfolds:
 *
 *   1. Understand Your Family     (assessments)
 *   2. Understand Your Child      (child-focused profile)
 *   3. Build Your Parenting Foundation (planning tools)
 *   4. Prepare to Work Together   (skills)
 *   5. Reports & Action Center    (outputs)
 *
 * Each pillar shows:
 *   * A big roman numeral badge
 *   * Title + one-sentence intent
 *   * The list of tools inside — each with a completion tick when done
 *   * A "start" CTA linking to the next incomplete tool
 *
 * Props
 *   completed  — dict of step-key -> truthy when that step is done. Keys
 *                match the existing Dashboard `prep.completed` shape
 *                (child_goals, issues, priority, comm_style, readiness).
 *   flags      — additional booleans available (e.g. hasSummary,
 *                hasNdAnswers, hasSafetyAssessment). Optional.
 */

const PILLARS = [
  {
    id: 1,
    key: "understand_family",
    title: "Understand your family",
    intent: "Where are we today?",
    Icon: ClipboardList,
    color: "#3D1A78",
    tools: [
      { label: "Co-Parenting Reflection (Communication Style)", to: "/prep/communication", completedKey: "comm_style" },
      { label: "Family Violence / IPV Screen", to: "/safety-assessment", completedFlag: "hasSafetyAssessment" },
      { label: "Special Needs Assessment", to: "/neurodivergent", completedFlag: "hasNdAnswers" },
      { label: "Mediation Readiness Check", to: "/prep/readiness", completedKey: "readiness" },
    ],
  },
  {
    id: 2,
    key: "understand_child",
    title: "Understand your child",
    intent: "What does my child need most?",
    Icon: Heart,
    color: "#B84EBB",
    tools: [
      { label: "Child-Centered Goals", to: "/prep/child-goals", completedKey: "child_goals" },
      { label: "Issues & Concerns (School, medical, emotional)", to: "/prep/issues", completedKey: "issues" },
      { label: "Special Needs Deep-Dive (optional)", to: "/neurodivergent", completedFlag: "hasNdAnswers" },
    ],
  },
  {
    id: 3,
    key: "foundation",
    title: "Build your parenting foundation",
    intent: "What kind of parenting relationship do I want to create?",
    Icon: Compass,
    color: "#5E2DB5",
    tools: [
      { label: "Priority & Agenda (What matters most?)", to: "/prep/priority", completedKey: "priority" },
      { label: "Foundation Statement (in your Summary)", to: "/summary", completedFlag: "hasSummary" },
      { label: "Personal Reflection", to: "/reflection" },
    ],
  },
  {
    id: 4,
    key: "work_together",
    title: "Prepare to work together",
    intent: "How can we communicate more effectively?",
    Icon: MessagesSquare,
    color: "#2DB5B5",
    tools: [
      { label: "Communication Style & AI Coach", to: "/prep/communication", completedKey: "comm_style" },
      { label: "AI Coach Chat (in the moment)", to: "/coach" },
      { label: "Safety & Parallel Parenting Toolkit", to: "/safety" },
      { label: "Journal / Reflection Space", to: "/reflection" },
      { label: "Gmail — Coach-drafted replies", to: "/gmail" },
    ],
  },
  {
    id: 5,
    key: "reports",
    title: "Reports & Action Center",
    intent: "Your documents, one place.",
    Icon: FileText,
    color: "#C28771",
    tools: [
      { label: "Co-Parenting Assessment", to: "/summary", completedFlag: "hasSummary" },
      { label: "Alignment Statement", to: "/summary?tab=agreement", completedFlag: "hasSummary" },
      { label: "Personal Growth Plan", to: "/summary?tab=improve", completedFlag: "hasSummary" },
      { label: "Special Needs Reports", to: "/neurodivergent/reports", completedFlag: "hasNdReports" },
      { label: "Certificate of Completion", to: "/my-plan#certificate", completedFlag: "hasCertificate" },
      { label: "My Plan (progress snapshot)", to: "/my-plan" },
    ],
  },
];

function isToolDone(tool, completed, flags) {
  if (tool.completedKey) return !!completed?.[tool.completedKey];
  if (tool.completedFlag) return !!flags?.[tool.completedFlag];
  return false;
}

function PillarCard({ pillar, completed, flags }) {
  const { Icon, color, tools } = pillar;
  const doneCount = tools.filter((t) => isToolDone(t, completed, flags)).length;
  const nextTool = tools.find((t) => !isToolDone(t, completed, flags)) || tools[0];
  const progress = tools.length ? Math.round((doneCount / tools.length) * 100) : 0;

  return (
    <article
      className="group bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-6 shadow-sm hover:shadow-md transition-shadow"
      data-testid={`pillar-${pillar.id}-card`}
    >
      <header className="flex items-start gap-4">
        <div
          className="shrink-0 w-14 h-14 rounded-2xl grid place-items-center font-serif text-2xl font-bold"
          style={{ background: `${color}18`, color }}
          aria-hidden
        >
          {pillar.id}
        </div>
        <div className="flex-1 min-w-0">
          <div
            className="text-[10px] uppercase tracking-[0.22em] font-bold"
            style={{ color }}
          >
            Pillar {pillar.id}
          </div>
          <h3 className="font-serif text-2xl text-[#1A1330] leading-tight">
            {pillar.title}
          </h3>
          <p className="text-sm text-[#4B4567] italic mt-0.5">{pillar.intent}</p>
        </div>
        <div className="shrink-0 hidden sm:block">
          <Icon size={22} style={{ color }} />
        </div>
      </header>

      <div className="mt-4 flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-[#E5E0EE] overflow-hidden">
          <div
            className="h-full transition-all"
            style={{
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${color} 0%, ${color}DD 100%)`,
            }}
          />
        </div>
        <div className="text-xs font-mono text-[#4B4567] whitespace-nowrap">
          {doneCount}/{tools.length} done
        </div>
      </div>

      <ul className="mt-4 space-y-2">
        {tools.map((t) => {
          const done = isToolDone(t, completed, flags);
          return (
            <li key={t.to + t.label}>
              <Link
                to={t.to}
                className="flex items-center gap-3 py-2 px-3 rounded-xl hover:bg-[#F5F2FA] text-sm"
                data-testid={`pillar-${pillar.id}-tool-${t.completedKey || t.completedFlag || t.label.split(" ")[0].toLowerCase()}`}
              >
                {done ? (
                  <CheckCircle2 size={16} style={{ color }} aria-hidden />
                ) : (
                  <span
                    className="w-4 h-4 rounded-full border-2 shrink-0"
                    style={{ borderColor: `${color}55` }}
                    aria-hidden
                  />
                )}
                <span className={done ? "text-[#1A1330]" : "text-[#4B4567]"}>
                  {t.label}
                </span>
                <ChevronRight size={14} className="ml-auto text-[#857E9C]" />
              </Link>
            </li>
          );
        })}
      </ul>

      <Link
        to={nextTool.to}
        className="mt-4 inline-flex items-center gap-2 text-sm font-semibold hover:underline"
        style={{ color }}
        data-testid={`pillar-${pillar.id}-cta`}
      >
        {doneCount === tools.length ? "Revisit" : doneCount === 0 ? "Start here" : "Continue"} →
      </Link>
    </article>
  );
}

export default function FivePillarJourney({ completed = {}, flags = {} }) {
  return (
    <section className="mt-8" data-testid="five-pillar-journey">
      <div className="mb-6">
        <div className="eyebrow text-[#3D1A78]">Your journey</div>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1">
          Five pillars, one child-centred path.
        </h2>
        <p className="text-[#4B4567] mt-2 max-w-2xl">
          Start anywhere. Come back anytime. Every pillar builds toward one
          simple goal: both homes on the same page.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {PILLARS.map((p) => (
          <PillarCard key={p.id} pillar={p} completed={completed} flags={flags} />
        ))}
      </div>
    </section>
  );
}
